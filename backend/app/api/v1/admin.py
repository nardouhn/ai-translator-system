"""
Admin API Router
----------------
Endpoints dành riêng cho Admin Dashboard (CMS).
Tất cả routes đều yêu cầu ADMIN_API_KEY hợp lệ.

Bảo mật: truyền key qua một trong hai cách:
  - Header:  Authorization: Bearer <ADMIN_API_KEY>
  - Header:  X-API-Key: <ADMIN_API_KEY>
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import File, Logs, StatusEnum
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
    Dependency: kiểm tra ADMIN_API_KEY.
    Chấp nhận token từ:
      - Authorization: Bearer <token>
      - X-API-Key: <token>
    """
    expected = settings.admin_api_key

    if not expected:
        # Chưa cấu hình key → chặn toàn bộ để tránh lộ dữ liệu
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
    Trả về:
    - **total_files_translated**: tổng số file có status = 'success' trong bảng `file`
    - **total_tokens_consumed**: hiện tại schema chưa lưu tokens_used nên trả về 0.
      👉 Khi bảng có cột đó, thay bằng: `select(func.sum(YourModel.tokens_used))`
    """
    try:
        # ── Đếm file đã dịch thành công ────────────────────────────────────
        # Bảng: file  |  Cột trạng thái: status  |  Giá trị cần đếm: 'success'
        stmt_files = select(func.count(File.file_id)).where(
            File.status == StatusEnum.success
        )
        result_files = await db.execute(stmt_files)
        total_files: int = result_files.scalar_one() or 0

        # ── Tổng tokens đã dùng ────────────────────────────────────────────
        # TODO: Schema hiện tại (Logs) chưa có cột tokens_used.
        #       Khi thêm cột vào model, thay đoạn này:
        #
        #   from app.db.models import Logs
        #   stmt_tokens = select(func.sum(Logs.tokens_used))
        #   result_tokens = await db.execute(stmt_tokens)
        #   total_tokens: int = result_tokens.scalar_one() or 0
        #
        total_tokens: int = 0  # placeholder – thay thế khi có cột tokens_used

        return {
            "total_files_translated": total_files,
            "total_tokens_consumed": total_tokens,
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
    summary="Xóa toàn bộ Redis cache",
    dependencies=[Depends(verify_admin_key)],
)
async def clear_redis_cache():
    """
    Kết nối đến Upstash Redis và thực hiện FLUSHDB để xóa toàn bộ keys
    trong database hiện tại (database 0 theo mặc định của REDIS_URL).

    Nếu muốn chỉ xóa theo prefix (an toàn hơn), dùng pattern SCAN + DEL:
        async for key in redis_client.scan_iter("prefix:*"):
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

        # Xóa toàn bộ keys trong DB hiện tại
        await redis_client.flushdb(asynchronous=True)

        logger.info("Admin đã xóa toàn bộ Redis cache.")
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
