"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("personality_key", sa.String(50), server_default="companion"),
        sa.Column("goals", sa.dialects.postgresql.JSONB()),
        sa.Column("timezone", sa.String(64), server_default="Europe/Istanbul"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "personality_profiles",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("tone_rules", sa.dialects.postgresql.JSONB()),
    )

    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("mood", sa.SmallInteger()),
        sa.Column("sleep_quality", sa.SmallInteger()),
        sa.Column("energy", sa.SmallInteger()),
        sa.Column("smoking_craving", sa.SmallInteger()),
        sa.Column("workout_done", sa.Boolean()),
        sa.Column("workout_type", sa.Text()),
        sa.Column("stress", sa.SmallInteger()),
        sa.Column("weight", sa.Numeric(6, 2)),
        sa.Column("motivation", sa.SmallInteger()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_check_ins_user_date"),
    )
    op.create_index("ix_check_ins_user_date", "check_ins", ["user_id", "date"])

    op.create_table(
        "meals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("photo_path", sa.Text()),
        sa.Column("estimated_calories", sa.Integer()),
        sa.Column("protein_g", sa.Numeric(6, 1)),
        sa.Column("carbs_g", sa.Numeric(6, 1)),
        sa.Column("fat_g", sa.Numeric(6, 1)),
        sa.Column("ai_analysis", sa.Text()),
        sa.Column("raw_vision", sa.dialects.postgresql.JSONB()),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "smoking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("intensity", sa.SmallInteger()),
        sa.Column("trigger_note", sa.Text()),
        sa.Column("context", sa.dialects.postgresql.JSONB()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(100)),
        sa.Column("duration_min", sa.Integer()),
        sa.Column("completed", sa.Boolean(), server_default="true"),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_session", "conversations", ["user_id", "session_id"])

    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("memory_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.5"),
        sa.Column("source", sa.String(20), server_default="extracted"),
        sa.Column("metadata", sa.dialects.postgresql.JSONB()),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memories_user_type_importance", "memories", ["user_id", "memory_type", "importance"])

    op.create_table(
        "memory_embeddings",
        sa.Column("memory_id", sa.Integer(), sa.ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("embedding", Vector(1536), nullable=False),
    )
    op.execute(
        "CREATE INDEX ix_memory_embeddings_hnsw ON memory_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "behavioral_insights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("insight_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("evidence", sa.dialects.postgresql.JSONB()),
        sa.Column("confidence", sa.Float(), server_default="0.7"),
        sa.Column("surfaced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("dismissed", sa.Boolean(), server_default="false"),
    )
    op.create_index("ix_insights_user_surfaced", "behavioral_insights", ["user_id", "surfaced_at"])


def downgrade() -> None:
    op.drop_table("behavioral_insights")
    op.drop_table("memory_embeddings")
    op.drop_table("memories")
    op.drop_table("conversations")
    op.drop_table("workouts")
    op.drop_table("smoking_events")
    op.drop_table("meals")
    op.drop_table("check_ins")
    op.drop_table("personality_profiles")
    op.drop_table("users")
