import hashlib
import asyncio
import logging
import json
import re
from datetime import datetime, timezone
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession

# Lưu ý: Cần import thêm Logs, StatusEnum, RequestTypeEnum từ app.db.models
from app.db.models import Domain, DomainNameEnum, Translation, Logs, StatusEnum, RequestTypeEnum
from app.services.cache_service import mget_cached_translations, mset_cached_translations, strictly_normalize_text, MODEL_VERSION
from app.services.translator_provider import translate_with_provider, translate_chunk_async
from app.services.text_splitter import split_text_into_chunks

logger = logging.getLogger(__name__)


def map_domain_to_id(domain: str | None) -> int:
    mapping = {
        "general": 1,
        "medical": 2,
        "technical": 3,
        "economic": 4
    }
    if not domain:
        return 1
    return mapping.get(domain.strip().lower(), 1)


def restore_formatting(original_chunk: str, translated_chunk: str) -> str:
    """
    Khôi phục khoảng trắng, dấu xuống dòng và dấu câu ở hai đầu của bản dịch 
    sao cho khớp với văn bản gốc.
    """
    if not original_chunk.strip():
        return original_chunk
        
    leading_match = re.match(r'^([\s\u200b\u200c\u200d\ufeff]+)', original_chunk)
    leading_ws = leading_match.group(1) if leading_match else ""
    
    trailing_match = re.search(r'([\s\u200b\u200c\u200d\ufeff]+)$', original_chunk)
    trailing_ws = trailing_match.group(1) if trailing_match else ""
    
    translated_chunk = translated_chunk.strip()
    
    orig_trailing_punct_match = re.search(r'([.!?,"\'\]\)\}]+)$', original_chunk.strip())
    if orig_trailing_punct_match:
        orig_punct = orig_trailing_punct_match.group(1)
        trans_trailing_punct_match = re.search(r'([.!?,"\'\]\)\}]+)$', translated_chunk)
        if not trans_trailing_punct_match:
            translated_chunk += orig_punct
            
    return leading_ws + translated_chunk + trailing_ws


# ==============================================================================
# HÀM 1: DÀNH CHO GIAO DIỆN TEXT / CHAT (STREAMING)
# ==============================================================================
async def stream_translate_text(
    db: DBSession,
    session_id: str,
    source_text: str,
    domain: str | None,
    background_tasks: BackgroundTasks,
    request_time: datetime | None = None,
    ip_address: str | None = None,
    auto_commit: bool = True,
):
    """
    Dịch văn bản và trả về dạng Server-Sent Events (SSE) cho UI.
    Nếu gặp lỗi trong quá trình dịch, stream sẽ lập tức bị ngắt và trả về lỗi.
    """
    domain_str = (domain or "general").strip().lower()
    domain_id_val = map_domain_to_id(domain_str)

    if request_time and request_time.tzinfo:
        request_time = request_time.replace(tzinfo=None)

    hash_string = f"{domain_id_val}_{source_text}"
    text_hash = hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    # 1. Check DB first
    def check_db():
        existing_translation = db.query(Translation).filter(
            Translation.text_hash == text_hash,
            Translation.domain_id == domain_id_val
        ).first()

        if existing_translation and existing_translation.translated_text != source_text:
            return {
                "hit": True,
                "translated_text": existing_translation.translated_text,
                "translation_id": getattr(existing_translation, "id", getattr(existing_translation, "trans_id", None)),
                "from_cache": True,
            }, domain_id_val
            
        return {"hit": False, "existing_translation": existing_translation}, domain_id_val

    db_check_result, domain_id_val = await run_in_threadpool(check_db)
    
    if db_check_result["hit"]:
        yield f"data: {json.dumps({'chunk': db_check_result['translated_text']})}\n\n"
        return

    # 2. Text Splitting
    chunks = split_text_into_chunks(source_text)
    if not chunks:
        yield f"data: {json.dumps({'chunk': ''})}\n\n"
        return
    
    logger.info(f"[STREAM] Translating text (session: {session_id}): split into {len(chunks)} chunks.")

    # 3. Redis Batch Check (MGET)
    cached_results = await mget_cached_translations(domain_str, chunks)
    
    final_translated_chunks = []
    newly_translated_mapping = {}
    provider = "custom-ai"

    # Helper: ghi log thất bại vào DB
    def _log_failure(reason: str):
        try:
            completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
            log_record = Logs(
                session_id=session_id,
                request_type=RequestTypeEnum.text,
                translation_id=None,
                status=StatusEnum.failed,
                request_time=request_time,
                completed_time=completed_time,
            )
            db.add(log_record)
            db.commit()
            logger.info(f"📝 Logged failed translation to DB. Reason: {reason}")
        except Exception as db_err:
            logger.error(f"Failed to write failure log to DB: {db_err}")

    for i, chunk in enumerate(chunks):
        cleaned_chunk = strictly_normalize_text(chunk)

        if not cleaned_chunk:
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            final_translated_chunks.append(chunk)
            continue

        cached_val = cached_results.get(chunk)

        if cached_val is not None:
            restored_cached_val = restore_formatting(chunk, cached_val)
            yield f"data: {json.dumps({'chunk': restored_cached_val})}\n\n"
            final_translated_chunks.append(restored_cached_val)
        else:
            try:
                translated_chunk = await translate_chunk_async(cleaned_chunk, domain_str)

                # Kiểm tra lỗi từ AI
                _FAIL_PREFIXES = ("[ERROR", "[TIMEOUT]", "[FAILED]")
                if translated_chunk is None or translated_chunk.strip() == "":
                    reason = "AI trả về kết quả rỗng (empty output)"
                    logger.error(f"❌ Translation FAILED (chunk {i}): {reason}")
                    await run_in_threadpool(_log_failure, reason)
                    yield f"data: {json.dumps({'error': f'Translation failed: {reason}'})}\n\n"
                    return  # DỪNG STREAM

                if any(translated_chunk.startswith(p) for p in _FAIL_PREFIXES):
                    reason = translated_chunk.split("]")[0] + "]" if "]" in translated_chunk else translated_chunk[:80]
                    logger.error(f"❌ Translation FAILED (chunk {i}): {reason}")
                    await run_in_threadpool(_log_failure, reason)
                    yield f"data: {json.dumps({'error': f'Translation failed: {reason}'})}\n\n"
                    return  # DỪNG STREAM

                restored_chunk = restore_formatting(chunk, translated_chunk)
                yield f"data: {json.dumps({'chunk': restored_chunk})}\n\n"
                final_translated_chunks.append(restored_chunk)
                
                newly_translated_mapping[chunk] = translated_chunk

                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                reason = str(e)
                logger.error(f"Chunk {i} translation raised exception: {reason}")
                await run_in_threadpool(_log_failure, reason)
                yield f"data: {json.dumps({'error': reason})}\n\n"
                return  # DỪNG STREAM

    translated_text = "".join(final_translated_chunks)

    # 4. Update Redis Cache in background
    if newly_translated_mapping:
        asyncio.create_task(mset_cached_translations(domain_str, newly_translated_mapping))

    # 5. Save and Log Success to DB
    def save_and_log_to_db():
        existing_translation = db_check_result.get("existing_translation")
        final_trans_id = None

        if translated_text != source_text:
            if existing_translation:
                existing_translation.translated_text = translated_text
                if hasattr(existing_translation, "provider"):
                    existing_translation.provider = provider
                else:
                    existing_translation.model_name = provider
                existing_translation.session_id = session_id
                final_trans_id = getattr(existing_translation, "id", getattr(existing_translation, "trans_id", None))
                if auto_commit:
                    db.commit()
            else:
                translation_data = {
                    "session_id": session_id,
                    "source_text": source_text,
                    "translated_text": translated_text,
                    "domain_id": domain_id_val,
                    "text_hash": text_hash,
                }
                if hasattr(Translation, "provider"):
                    translation_data["provider"] = provider
                else:
                    translation_data["model_name"] = provider

                translation = Translation(**translation_data)
                db.add(translation)
                db.flush()
                final_trans_id = getattr(translation, "id", getattr(translation, "trans_id", None))
                if auto_commit:
                    db.commit()
                    db.refresh(translation)
        else:
            if existing_translation:
                final_trans_id = getattr(existing_translation, "id", getattr(existing_translation, "trans_id", None))

        completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
        log_record = Logs(
            session_id=session_id,
            request_type=RequestTypeEnum.text,
            translation_id=final_trans_id,
            status=StatusEnum.success,
            request_time=request_time,
            completed_time=completed_time,
        )
        db.add(log_record)
        db.commit()

    # Sử dụng background_tasks thay vì chặn (block) response cuối cùng
    background_tasks.add_task(save_and_log_to_db)


# ==============================================================================
# HÀM 2: DÀNH CHO XỬ LÝ FILE (DOCX, PDF) - TRẢ VỀ STRING TĨNH, CHỊU LỖI CAO
# ==============================================================================
async def batch_translate_document(
    source_text: str,
    domain: str | None,
    session_id: str = "batch_file"
) -> str:
    """
    Dịch toàn bộ văn bản được trích xuất từ file.
    Trả về một chuỗi kết quả (string). Nếu một chunk bị lỗi, hệ thống sẽ tự động 
    lấy lại văn bản gốc của chunk đó để đảm bảo cấu trúc file không bị hỏng, 
    thay vì ngắt ngang toàn bộ quá trình.
    """
    domain_str = (domain or "general").strip().lower()

    # 1. Text Splitting
    chunks = split_text_into_chunks(source_text)
    if not chunks:
        return source_text

    logger.info(f"[BATCH FILE] Translating file text (session: {session_id}): split into {len(chunks)} chunks.")

    # 2. Redis Batch Check (MGET)
    cached_results = await mget_cached_translations(domain_str, chunks)
    
    final_translated_chunks = []
    newly_translated_mapping = {}

    for i, chunk in enumerate(chunks):
        cleaned_chunk = strictly_normalize_text(chunk)

        if not cleaned_chunk:
            final_translated_chunks.append(chunk)
            continue

        cached_val = cached_results.get(chunk)

        if cached_val is not None:
            restored_cached_val = restore_formatting(chunk, cached_val)
            final_translated_chunks.append(restored_cached_val)
        else:
            try:
                translated_chunk = await translate_chunk_async(cleaned_chunk, domain_str)

                # KIỂM TRA LỖI - FALLBACK VỀ TEXT GỐC THAY VÌ BÁO LỖI VÀ NGẮT
                _FAIL_PREFIXES = ("[ERROR", "[TIMEOUT]", "[FAILED]")
                if translated_chunk is None or translated_chunk.strip() == "" or any(translated_chunk.startswith(p) for p in _FAIL_PREFIXES):
                    logger.warning(f"⚠️ Chunk {i} translation failed in Batch Mode. Falling back to original text.")
                    final_translated_chunks.append(chunk) # Cứu file bằng cách trả về chunk gốc
                    continue

                restored_chunk = restore_formatting(chunk, translated_chunk)
                final_translated_chunks.append(restored_chunk)
                newly_translated_mapping[chunk] = translated_chunk

                # Sleep ngắn để giảm tải API
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"⚠️ Exception at chunk {i} in Batch Mode: {str(e)}. Falling back to original.")
                final_translated_chunks.append(chunk) # Lỗi API/Network vẫn trả về chunk gốc
                continue

    translated_text = "".join(final_translated_chunks)

    # 3. Update Redis Cache in background
    if newly_translated_mapping:
        asyncio.create_task(mset_cached_translations(domain_str, newly_translated_mapping))

    # Không lưu DB khối text lớn này để tránh làm phình Database (Cache chunk qua Redis đã đủ)
    
    return translated_text
