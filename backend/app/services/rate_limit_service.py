from fastapi import HTTPException, status

from app.services.redis_client import get_async_redis

RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_WINDOW_SECONDS = 60


async def check_rate_limit(session_id: str):
    redis_client = get_async_redis()
    key = f"rate_limit:{session_id}"

    # Atomic INCR + EXPIRE via pipeline — prevents key living forever if server
    # crashes between the two commands (race condition fix).
    async with redis_client.pipeline(transaction=False) as pipe:
        pipe.incr(key)
        pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
        results = await pipe.execute()

    current_count = results[0]

    if current_count > RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
        )
