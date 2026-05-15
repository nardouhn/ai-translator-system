"""
Admin API Router – v2
=====================
Endpoints dành riêng cho Admin Dashboard (CMS).
Tất cả routes đều yêu cầu ADMIN_API_KEY hợp lệ.

Bảo mật – truyền key qua một trong hai header:
  Authorization: Bearer <ADMIN_API_KEY>
  X-API-Key: <ADMIN_API_KEY>

Endpoints:
  GET  /api/admin/stats        → Thống kê tổng hợp
  POST /api/admin/clear-cache  → Xóa toàn bộ Redis cache
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import File, Logs, RequestTypeEnum, Session, StatusEnum
from app.db.session import get_async_db
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# ---------------------------------------------------------------------------
# Security schemes
# ---------------------------------------------------------------------------
_bearer_scheme = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_admin_key(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
    x_api_key: str | None = Security(_api_key_header),
) -> None:
    """
    Dependency kiểm tra ADMIN_API_KEY.
    Ưu tiên: Authorization: Bearer → X-API-Key.
    """
    expected = settings.admin_api_key

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY chưa được cấu hình trên server.",
        )

    token: str | None = None
    if bearer is not None:
        token = bearer.credentials
    elif x_api_key is not None:
        token = x_api_key

    if not token or token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: API key không hợp lệ hoặc thiếu.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# API 1 – GET /api/admin/stats
# ---------------------------------------------------------------------------
@router.get(
    "/stats",
    summary="Thống kê tổng hợp cho Admin Dashboard",
    dependencies=[Depends(verify_admin_key)],
)
async def get_admin_stats(db: AsyncSession = Depends(get_async_db)):
    """
    Trả về các chỉ số:

    - **total_texts_translated** – logs có request_type='text' & status='success'
    - **total_files_translated** – logs có request_type='file' & status='success'
    - **total_data_processed_mb** – SUM(file.file_size) của file status='success', đổi sang MB
    - **total_sessions** – tổng số dòng trong bảng session
    - **error_rate_percent** – % dòng logs có status != 'success' trên tổng logs
    """
    try:
        # ── 1. Tổng bản dịch văn bản thành công ─────────────────────────────
        stmt_texts = select(func.count(Logs.log_id)).where(
            Logs.request_type == RequestTypeEnum.text,
            Logs.status == StatusEnum.success,
        )
        total_texts: int = (await db.execute(stmt_texts)).scalar_one() or 0

        # ── 2. Tổng file đã dịch thành công ──────────────────────────────────
        stmt_files = select(func.count(Logs.log_id)).where(
            Logs.request_type == RequestTypeEnum.file,
            Logs.status == StatusEnum.success,
        )
        total_files: int = (await db.execute(stmt_files)).scalar_one() or 0

        # ── 3. Tổng dữ liệu đã xử lý (MB) ───────────────────────────────────
        # SUM(file_size) bytes → đổi sang MB (1 MB = 1_048_576 bytes)
        stmt_size = select(func.sum(File.file_size)).where(
            File.status == StatusEnum.success
        )
        total_bytes: int = (await db.execute(stmt_size)).scalar_one() or 0
        total_mb = round(total_bytes / 1_048_576, 2)

        # ── 4. Tổng số sessions ───────────────────────────────────────────────
        stmt_sessions = select(func.count(Session.session_id))
        total_sessions: int = (await db.execute(stmt_sessions)).scalar_one() or 0

        # ── 5. Tỷ lệ lỗi (%) ─────────────────────────────────────────────────
        # error_rate = count(logs WHERE status != 'success') / count(*) * 100
        stmt_error = select(
            func.count(Logs.log_id).label("total"),
            func.sum(
                case((Logs.status != StatusEnum.success, 1), else_=0)
            ).label("errors"),
        )
        error_row = (await db.execute(stmt_error)).one()
        total_logs: int = error_row.total or 0
        error_count: int = int(error_row.errors or 0)
        error_rate = round((error_count / total_logs * 100), 2) if total_logs > 0 else 0.0

        return {
            "total_texts_translated": total_texts,
            "total_files_translated": total_files,
            "total_data_processed_mb": total_mb,
            "total_sessions": total_sessions,
            "error_rate_percent": error_rate,
        }

    except Exception as exc:
        logger.error("Lỗi khi lấy admin stats: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi truy vấn database: {exc}",
        )


# ---------------------------------------------------------------------------
# API 2 – POST /api/admin/clear-cache
# ---------------------------------------------------------------------------
@router.post(
    "/clear-cache",
    summary="Xóa toàn bộ Redis cache (Upstash)",
    dependencies=[Depends(verify_admin_key)],
)
async def clear_redis_cache():
    """
    Kết nối Upstash Redis qua redis.asyncio và gọi FLUSHDB.

    Nếu muốn chỉ xóa theo prefix (an toàn hơn), thay bằng:
        async for key in redis_client.scan_iter("cache:*"):
            await redis_client.delete(key)
    """
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )

        # Ping trước khi xóa để chắc chắn kết nối OK
        await redis_client.ping()

        # FLUSHDB xóa toàn bộ keys trong database hiện tại
        await redis_client.flushdb()

        logger.info("Admin: đã xóa toàn bộ Redis cache.")
        return {"status": "success", "message": "Redis cache cleared successfully"}

    except Exception as exc:
        logger.error("Lỗi khi xóa Redis cache: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể kết nối hoặc xóa Redis: {exc}",
        )
    finally:
        if redis_client:
            await redis_client.aclose()
