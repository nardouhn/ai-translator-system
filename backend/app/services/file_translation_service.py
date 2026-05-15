import os
import tempfile
import logging
import asyncio
import base64
import hashlib
from sqlalchemy.future import select

from app.settings import settings
from app.db.session import AsyncSessionLocal
from app.db.models import File, FileSegment, StatusEnum, Logs, RequestTypeEnum
from app.services.document_translator import convert_pdf_to_docx, translate_docx_document, translate_txt_document
from app.services.cache_service import mget_cached_translations, mset_cached_translations
from app.services.translator_provider import translate_chunk_async
from app.services.redis_client import get_async_redis

logger = logging.getLogger(__name__)

async def process_file_translation(
    file_id: int, 
    file_path: str, 
    domain: str, 
    session_id: str,
    request_time: __import__('datetime').datetime | None = None,
    ip_address: str | None = None
):
    domain_str = (domain or "general").strip().lower()
    
    if request_time and request_time.tzinfo:
        request_time = request_time.replace(tzinfo=None)
        logger.info(f"Stripped tzinfo from request_time. Is aware? {request_time.tzinfo is not None}")
    else:
        logger.info(f"request_time is already naive or None. Is aware? {getattr(request_time, 'tzinfo', None) is not None}")
    
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

            if content_length == 0:
                raise Exception("Lỗi: Tải file thất bại. File rỗng (0 bytes).")

            ext = file_row.original_filename.split('.')[-1].lower() if file_row.original_filename else "unknown"
            
            text_hash = hashlib.sha256(file_content).hexdigest()

            if ext in ["docx", "pdf"] and content_length < 100:
                raise Exception(f"Lỗi: Nội dung file {ext} tải về không hợp lệ (dung lượng quá nhỏ: {content_length} bytes). Trích xuất: {file_content[:100]}")

            segments_list = []
            
            # Helper for Progress Update
            redis_client = get_async_redis()
            progress_key = f"job_progress:{file_id}"
            
            async def _update_progress(current: int, total: int):
                if total == 0: return
                pct = int((current / total) * 100)
                await redis_client.setex(progress_key, 86400, str(pct))
            
            async def _do_translate_batch(texts: list[str]) -> list[str]:
                if not texts:
                    return []
                
                total = len(texts)
                logger.info(f"File Translation: Found {total} chunks to translate.")
                
                # BATCH MGET Check from Upstash
                cached_results = await mget_cached_translations(domain_str, texts)
                
                translated_texts = []
                newly_translated = {}
                
                last_progress_update = 0
                
                for idx, chunk in enumerate(texts):
                    # Empty check
                    if not chunk.strip():
                        translated_texts.append(chunk)
                        continue
                        
                    from app.services.cache_service import strictly_normalize_text
                    cleaned_chunk = strictly_normalize_text(chunk)
                    cached_val = cached_results.get(chunk)
                    
                    debug_hash = __import__('hashlib').sha256(cleaned_chunk.encode("utf-8")).hexdigest()
                    logger.debug(f"File Cache Key: translate:v5:{domain_str}:en:vi:{debug_hash} | Text: '{cleaned_chunk[:20]}'")
                    
                    if cached_val is not None:
                        logger.info(f"🟢 CACHE HIT for chunk {idx+1}/{total}: '{cleaned_chunk[:20]}...'")
                        translated_texts.append(cached_val)
                    else:
                        logger.warning(f"🔴 CACHE MISS for chunk {idx+1}/{total}: '{cleaned_chunk[:20]}...'. Calling Kaggle...")
                        
                        from app.services.text_splitter import split_text_into_chunks
                        # Chẻ nhỏ đoạn văn dài thành các sub-chunk (600 ký tự) để Kaggle không bị timeout
                        sub_chunks = split_text_into_chunks(chunk, max_chars=600)
                        
                        tr_parts = []
                        for sc in sub_chunks:
                            if not sc.strip():
                                tr_parts.append(sc)
                                continue
                            
                            # Kiểm tra cache cho từng sub-chunk
                            sc_cleaned = strictly_normalize_text(sc)
                            sc_cached = await mget_cached_translations(domain_str, [sc])
                            sc_val = sc_cached.get(sc)
                            
                            if sc_val is not None:
                                tr_parts.append(sc_val)
                            else:
                                sc_tr = await translate_chunk_async(sc, domain_str)
                                tr_parts.append(sc_tr)
                                if not sc_tr.startswith("[ERROR") and not sc_tr.startswith("[TIMEOUT") and not sc_tr.startswith("[FAILED"):
                                    newly_translated[sc] = sc_tr
                        
                        tr = "".join(tr_parts) if tr_parts else chunk
                        translated_texts.append(tr)
                        
                        # Cache toàn bộ câu văn gốc nếu cần (chỉ khi không có lỗi)
                        if not tr.startswith("[ERROR") and not tr.startswith("[TIMEOUT") and not tr.startswith("[FAILED"):
                            newly_translated[chunk] = tr
                    
                    segments_list.append({
                        "source_text": chunk,
                        "translated_text": translated_texts[-1]
                    })
                    
                    # Batch Update Progress in Upstash
                    current_pct = int(((idx + 1) / total) * 100)
                    if (idx + 1) % 10 == 0 or (current_pct - last_progress_update) >= 5 or (idx + 1) == total:
                        await _update_progress(idx + 1, total)
                        last_progress_update = current_pct
                        
                    # Periodically save cache to Upstash to prevent total loss on crash
                    if len(newly_translated) >= 10:
                        asyncio.create_task(mset_cached_translations(domain_str, newly_translated))
                        newly_translated.clear()
                        
                # Save any remaining newly translated chunks to Cache
                if newly_translated:
                    asyncio.create_task(mset_cached_translations(domain_str, newly_translated))
                    
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
                    
                    if ext == "pdf":
                        # Convert DOCX back to PDF
                        from app.services.document_translator import convert_docx_to_pdf
                        translated_docx_bytes = base64.b64decode(b64_data)
                        translated_pdf_bytes = convert_docx_to_pdf(translated_docx_bytes)
                        b64_data = base64.b64encode(translated_pdf_bytes).decode("utf-8")
                else:
                    full_text, b64_data = "", ""
            except Exception as model_error:
                error_str = f"File Translation failed during processing: {str(model_error)}"
                logger.error(error_str, exc_info=True)
                
                try:
                    await db.rollback()
                    
                    # Lấy lại file_row sau khi rollback
                    result = await db.execute(select(File).where(File.file_id == file_id))
                    file_row = result.scalars().first()
                    if file_row:
                        file_row.status = StatusEnum.failed
                        file_row.error_message = error_str
                    
                    from datetime import datetime, timezone
                    completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
                    
                    log_record = Logs(
                        session_id=session_id,
                        translation_id=None,
                        status=StatusEnum.failed,
                        request_type=RequestTypeEnum.file,
                        request_time=request_time, # Đã được xử lý replace(tzinfo=None) ở đầu hàm
                        completed_time=completed_time,
                        file_id=file_id,
                    )
                    db.add(log_record)
                    await db.commit()
                except Exception as inner_db_error:
                    await db.rollback()
                    logger.error(f"Failed to log model error to DB: {str(inner_db_error)}")
                return  # Exit early

            import uuid
            original_name = file_row.original_filename or "unknown"
            base_name, ext_str = os.path.splitext(original_name)
            base_name = os.path.basename(base_name) # Strip any folder paths
            safe_filename = f"{base_name}_translated{ext_str}"
            
            translated_file_key = f"translations/{uuid.uuid4()}/{safe_filename}"
            
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
            from app.services.translation_service import map_domain_to_id
            domain_id_val = map_domain_to_id(domain_str)
            
            for index, seg in enumerate(segments_list):
                if seg['source_text']:
                    hash_string = f"{domain_id_val}_{seg['source_text']}"
                    seg_hash = hashlib.sha256(hash_string.encode("utf-8")).hexdigest()
                else:
                    seg_hash = None
                segment_data = {
                    "file_id": file_id,
                    "segment_order": index,
                    "source_text": seg['source_text'],
                    "translated_text": seg['translated_text'],
                    "text_hash": seg_hash
                }
                db.add(FileSegment(**segment_data))
                
            await db.flush()

            file_row.status = StatusEnum.success
            await db.commit()

            # Mark 100%
            await redis_client.setex(progress_key, 86400, "100")

            from datetime import datetime, timezone
            completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
            log_record = Logs(
                session_id=session_id,
                translation_id=None,
                status=StatusEnum.success,
                request_type=RequestTypeEnum.file,
                request_time=request_time, # Đã được xử lý tzinfo=None ở đầu hàm
                completed_time=completed_time,
                file_id=file_id,
            )
            
            try:
                db.add(log_record)
                await db.commit()
            except Exception as db_err:
                await db.rollback()
                logger.error(f"Failed to commit success log: {str(db_err)}")

        except Exception as e:
            logger.error(f"Unexpected error in process_file_translation: {str(e)}", exc_info=True)
            try:
                await db.rollback()
                
                # Lấy lại file_row sau khi rollback
                result = await db.execute(select(File).where(File.file_id == file_id))
                file_row = result.scalars().first()
                if file_row:
                    file_row.status = StatusEnum.error
                    file_row.error_message = str(e)
                    
                from datetime import datetime, timezone
                completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
                
                log_record = Logs(
                    session_id=session_id,
                    translation_id=None,
                    status=StatusEnum.error,
                    request_type=RequestTypeEnum.file,
                    request_time=request_time,
                    completed_time=completed_time,
                    file_id=file_id,
                )
                db.add(log_record)
                await db.commit()
            except Exception as inner_e:
                await db.rollback()
                logger.error(f"Failed to commit error state to DB: {str(inner_e)}")
        finally:
            if local_tmp_path and os.path.exists(local_tmp_path):
                os.remove(local_tmp_path)
