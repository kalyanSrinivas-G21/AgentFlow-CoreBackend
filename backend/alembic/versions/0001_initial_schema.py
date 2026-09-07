# backend/alembic/versions/0001_initial_schema.py
"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-02 20:37:18.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Projects
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Audit Logs
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.String(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Event Records
    op.create_table('event_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('causation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_event_records_event_type', 'event_records', ['event_type'], unique=False)
    op.create_index('ix_event_records_occurred_at', 'event_records', ['occurred_at'], unique=False)
    op.create_index('ix_event_records_task_id', 'event_records', ['task_id'], unique=False)

    # Model Registry
    op.create_table('model_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier', sa.String(), nullable=False),
        sa.Column('model_tag', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Resource Metrics
    op.create_table('resource_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sampled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('cpu_percent', sa.Float(), nullable=False),
        sa.Column('ram_percent', sa.Float(), nullable=False),
        sa.Column('gpu_percent', sa.Float(), nullable=True),
        sa.Column('vram_used_mb', sa.Float(), nullable=True),
        sa.Column('active_task_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Tasks
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('input_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_of_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['retry_of_task_id'], ['tasks.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Files
    op.create_table('files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Agent Runs
    op.create_table('agent_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tier_used', sa.String(), nullable=False),
        sa.Column('iteration_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Document Chunks
    op.create_table('document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=768), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Artifacts
    op.create_table('artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('content_ref', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Plan Steps
    op.create_table('plan_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('args', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Tool Executions
    op.create_table('tool_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_step_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['plan_step_id'], ['plan_steps.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('tool_executions')
    op.drop_table('plan_steps')
    op.drop_table('artifacts')
    op.drop_table('document_chunks')
    op.drop_table('agent_runs')
    op.drop_table('files')
    op.drop_table('tasks')
    op.drop_table('resource_metrics')
    op.drop_table('model_registry')
    op.drop_index('ix_event_records_task_id', table_name='event_records')
    op.drop_index('ix_event_records_occurred_at', table_name='event_records')
    op.drop_index('ix_event_records_event_type', table_name='event_records')
    op.drop_table('event_records')
    op.drop_table('audit_logs')
    op.drop_table('projects')