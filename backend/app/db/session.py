"""
Database Session – Supabase PostgreSQL
======================================
Chuỗi kết nối đúng từ Supabase Dashboard:

  Project Settings → Database → Connection string → URI

Có 2 lựa chọn cổng:
  - Cổng 5432  (Direct / Session mode)  → dùng cho local dev, migrations, CLI
  - Cổng 6543  (Transaction Pooler)     → dùng cho production / serverless

Với SQLAlchemy connection pool thường trực (không serverless), dùng cổng 5432.

Format chuỗi đúng:
  postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

KHÔNG cần thêm ?pgbouncer=true nếu dùng cổng 5432 Session mode.
Chỉ thêm ?pgbouncer=true khi dùng cổng 6543 Transaction Pooler với psycopg2.
"""

from __future__ import annotations

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chuẩn hoá URL
# ---------------------------------------------------------------------------
def _make_sync_url(url: str) -> str:
    """Đảm bảo dùng driver postgresql:// cho psycopg2/psycopg."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # Bỏ pgbouncer param nếu có (không cần với session mode 5432)
    return url.split("?")[0]


def _make_async_url(url: str) -> str:
    """Chuyển sang driver asyncpg cho async engine."""
    url = _make_sync_url(url)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


_sync_url = _make_sync_url(settings.database_url)
_async_url = _make_async_url(settings.database_url)

# ---------------------------------------------------------------------------
# SSL (Supabase yêu cầu SSL khi kết nối qua internet)
# ---------------------------------------------------------------------------
_sync_connect_args: dict = {}
_async_connect_args: dict = {}

if "supabase.com" in settings.database_url:
    _sync_connect_args["sslmode"] = "require"
    # asyncpg dùng bool/string khác với psycopg2
    _async_connect_args["ssl"] = "require"

# ---------------------------------------------------------------------------
# Sync Engine (dùng cho Alembic migrations và code sync)
# ---------------------------------------------------------------------------
# pool_pre_ping=True   : kiểm tra connection còn sống trước khi dùng
# pool_recycle=1800    : đóng/tái tạo connection sau 30 phút (tránh timeout Supabase)
# pool_size=5          : số connection thường trực tối đa
# max_overflow=10      : số connection tạm thời khi pool đầy
engine: Engine = create_engine(
    _sync_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    connect_args=_sync_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, _connection_record):
    logger.debug("Sync DB connection established: %s", dbapi_conn)


# ---------------------------------------------------------------------------
# Async Engine (dùng cho FastAPI async endpoints)
# ---------------------------------------------------------------------------
async_engine = create_async_engine(
    _async_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    connect_args=_async_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------
def get_engine() -> Engine:
    return engine


def get_db():
    """Sync session dependency cho Alembic / sync routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Async session dependency cho FastAPI async routes."""
    async with AsyncSessionLocal() as db:
        yield db


# ---------------------------------------------------------------------------
# Health check helper (gọi khi startup để xác nhận kết nối)
# ---------------------------------------------------------------------------
async def check_db_connection() -> bool:
    """Ping database, trả về True nếu OK."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection OK")
        return True
    except Exception as exc:
        logger.error("❌ Database connection FAILED: %s", exc)
        return False
