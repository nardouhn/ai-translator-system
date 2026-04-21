from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Import Base và settings của bạn
from app.db.base import Base
from app.db import models  # noqa
from app.settings import settings

# 1. Lấy cấu hình từ alembic.ini
config = context.config

# 2. Ưu tiên lấy Database URL từ biến môi trường (Docker dùng cái này)
# Nếu không có biến môi trường thì mới dùng từ file settings
db_url = os.getenv("DATABASE_URL", settings.database_url)
config.set_main_option("sqlalchemy.url", db_url)

# 3. Cấu hình Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. Metadata để Alembic tự động phát hiện thay đổi trong models
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Chạy migrations ở chế độ 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Chạy migrations ở chế độ 'online'."""
    # Sử dụng URL đã được chuẩn hóa ở bước 2
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()