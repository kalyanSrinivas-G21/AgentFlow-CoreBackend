"""restore persistent Phase 15 model catalog

Revision ID: b7f5c2e4a1d0
Revises: 9eeb6c3f39f3
Create Date: 2026-09-07 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7f5c2e4a1d0"
down_revision: Union[str, None] = "9eeb6c3f39f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("runtime_type", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("modalities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_limit", sa.Integer(), nullable=True),
        sa.Column("estimated_vram_mb", sa.Integer(), nullable=True),
        sa.Column("measured_vram_mb", sa.Integer(), nullable=True),
        sa.Column("cpu_fallback", sa.Boolean(), nullable=False),
        sa.Column("gpu_required", sa.Boolean(), nullable=False),
        sa.Column("supported_devices", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("availability", sa.Boolean(), nullable=False),
        sa.Column("load_state", sa.String(), nullable=False),
        sa.Column("health", sa.String(), nullable=False),
        sa.Column("failure_reason", sa.String(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id"),
    )
    op.create_index("ix_model_registry_model_id", "model_registry", ["model_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_model_registry_model_id", table_name="model_registry")
    op.drop_table("model_registry")
