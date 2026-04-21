"""initial schema based on sql spec

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-14 17:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute("CREATE TYPE file_type_t AS ENUM ('docx', 'txt');")
    op.execute("CREATE TYPE request_type_t AS ENUM ('text', 'file');")
    op.execute("CREATE TYPE status_t AS ENUM ('pending', 'success', 'error');")
    op.execute("CREATE TYPE domain_name_t AS ENUM ('general', 'business', 'technical', 'medical');")

    op.create_table(
        "language",
        sa.Column("lang_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lang_code", sa.String(length=10), nullable=False),
        sa.Column("lang_name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("lang_id"),
        sa.UniqueConstraint("lang_code"),
    )

    op.create_table(
        "domain",
        sa.Column("domain_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "domain_name",
            postgresql.ENUM("general", "business", "technical", "medical", name="domain_name_t", create_type=False),
            server_default="general",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("domain_id"),
    )

    op.create_table(
        "session",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "translation",
        sa.Column("trans_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("source_lang", sa.Integer(), nullable=False),
        sa.Column("target_lang", sa.Integer(), nullable=False),
        sa.Column("domain_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["domain_id"], ["domain.domain_id"], name="fk_translation_domain"),
        sa.ForeignKeyConstraint(["session_id"], ["session.session_id"], name="fk_translation_session"),
        sa.ForeignKeyConstraint(["source_lang"], ["language.lang_id"], name="fk_translation_source_lang"),
        sa.ForeignKeyConstraint(["target_lang"], ["language.lang_id"], name="fk_translation_target_lang"),
        sa.PrimaryKeyConstraint("trans_id"),
    )
    op.create_index("idx_translation_lang", "translation", ["source_lang", "target_lang"], unique=False)
    op.create_index("idx_translation_domain", "translation", ["domain_id"], unique=False)
    op.create_index(
        "uniq_translation_cache",
        "translation",
        ["text_hash", "source_lang", "target_lang", "domain_id"],
        unique=True,
    )

    op.create_table(
        "file",
        sa.Column("file_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("translated_filename", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("source_lang", sa.Integer(), nullable=True),
        sa.Column("target_lang", sa.Integer(), nullable=True),
        sa.Column("domain_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("file_type", postgresql.ENUM("docx", "txt", name="file_type_t", create_type=False), nullable=True),
        sa.ForeignKeyConstraint(["domain_id"], ["domain.domain_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.session_id"]),
        sa.ForeignKeyConstraint(["source_lang"], ["language.lang_id"]),
        sa.ForeignKeyConstraint(["target_lang"], ["language.lang_id"]),
        sa.PrimaryKeyConstraint("file_id"),
    )

    op.create_table(
        "file_segment",
        sa.Column("segment_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("text_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("segment_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["file.file_id"]),
        sa.PrimaryKeyConstraint("segment_id"),
    )
    op.create_index("idx_file_segment_file", "file_segment", ["file_id"], unique=False)

    op.create_table(
        "logs",
        sa.Column("log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("request_type", postgresql.ENUM("text", "file", name="request_type_t", create_type=False), nullable=True),
        sa.Column("translation_id", sa.BigInteger(), nullable=True),
        sa.Column("file_id", sa.BigInteger(), nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "success", "error", name="status_t", create_type=False), nullable=True),
        sa.Column("request_time", sa.DateTime(), nullable=True),
        sa.Column("completed_time", sa.DateTime(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["file.file_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.session_id"]),
        sa.ForeignKeyConstraint(["translation_id"], ["translation.trans_id"]),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("idx_logs_time", "logs", ["request_time"], unique=False)
    op.create_index("idx_logs_session", "logs", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_logs_session", table_name="logs")
    op.drop_index("idx_logs_time", table_name="logs")
    op.drop_table("logs")
    op.drop_index("idx_file_segment_file", table_name="file_segment")
    op.drop_table("file_segment")
    op.drop_table("file")
    op.drop_index("uniq_translation_cache", table_name="translation")
    op.drop_index("idx_translation_domain", table_name="translation")
    op.drop_index("idx_translation_lang", table_name="translation")
    op.drop_table("translation")
    op.drop_table("session")
    op.drop_table("domain")
    op.drop_table("language")
    op.execute("DROP TYPE IF EXISTS status_t;")
    op.execute("DROP TYPE IF EXISTS request_type_t;")
    op.execute("DROP TYPE IF EXISTS file_type_t;")
    op.execute("DROP TYPE IF EXISTS domain_name_t;")
