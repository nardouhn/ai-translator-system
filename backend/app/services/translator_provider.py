import asyncio
import httpx
import logging
from fastapi import HTTPException

# Setup logger
logger = logging.getLogger(__name__)

CUSTOM_MODEL_URL = "http://34.21.169.146:8001/translate"

# Limit concurrent requests to the local AI model to avoid overloading
# We use 2 to ensure stability with single GPU on Kaggle
concurrency_limit = asyncio.Semaphore(2)

_shared_client: httpx.AsyncClient | None = None

def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0),
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=5)
        )
    return _shared_client

async def translate_with_provider(
    source_text: str,
    domain: str = "General",
) -> tuple[str, str]:
    """
    Translates text using the custom ngrok endpoint with a concurrency limit and retry logic.
    """
    max_retries = 3
    
    async with concurrency_limit:
        client = get_shared_client()
        for attempt in range(max_retries + 1):
                try:
                    # Không tự ý đổi tên domain nữa để đồng bộ với API Model
                    api_domain = domain.lower()
                        
                    payload = {
                        "text": source_text,
                        "domain": api_domain
                    }
                    response = await client.post(CUSTOM_MODEL_URL, json=payload)
                    
                    if response.status_code >= 400:
                        error_msg = f"HTTP {response.status_code}"
                        try:
                            err_data = response.json()
                            if isinstance(err_data, dict) and "error" in err_data:
                                error_msg = err_data["error"]
                            else:
                                error_msg += f": {response.text}"
                        except Exception:
                            error_msg += f": {response.text}"
                            
                        logger.error(f"Lỗi TỪ CHỐI TỪ MODEL. HTTP Status: {response.status_code}")
                        logger.error(f"Chi tiết response body: {response.text}")
                            
                        if attempt < max_retries:
                            backoff = 2 ** (attempt + 1)
                            logger.warning(f"Translation attempt {attempt + 1} failed. Retrying in {backoff}s... Error: {error_msg}")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            # Do not crash the entire file translation on failure, just return original text
                            # with an error message so the file can continue
                            logger.error(f"Translation failed after {max_retries + 1} attempts. Error: {error_msg}")
                            return f"[ERROR: {error_msg}] {source_text}", "custom-ai"

                    data = response.json()
                    translated = data.get("translation", data.get("output", data.get("translated_text", source_text)))
                    
                    # Mandatory sleep to respect Ngrok rate limits and cool down GPU
                    await asyncio.sleep(2)
                    
                    return translated, "custom-ai"
                    
                except (httpx.TimeoutException, httpx.RequestError) as e:
                    logger.error(f"Lỗi TIMEOUT / NETWORK: {type(e).__name__} - {e}")
                    if attempt < max_retries:
                        backoff = 2 ** (attempt + 1)
                        logger.warning(f"Translation attempt {attempt + 1} failed for chunk. Retrying in {backoff}s... Error: {e}")
                        await asyncio.sleep(backoff) 
                    else:
                        logger.error(f"Translation failed after {max_retries + 1} attempts. Error: {e}")
                        return f"[TIMEOUT] {source_text}", "custom-ai"
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during translation: {e}")
                    return f"[ERROR] {source_text}", "custom-ai"
                
    return f"[FAILED] {source_text}", "custom-ai"

import re

async def translate_chunk_async(
    source_text: str,
    domain: str = "General",
) -> str:
    """
    Asynchronously translates a single chunk of text using the custom AI model.
    Assumes the caller (translation_service) has already split text into
    appropriate chunks via text_splitter.split_text_into_chunks().
    Do NOT re-split here — double-splitting corrupts sentence boundaries.
    """
    translated, _ = await translate_with_provider(source_text, domain)
    return translated

async def translate_batch_with_provider(
    texts: list[str],
    domain: str = "General",
) -> tuple[list[str], str]:
    if not texts:
        return [], "custom-ai"
    
    results = []
    for i, t in enumerate(texts):
        if not t.strip():
            results.append(t)
            continue
            
        translated_text = await translate_chunk_async(t, domain)
        results.append(translated_text)
        
        # Sleep to let Kaggle server breathe
        if i < len(texts) - 1:
            await asyncio.sleep(1)
            
    return results, "custom-ai"
