import redis.asyncio as aioredis
from redis.asyncio import Redis, ConnectionPool
from app.settings import settings

redis_pool = None

def get_async_redis() -> Redis:
    global redis_pool
    if redis_pool is None:
        redis_url = settings.redis_url

        
        # Determine if SSL is needed based on the protocol
        # For Upstash rediss://, we should set ssl_cert_reqs="none" to avoid certificate errors
        kwargs = {"decode_responses": True}
        if redis_url.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = "none"
            
        redis_pool = ConnectionPool.from_url(redis_url, **kwargs)
        
    return Redis(connection_pool=redis_pool)
