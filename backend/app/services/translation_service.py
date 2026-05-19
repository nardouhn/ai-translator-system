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
                status=
