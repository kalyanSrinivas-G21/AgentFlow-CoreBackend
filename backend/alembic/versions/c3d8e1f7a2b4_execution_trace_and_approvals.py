"""add safe execution traces and approval checkpoints

Revision ID: c3d8e1f7a2b4
Revises: b7f5c2e4a1d0
Create Date: 2026-09-07 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d8e1f7a2b4"
down_revision: Union[str, None] = "b7f5c2e4a1d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_trace_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_type", sa.String(), nullable=False),
        sa.Column("component", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("retry_number", sa.Integer(), nullable=False),
        sa.Column("parent_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_category", sa.String(), nullable=True),
        sa.Column("safe_summary", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_trace_records_execution_id", "execution_trace_records", ["execution_id"])
    op.create_index("ix_execution_trace_records_step_id", "execution_trace_records", ["step_id"])

    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_execution_id", "approval_requests", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_requests_execution_id", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_execution_trace_records_step_id", table_name="execution_trace_records")
    op.drop_index("ix_execution_trace_records_execution_id", table_name="execution_trace_records")
    op.drop_table("execution_trace_records")
