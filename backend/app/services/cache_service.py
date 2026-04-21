import hashlib
from app.services.redis_client import get_redis

CACHE_TTL_SECONDS = 86400
MODEL_VERSION = "v1"


def normalize_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def get_cache_key(source_lang: str, target_lang: str, text: str) -> str:
    normalized_text = normalize_text(text)
    text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"translate:{MODEL_VERSION}:{source_lang}:{target_lang}:{text_hash}"


def get_cached_translation(source_lang: str, target_lang: str, text: str) -> str | None:
    if len(text) > 5000:
        return None

    redis_client = get_redis()
    key = get_cache_key(source_lang, target_lang, text)
    cached_value = redis_client.get(key)
    if cached_value:
        return cached_value
    return None


def set_cached_translation(source_lang: str, target_lang: str, text: str, translated_text: str) -> None:
    if len(text) > 5000:
        return

    redis_client = get_redis()
    key = get_cache_key(source_lang, target_lang, text)
    redis_client.setex(key, CACHE_TTL_SECONDS, translated_text)
