import os
from redis import Redis
import redis.asyncio as aioredis

redis_client = None
async_redis_client = None

def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(redis_url, decode_responses=True)
    return redis_client

def get_async_redis() -> aioredis.Redis:
    global async_redis_client
    if async_redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        async_redis_client = aioredis.from_url(redis_url, decode_responses=True)
    return async_redis_client