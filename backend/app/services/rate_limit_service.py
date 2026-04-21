from fastapi import HTTPException, status

from app.services.redis_client import get_redis

RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit(session_id: str):
    redis_client = get_redis()
    key = f"rate_limit:{session_id}"

    current_count = redis_client.incr(key)
    if current_count == 1:
        redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

    if current_count > RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
        )
