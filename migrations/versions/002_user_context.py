"""Migration 002: user context and proactive outreach fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("context_summary", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("schedule", sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column(
        "users",
        sa.Column("last_proactive_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("users", sa.Column("nudges_today_count", sa.SmallInteger(), server_default="0"))
    op.add_column("users", sa.Column("nudges_today_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "nudges_today_date")
    op.drop_column("users", "nudges_today_count")
    op.drop_column("users", "last_proactive_at")
    op.drop_column("users", "schedule")
    op.drop_column("users", "context_summary")
