import asyncio
import httpx
import logging

# Setup logger
logger = logging.getLogger(__name__)

CUSTOM_MODEL_URL = "https://luncheon-scorebook-daylight.ngrok-free.dev/translate"

# Limit concurrent requests to the local AI model to avoid overloading
# We use 2 to ensure stability with single GPU on Kaggle
concurrency_limit = asyncio.Semaphore(2)

async def translate_with_provider(
    source_text: str,
    source_lang: str,
    target_lang: str,
    domain: str = "General",
) -> tuple[str, str]:
    """
    Translates text using the custom ngrok endpoint with a concurrency limit and retry logic.
    """
    max_retries = 2
    # Increase timeout significantly because chunks are queued on GPU
    timeout = httpx.Timeout(300.0)
    
    async with concurrency_limit:
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    payload = {
                        "text": source_text,
                        "domain": domain
                    }
                    response = await client.post(CUSTOM_MODEL_URL, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    # The Kaggle server returns 'output', not 'translated_text'
                    translated = data.get("output", source_text)
                    return translated, "custom-ai"
            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                if attempt < max_retries:
                    logger.warning(f"Translation attempt {attempt + 1} failed for chunk. Retrying... Error: {e}")
                    await asyncio.sleep(1) 
                else:
                    logger.error(f"Translation failed after {max_retries + 1} attempts. Error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during translation: {e}")
                break 
                
    # Return original text as fallback without the prefix as requested
    return source_text, "fallback"

async def translate_chunk_async(
    source_text: str,
    source_lang: str,
    target_lang: str,
    domain: str = "General",
) -> str:
    """
    Asynchronously translates a chunk of text using the custom AI model.
    """
    translated, _ = await translate_with_provider(
        source_text,
        source_lang,
        target_lang,
        domain
    )
    return translated

import re

async def translate_batch_with_provider(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    domain: str = "General",
) -> tuple[list[str], str]:
    if not texts:
        return [], "custom-ai"
    
    # The semaphore inside translate_with_provider will handle concurrency limit automatically
    tasks = [translate_chunk_async(t, source_lang, target_lang, domain) for t in texts]
    results = await asyncio.gather(*tasks)
    return list(results), "custom-ai"
