import os
import asyncio
import tempfile
import logging
from arq import Worker
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.settings import settings
from app.db.session import AsyncSessionLocal
from app.db.models import File, FileSegment, StatusEnum, Logs, RequestTypeEnum
from app.services.document_translator import convert_pdf_to_docx, translate_docx_document, translate_txt_document
from app.services.translator_provider import translate_batch_with_provider

logger = logging.getLogger(__name__)

async def process_file_translation(ctx, file_id: int, file_path: str, source_lang: str, target_lang: str, domain: str, session_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(File).where(File.file_id == file_id))
        file_row = result.scalars().first()
        if not file_row:
            if os.path.exists(file_path):
                os.remove(file_path)
            return
            
        file_row.status = StatusEnum.processing
        await db.commit()

        local_tmp_path = None
        try:
            # Download file from R2
            from app.services.storage_service import StorageService
            import aioboto3
            import uuid
            
            base_name = os.path.basename(file_path)
            local_tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{base_name}")
            
            session = aioboto3.Session()
            async with session.client(**StorageService.get_s3_client_args()) as s3_client:
                await s3_client.download_file(settings.r2_bucket_name, file_path, local_tmp_path)
            
            with open(local_tmp_path, "rb") as f:
                file_content = f.read()

            content_length = len(file_content)
            logger.info(f"Downloaded file length: {content_length} bytes")
            if content_length < 100:
                logger.warning(f"File content preview (first 100 bytes): {file_content[:100]}")

            if content_length == 0:
                raise Exception("Lỗi: Tải file thất bại. File rỗng (0 bytes).")

            ext = file_row.original_filename.split('.')[-1].lower() if file_row.original_filename else "unknown"

            if ext in ["docx", "pdf"] and content_length < 100:
                raise Exception(f"Lỗi: Nội dung file {ext} tải về không hợp lệ (dung lượng quá nhỏ: {content_length} bytes). Trích xuất: {file_content[:100]}")

            segments_list = []
            
            async def _do_translate_batch(texts: list[str]) -> list[str]:
                if not texts:
                    return []
                translated_texts, _ = await translate_batch_with_provider(texts, domain or "General")
                for orig, tr in zip(texts, translated_texts):
                    segments_list.append({
                        "source_text": orig,
                        "translated_text": tr
                    })
                return translated_texts

            async def _do_translate(text: str) -> str:
                res = await _do_translate_batch([text])
                return res[0] if res else text

            # Perform document translation
            try:
                if ext == "txt":
                    full_text, b64_data = await translate_txt_document(file_content, _do_translate)
                elif ext == "docx" or ext == "pdf":
                    if ext == "pdf":
                        docx_bytes = convert_pdf_to_docx(file_content)
                    else:
                        docx_bytes = file_content
                    full_text, b64_data = await translate_docx_document(docx_bytes, _do_translate_batch)
                else:
                    full_text, b64_data = "", ""
            except Exception as model_error:
                error_str = f"AI Model translation failed: {str(model_error)}"
                logger.error(error_str, exc_info=True)
                
                file_row.status = StatusEnum.failed
                file_row.error_message = error_str
                await db.commit()
                
                log_record = Logs(
                    session_id=session_id,
                    translation_id=None,
                    status=StatusEnum.failed,
                    request_type=RequestTypeEnum.file,
                )
                db.add(log_record)
                await db.commit()
                return  # Exit early since translation failed

            # Save the base64 string to a new file so it can be downloaded
            import base64
            translated_file_key = f"translated_{file_path}"
            if b64_data:
                translated_file_content = base64.b64decode(b64_data)
                
                async with session.client(**StorageService.get_s3_client_args()) as s3_client:
                    await s3_client.put_object(
                        Bucket=settings.r2_bucket_name,
                        Key=translated_file_key,
                        Body=translated_file_content
                    )
                
                file_row.file_path = translated_file_key

            # Save segments asynchronously
            for index, seg in enumerate(segments_list):
                segment_data = {
                    "file_id": file_id,
                    "segment_order": index,
                    "source_text": seg['source_text'],
                    "translated_text": seg['translated_text']
                }
                db.add(FileSegment(**segment_data))
                
            await db.flush()

            file_row.status = StatusEnum.success
            await db.commit()

            log_record = Logs(
                session_id=session_id,
                translation_id=None,
                status=StatusEnum.success,
                request_type=RequestTypeEnum.file,
            )
            db.add(log_record)
            await db.commit()

        except Exception as e:
            logger.error(f"Unexpected error in process_file_translation: {str(e)}", exc_info=True)
            file_row.status = StatusEnum.error
            file_row.error_message = str(e)
            await db.commit()
        finally:
            if local_tmp_path and os.path.exists(local_tmp_path):
                os.remove(local_tmp_path)

redis_settings = RedisSettings.from_dsn(settings.redis_url)
if settings.redis_url.startswith("rediss://"):
    redis_settings.ssl_cert_reqs = "none"

class WorkerSettings:
    functions = [process_file_translation]
    redis_settings = redis_settings
