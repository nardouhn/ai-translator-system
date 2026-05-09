import hashlib
from app.services.redis_client import get_redis, get_async_redis

CACHE_TTL_SECONDS = 604800
MODEL_VERSION = "v4" # Bump version to clear old bad cache

import re

def strictly_normalize_text(text: str) -> str:
    """Collapses all whitespace, newlines, and invisible chars into a single space."""
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def generate_cache_key(domain: str, text: str, source_lang: str, target_lang: str) -> str:
    cleaned_text = strictly_normalize_text(text)
    text_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
    return f"translate:{MODEL_VERSION}:{domain.strip().lower()}:{source_lang.strip().lower()}:{target_lang.strip().lower()}:{text_hash}"

async def get_cached_translation(domain: str, text: str, source_lang: str, target_lang: str) -> str | None:
    if len(text) > 5000:
        return None

    redis_client = get_async_redis()
    key = generate_cache_key(domain, text, source_lang, target_lang)
    cached_value = await redis_client.get(key)
    if cached_value:
        return cached_value
    return None

async def set_cached_translation(domain: str, text: str, translated_text: str, source_lang: str, target_lang: str) -> None:
    if len(text) > 5000:
        return

    redis_client = get_async_redis()
    key = generate_cache_key(domain, text, source_lang, target_lang)
    await redis_client.setex(key, CACHE_TTL_SECONDS, translated_text)

async def mget_cached_translations(domain: str, chunks: list[str], source_lang: str, target_lang: str) -> dict[str, str | None]:
    if not chunks:
        return {}

    async_redis = get_async_redis()
    keys = [generate_cache_key(domain, chunk, source_lang, target_lang) for chunk in chunks]
    
    cached_values = await async_redis.mget(keys)
    
    result = {}
    for chunk, value in zip(chunks, cached_values):
        result[chunk] = value
    return result

async def mset_cached_translations(domain: str, mapping: dict[str, str], source_lang: str, target_lang: str) -> None:
    if not mapping:
        return

    async_redis = get_async_redis()
    
    pipeline = async_redis.pipeline()
    for chunk, translated_text in mapping.items():
        if len(chunk) <= 5000:
            key = generate_cache_key(domain, chunk, source_lang, target_lang)
            pipeline.setex(key, CACHE_TTL_SECONDS, translated_text)
            
    await pipeline.execute()
