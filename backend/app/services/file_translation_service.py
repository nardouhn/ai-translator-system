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
                
                from app.services.text_splitter import split_text_into_chunks
                from app.services.cache_service import MODEL_VERSION
                
                logger.info(f"File Translation: Found {len(texts)} paragraphs to process.")
                
                # --- BƯỚC 1: Chuẩn bị tất cả sub-chunks TRƯỚC khi gọi bất kỳ API nào ---
                # Mỗi paragraph được cắt thành sub-chunks (<=600 chars), ta build 1 flat list
                # để batch MGET 1 lần duy nhất, cực kỳ hiệu quả.
                paragraph_sub_chunks: list[list[str]] = []
                all_sub_chunks_flat: list[str] = []
                
                for chunk in texts:
                    if not chunk.strip():
                        paragraph_sub_chunks.append([chunk])
                    else:
                        sub_chunks = split_text_into_chunks(chunk, max_chars=600)
                        paragraph_sub_chunks.append(sub_chunks)
                        all_sub_chunks_flat.extend([sc for sc in sub_chunks if sc.strip()])
                
                # --- BƯỚC 2: Batch MGET TẤT CẢ sub-chunks trong 1 lần duy nhất ---
                logger.info(f"Batch MGET {len(all_sub_chunks_flat)} sub-chunks from Redis...")
                all_cached = await mget_cached_translations(domain_str, all_sub_chunks_flat)
                
                # --- BƯỚC 3: Dịch từng paragraph, tra cứu cache trước, gọi Kaggle nếu miss ---
                translated_texts = []
                newly_translated = {}
                last_progress_update = 0
                total = len(texts)
                
                for idx, (chunk, sub_chunks) in enumerate(zip(texts, paragraph_sub_chunks)):
                    if not chunk.strip():
                        translated_texts.append(chunk)
                    else:
                        tr_parts = []
                        for sc in sub_chunks:
                            if not sc.strip():
                                tr_parts.append(sc)
                                continue
                            
                            cached_val = all_cached.get(sc)
                            if cached_val is not None:
                                logger.info(f"🟢 CACHE HIT sub-chunk: '{sc[:30]}'")
                                tr_parts.append(cached_val)
                            else:
                                logger.warning(f"🔴 CACHE MISS sub-chunk: '{sc[:30]}'. Calling AI...")
                                sc_tr = await translate_chunk_async(sc, domain_str)

                                # --- Kiểm tra thất bại: raise để file bị đánh dấu failed ---
                                _FAIL_PREFIXES = ("[ERROR", "[TIMEOUT]", "[FAILED]")
                                if sc_tr is None or sc_tr.strip() == "":
                                    raise Exception(
                                        f"AI trả về kết quả rỗng cho đoạn: '{sc[:60]}...'"
                                    )
                                if any(sc_tr.startswith(p) for p in _FAIL_PREFIXES):
                                    reason = sc_tr.split("]")[0] + "]" if "]" in sc_tr else sc_tr[:80]
                                    raise Exception(
                                        f"AI thất bại với lý do '{reason}' cho đoạn: '{sc[:60]}...'"
                                    )

                                tr_parts.append(sc_tr)
                                # Chỉ lưu cache khi dịch thành công
                                newly_translated[sc] = sc_tr

                        
                        tr = "".join(tr_parts) if tr_parts else chunk
                        translated_texts.append(tr)
                    
                    segments_list.append({
                        "source_text": chunk,
                        "translated_text": translated_texts[-1]
                    })
                    
                    # Update progress
                    current_pct = int(((idx + 1) / total) * 100)
                    if (idx + 1) % 10 == 0 or (current_pct - last_progress_update) >= 5 or (idx + 1) == total:
                        await _update_progress(idx + 1, total)
                        last_progress_update = current_pct
                    
                    # Flush cache mỗi 10 entries mới để không mất data khi crash
                    if len(newly_translated) >= 10:
                        asyncio.create_task(mset_cached_translations(domain_str, newly_translated.copy()))
                        newly_translated.clear()
                
                # Flush cache còn lại
                if newly_translated:
                    asyncio.create_task(mset_cached_translations(domain_str, newly_translated.copy()))
                
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
                
                uploaded = await StorageService.upload_translated_file(
                    object_key=translated_file_key,
                    file_bytes=translated_file_content,
                    original_filename=safe_filename
                )
                if uploaded:
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
