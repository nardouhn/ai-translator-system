"""Add processing and failed to StatusEnum

Revision ID: 97f6da3c2dcc
Revises: 13681f676df0
Create Date: 2026-05-09 02:38:03.571016
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97f6da3c2dcc'
down_revision: Union[str, Sequence[str], None] = '13681f676df0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE status_t ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TYPE status_t ADD VALUE IF NOT EXISTS 'failed'")


def downgrade() -> None:
    pass
