import hashlib
import asyncio
import logging
from fastapi import BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session as DBSession

from app.db.models import Domain, DomainNameEnum, Translation
from app.services.cache_service import get_cached_translation, set_cached_translation, mget_cached_translations, mset_cached_translations
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


import json

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
    
    for i, chunk in enumerate(chunks):
        from app.services.cache_service import strictly_normalize_text
        cleaned_chunk = strictly_normalize_text(chunk)
        cached_val = cached_results.get(chunk)
        debug_hash = __import__('hashlib').sha256(cleaned_chunk.encode("utf-8")).hexdigest()
        logger.debug(f"Text Cache Key: translate:v5:{domain_str}:en:vi:{debug_hash} | Text: '{cleaned_chunk[:20]}'")
        
        if cached_val is not None:
            logger.info(f"🟢 CACHE HIT for chunk: '{cleaned_chunk[:20]}...'")
            yield f"data: {json.dumps({'chunk': cached_val})}\n\n"
            final_translated_chunks.append(cached_val)
        else:
            logger.warning(f"🔴 CACHE MISS for chunk: '{cleaned_chunk[:20]}...'. Calling Kaggle...")
            try:
                translated_chunk = await translate_chunk_async(chunk, domain_str)
                if translated_chunk is None or translated_chunk == chunk:
                    logger.error(f"Chunk {i} translation returned identical text, treating as failure.")
                    from fastapi import HTTPException
                    raise HTTPException(status_code=502, detail="Translation API returned identical source text.")
                
                yield f"data: {json.dumps({'chunk': translated_chunk})}\n\n"
                final_translated_chunks.append(translated_chunk)
                newly_translated_mapping[chunk] = translated_chunk
                
                if i < len(chunks) - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Chunk {i} translation failed: {e}")
                # We yield an error event so the client knows
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

    translated_text = "".join(final_translated_chunks)
    
    # 6. Update Cache (MSET) in background
    if newly_translated_mapping:
        asyncio.create_task(mset_cached_translations(domain_str, newly_translated_mapping))

    # 7. Database Logging
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
    
    # Log operations to DB before closing
    def log_operations():
        from app.db.models import Logs, StatusEnum, RequestTypeEnum
        from datetime import datetime, timezone
        completed_time = datetime.now(timezone.utc)
        
        log_status = getattr(StatusEnum, "cache_hit", StatusEnum.success) if len(newly_translated_mapping) == 0 else StatusEnum.success
        log_record = Logs(
            session_id=session_id,
            request_type=getattr(RequestTypeEnum, "text", "text"),
            translation_id=final_trans_id,
            status=log_status,
            request_time=request_time,
            completed_time=completed_time,
        )
        db.add(log_record)
        db.commit()

    await run_in_threadpool(log_operations)
