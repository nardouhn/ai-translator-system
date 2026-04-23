import hashlib
from app.services.redis_client import get_redis, get_async_redis

CACHE_TTL_SECONDS = 86400
MODEL_VERSION = "v3" # Bump version to clear old bad cache

def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())

def get_cache_key(domain: str, text: str, source_lang: str = None, target_lang: str = None) -> str:
    normalized_text = normalize_text(text)
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    # Using the user's requested format: translate:{domain}:{hash}
    # We include MODEL_VERSION to avoid collisions with old cache format if any
    return f"translate:{MODEL_VERSION}:{domain.lower()}:{text_hash}"

def get_cached_translation(domain: str, text: str) -> str | None:
    if len(text) > 5000:
        return None

    redis_client = get_redis()
    key = get_cache_key(domain, text)
    cached_value = redis_client.get(key)
    if cached_value:
        return cached_value
    return None

def set_cached_translation(domain: str, text: str, translated_text: str) -> None:
    if len(text) > 5000:
        return

    redis_client = get_redis()
    key = get_cache_key(domain, text)
    redis_client.setex(key, CACHE_TTL_SECONDS, translated_text)

async def mget_cached_translations(domain: str, chunks: list[str]) -> dict[str, str | None]:
    if not chunks:
        return {}

    async_redis = get_async_redis()
    keys = [get_cache_key(domain, chunk) for chunk in chunks]
    
    cached_values = await async_redis.mget(keys)
    
    result = {}
    for chunk, value in zip(chunks, cached_values):
        result[chunk] = value
    return result

async def mset_cached_translations(domain: str, mapping: dict[str, str]) -> None:
    if not mapping:
        return

    async_redis = get_async_redis()
    
    pipeline = async_redis.pipeline()
    for chunk, translated_text in mapping.items():
        if len(chunk) <= 5000:
            key = get_cache_key(domain, chunk)
            pipeline.setex(key, CACHE_TTL_SECONDS, translated_text)
            
    await pipeline.execute()
