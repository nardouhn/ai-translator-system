import hashlib

from sqlalchemy.orm import Session as DBSession

from app.db.models import Domain, DomainNameEnum, Language, Translation
from app.services.cache_service import get_cached_translation, set_cached_translation
from app.services.translator_provider import translate_with_provider


def _get_or_create_language(db: DBSession, lang_code: str) -> Language:
    normalized_code = lang_code.strip().lower()
    language = db.query(Language).filter(Language.lang_code == normalized_code).first()
    if language:
        return language

    language = Language(
        lang_code=normalized_code,
        lang_name=normalized_code.upper(),
    )
    db.add(language)
    db.flush()
    return language


def _get_or_create_domain(db: DBSession, domain: str | None) -> Domain:
    domain_value = (domain or DomainNameEnum.general.value).strip().lower()
    allowed_values = {item.value for item in DomainNameEnum}
    if domain_value not in allowed_values:
        domain_value = DomainNameEnum.general.value

    domain_row = db.query(Domain).filter(Domain.domain_name == domain_value).first()
    if domain_row:
        return domain_row

    domain_row = Domain(domain_name=DomainNameEnum(domain_value))
    db.add(domain_row)
    db.flush()
    return domain_row


async def translate_text(
    db,
    session_id: str,
    source_text: str,
    source_lang: str,
    target_lang: str,
    domain: str | None,
    auto_commit: bool = True,
):
    from fastapi.concurrency import run_in_threadpool
    from app.services.text_splitter import split_text_into_chunks
    from app.services.cache_service import mget_cached_translations, mset_cached_translations
    from app.services.translator_provider import translate_chunk_async
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    # Ensure domain is a string for cache key logic
    domain_str = (domain or DomainNameEnum.general.value).strip().lower()

    # 1. Text Splitting
    chunks = split_text_into_chunks(source_text)
    if not chunks:
        return {
            "translated_text": "",
            "translation_id": None,
            "from_cache": True,
        }
    
    logger.info(f"Translating text (session: {session_id}): split into {len(chunks)} chunks.")

    # 2. Redis Batch Check (MGET) - Now passing domain_str
    cached_results = await mget_cached_translations(domain_str, chunks)
    
    # 3. Classify Hit/Miss
    hit_chunks = {}
    miss_chunks = []
    
    for i, chunk in enumerate(chunks):
        cached_val = cached_results.get(chunk)
        if cached_val is not None:
            hit_chunks[i] = cached_val
        else:
            miss_chunks.append((i, chunk))

    # 4. Parallel Translation for Misses
    translated_misses = {}
    newly_translated_mapping = {}
    provider = "custom-ai"
    
    if miss_chunks:
        # Create a list of tasks - Now passing domain_str
        tasks = [
            translate_chunk_async(chunk, source_lang, target_lang, domain_str)
            for _, chunk in miss_chunks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        i_miss = 0
        for (i, chunk) in miss_chunks:
            translated_chunk = results[i_miss] if i_miss < len(results) else None
            i_miss += 1
            
            if translated_chunk is None or isinstance(translated_chunk, Exception) or translated_chunk == chunk:
                # Fallback to original text if exception occurred or result is same as source (failure)
                translated_misses[i] = chunk
                if isinstance(translated_chunk, Exception):
                    logger.error(f"Chunk {i} translation failed: {translated_chunk}")
            else:
                translated_misses[i] = translated_chunk
                newly_translated_mapping[chunk] = translated_chunk

    # 5. Update Cache (MSET) in background - Now passing domain_str
    if newly_translated_mapping:
        asyncio.create_task(mset_cached_translations(domain_str, newly_translated_mapping))

    # 6. Reassembly - Join without extra spaces because separators are already in chunks
    final_translated_chunks = []
    for i in range(len(chunks)):
        if i in hit_chunks:
            final_translated_chunks.append(hit_chunks[i])
        else:
            final_translated_chunks.append(translated_misses[i])
            
    translated_text = "".join(final_translated_chunks)
    
    # 7. Database Logging (Synchronous operations wrapped in threadpool)
    def db_operations():
        source_language = _get_or_create_language(db, source_lang)
        target_language = _get_or_create_language(db, target_lang)
        domain_row = _get_or_create_domain(db, domain)

        text_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

        # Check DB cache
        existing_translation = db.query(Translation).filter(
            Translation.text_hash == text_hash,
            Translation.source_lang == source_language.lang_id,
            Translation.target_lang == target_language.lang_id,
            Translation.domain_id == domain_row.domain_id
        ).first()

        # If it exists and is a GOOD translation, return it
        if existing_translation and existing_translation.translated_text != source_text:
            return {
                "translated_text": existing_translation.translated_text,
                "translation_id": getattr(existing_translation, "id", getattr(existing_translation, "trans_id", None)),
                "from_cache": True,
            }

        # Otherwise, prepare to Save/Update
        translation_data = {
            "session_id": session_id,
            "source_text": source_text,
            "translated_text": translated_text,
            "source_lang": source_language.lang_id,
            "target_lang": target_language.lang_id,
            "domain_id": domain_row.domain_id,
            "text_hash": text_hash,
        }
        if hasattr(Translation, "provider"):
            translation_data["provider"] = provider
        else:
            translation_data["model_name"] = provider

        final_trans_id = None
        # Only save/update if it's a real translation (different from source)
        if translated_text != source_text:
            if existing_translation:
                # UPDATE existing bad record instead of INSERT
                existing_translation.translated_text = translated_text
                if hasattr(existing_translation, "provider"):
                    existing_translation.provider = provider
                else:
                    existing_translation.model_name = provider
                existing_translation.session_id = session_id
                final_trans_id = getattr(existing_translation, "id", getattr(existing_translation, "trans_id", None))
            else:
                # INSERT new record
                translation = Translation(**translation_data)
                db.add(translation)
                db.flush() # Get the ID
                final_trans_id = getattr(translation, "id", getattr(translation, "trans_id", None))
            
            if auto_commit:
                db.commit()
                if not existing_translation:
                    db.refresh(translation)

        return {
            "translated_text": translated_text,
            "translation_id": final_trans_id,
            "from_cache": len(miss_chunks) == 0 and translated_text != source_text,
        }

    return await run_in_threadpool(db_operations)
