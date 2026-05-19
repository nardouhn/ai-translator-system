import hashlib
import asyncio
import logging
import json
import re
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession

from app.db.models import Domain, DomainNameEnum, Translation
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


async def stream_translate_text(
    db: DBSession,
    session_id: str,
    source_text: str,
    domain: str | None,
    background_tasks: BackgroundTasks,
    request_time: __import__('datetime').datetime | None = None,
    ip_address: str | None = None,
    auto_commit: bool = True,
):
    domain_str = (domain or "general").strip().lower()
    domain_id_val = map_domain_to_id(domain_str)

    if request_time and request_time.tzinfo:
        request_time = request_time.replace(tzinfo=None)

    hash_string = f"{domain_id_val}_{source_text}"
    text_hash = hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

    # 1. Check DB first (Synchronous operations wrapped in threadpool)
    def check_db():
        # Check DB cache
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
    
    logger.info(f"Translating text (session: {session_id}): split into {len(chunks)} chunks.")

    # 3. Redis Batch Check (MGET)
    cached_results = await mget_cached_translations(domain_str, chunks)
    
    final_translated_chunks = []
    newly_translated_mapping = {}
    provider = "custom-ai"

    # ── Helper: ghi log thất bại vào DB ────────────────────────────────────
    def _log_failure(reason: str):
        from app.db.models import Logs, StatusEnum, RequestTypeEnum
        from datetime import datetime, timezone
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

        # Chunk chỉ toàn invisible chars/khoảng trắng/xuống dòng → trả về nguyên gốc
        if not cleaned_chunk:
            logger.debug(f"Chunk {i} is empty after normalization, yielding original.")
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            final_translated_chunks.append(chunk)
            continue

        cached_val = cached_results.get(chunk)
        debug_hash = hashlib.sha256(cleaned_chunk.encode("utf-8")).hexdigest()
        logger.debug(f"Text Cache Key: translate:{MODEL_VERSION}:{domain_str}:en:vi:{debug_hash} | Text: '{cleaned_chunk[:20]}'")

        if cached_val is not None:
            logger.info(f"🟢 CACHE HIT for chunk: '{cleaned_chunk[:20]}...'")
            restored_cached_val = restore_formatting(chunk, cached_val)
            yield f"data: {json.dumps({'chunk': restored_cached_val})}\n\n"
            final_translated_chunks.append(restored_cached_val)
        else:
            logger.warning(f"🔴 CACHE MISS for chunk: '{cleaned_chunk[:20]}...'. Calling AI...")
            try:
                # Gửi text đã normalize cho AI để tránh invisible chars làm model bị lỗi
                translated_chunk = await translate_chunk_async(cleaned_chunk, domain_str)

                # --- Kiểm tra kết quả thất bại từ AI ---
                _FAIL_PREFIXES = ("[ERROR", "[TIMEOUT]", "[FAILED]")
                if translated_chunk is None or translated_chunk.strip() == "":
                    reason = "AI trả về kết quả rỗng (empty output)"
                    logger.error(f"❌ Translation FAILED (chunk {i}): {reason}")
                    _log_failure(reason)
                    yield f"data: {json.dumps({'error': f'Translation failed: {reason}'})}\n\n"
                    return  # Dừng stream, không lưu cache

                if any(translated_chunk.startswith(p) for p in _FAIL_PREFIXES):
                    reason = translated_chunk.split("]")[0] + "]" if "]" in translated_chunk else translated_chunk[:80]
                    logger.error(f"❌ Translation FAILED (chunk {i}): {reason}")
                    _log_failure(reason)
                    yield f"data: {json.dumps({'error': f'Translation failed: {reason}'})}\n\n"
                    return  # Dừng stream, không lưu cache

                if translated_chunk == cleaned_chunk:
                    logger.warning(f"Chunk {i} translation returned identical text, keeping it.")

                # Khôi phục khoảng trắng/xuống dòng trước khi stream về client
                restored_chunk = restore_formatting(chunk, translated_chunk)
                yield f"data: {json.dumps({'chunk': restored_chunk})}\n\n"
                final_translated_chunks.append(restored_chunk)
                
                # Lưu cache với key là chunk gốc, value là kết quả trả về trực tiếp từ AI (chưa thêm format)
                newly_translated_mapping[chunk] = translated_chunk

                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                reason = str(e)
                logger.error(f"Chunk {i} translation raised exception: {reason}")
                _log_failure(reason)
                # Trả về nguyên gốc thay vì quăng lỗi nếu muốn ứng dụng chạy tiếp (tùy logic của bạn)
                yield f"data: {json.dumps({'error': reason})}\n\n"
                return

    translated_text = "".join(final_translated_chunks)

    # 6. Update Cache (MSET) in background — chỉ khi có kết quả thành công
    if newly_translated_mapping:
        asyncio.create_task(mset_cached_translations(domain_str, newly_translated_mapping))

    # 7. Database Logging — lưu bản dịch + log success
    def save_to_db():
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

        return final_trans_id

    final_trans_id = await run_in_threadpool(save_to_db)

    # Log success
    def log_operations():
        from app.db.models import Logs, StatusEnum, RequestTypeEnum
        from datetime import datetime, timezone
        completed_time = datetime.now(timezone.utc).replace(tzinfo=None)
        log_status = StatusEnum.success
        log_record = Logs(
            session_id=session_id,
            request_type=RequestTypeEnum.text,
            translation_id=final_trans_id,
            status=log_status,
            request_time=request_time,
            completed_time=completed_time,
        )
        db.add(log_record)
        db.commit()

    await run_in_threadpool(log_operations)
