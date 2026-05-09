from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_async_db
from app.services.redis_client import get_async_redis
from app.services.storage_service import StorageService
import aioboto3

router = APIRouter()

@router.get("/test-cloud")
async def test_cloud_connections(db: AsyncSession = Depends(get_async_db)):
    status_report = {}

    # 1. Test Postgres (Supabase)
    try:
        await db.execute(text("SELECT 1"))
        status_report["postgres"] = "✅ Thành công"
    except Exception as e:
        status_report["postgres"] = f"❌ Thất bại: {str(e)}"

    # 2. Test Redis (Upstash)
    try:
        redis = get_async_redis()
        response = await redis.ping()
        if response:
            status_report["redis"] = "✅ Thành công"
        else:
            status_report["redis"] = "❌ Thất bại: Không nhận được PONG"
    except Exception as e:
        status_report["redis"] = f"❌ Thất bại: {str(e)}"

    # 3. Test Cloudflare R2
    try:
        session = aioboto3.Session()
        async with session.client(**StorageService.get_s3_client_args()) as s3_client:
            # Dùng head_bucket thay vì list_buckets vì token R2 thường bị giới hạn quyền truy cập ở cấp độ Bucket
            from app.settings import settings
            await s3_client.head_bucket(Bucket=settings.r2_bucket_name)
            status_report["cloudflare_r2"] = "✅ Thành công"
    except Exception as e:
        status_report["cloudflare_r2"] = f"❌ Thất bại: {str(e)}"

    return status_report
