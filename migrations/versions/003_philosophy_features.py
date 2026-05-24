"""Migration 003: philosophy features — dreams, shadow, stoic rituals, CBT, preferences."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferences", postgresql.JSONB(), nullable=True, server_default="{}"),
    )

    op.create_table(
        "dream_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("symbols", postgresql.JSONB(), nullable=True),
        sa.Column("mood", sa.String(100), nullable=True),
        sa.Column("ai_interpretation", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dream_entries_user_logged", "dream_entries", ["user_id", "logged_at"])

    op.create_table(
        "shadow_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("ai_reflection", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shadow_notes_user_logged", "shadow_notes", ["user_id", "logged_at"])

    op.create_table(
        "thought_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("situation", sa.Text(), nullable=True),
        sa.Column("automatic_thought", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(100), nullable=True),
        sa.Column("emotion_intensity", sa.SmallInteger(), nullable=True),
        sa.Column("evidence_for", sa.Text(), nullable=True),
        sa.Column("evidence_against", sa.Text(), nullable=True),
        sa.Column("balanced_thought", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_thought_records_user_logged", "thought_records", ["user_id", "logged_at"])

    op.create_table(
        "stoic_rituals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ritual_type", sa.String(20), nullable=False),
        sa.Column("control_items", postgresql.JSONB(), nullable=True),
        sa.Column("premeditatio", sa.Text(), nullable=True),
        sa.Column("virtue_intention", sa.Text(), nullable=True),
        sa.Column("evening_good", sa.Text(), nullable=True),
        sa.Column("evening_hard", sa.Text(), nullable=True),
        sa.Column("dichotomy_audit", sa.Text(), nullable=True),
        sa.Column("tomorrow_intention", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stoic_rituals_user_type", "stoic_rituals", ["user_id", "ritual_type", "logged_at"])

    op.create_table(
        "emotion_checkins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("emotion", sa.String(100), nullable=False),
        sa.Column("intensity", sa.SmallInteger(), nullable=True),
        sa.Column("body_sensation", sa.Text(), nullable=True),
        sa.Column("ai_reflection", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_emotion_checkins_user_logged", "emotion_checkins", ["user_id", "logged_at"])


def downgrade() -> None:
    op.drop_index("ix_emotion_checkins_user_logged", "emotion_checkins")
    op.drop_table("emotion_checkins")
    op.drop_index("ix_stoic_rituals_user_type", "stoic_rituals")
    op.drop_table("stoic_rituals")
    op.drop_index("ix_thought_records_user_logged", "thought_records")
    op.drop_table("thought_records")
    op.drop_index("ix_shadow_notes_user_logged", "shadow_notes")
    op.drop_table("shadow_notes")
    op.drop_index("ix_dream_entries_user_logged", "dream_entries")
    op.drop_table("dream_entries")
    op.drop_column("users", "preferences")
