from redis import Redis

redis_client = None


def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    return redis_client
