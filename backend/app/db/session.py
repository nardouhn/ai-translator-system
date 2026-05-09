from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.settings import settings

# Setup SSL for Supabase if needed
sync_connect_args = {}
async_connect_args = {}
if "supabase.com" in settings.database_url:
    sync_connect_args["sslmode"] = "require"
    async_connect_args["ssl"] = "require"

# Setup Sync Engine
# pool_pre_ping: Check connection is still alive before using it
# pool_recycle: Prevent idle connections from timing out on Supabase
# pool_size, max_overflow: Manage connection limits
engine = create_engine(
    settings.database_url, 
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=15,
    connect_args=sync_connect_args
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

# Setup Async Engine
# Convert 'postgres://' or 'postgresql://' to 'postgresql+asyncpg://'
async_db_url = settings.database_url
if async_db_url.startswith("postgres://"):
    async_db_url = async_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif async_db_url.startswith("postgresql://"):
    async_db_url = async_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

async_engine = create_async_engine(
    async_db_url, 
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=15,
    connect_args=async_connect_args
)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=AsyncSession)

def get_engine() -> Engine:
    return engine

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
