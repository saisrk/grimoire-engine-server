"""Add repository config and webhook execution logs

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2025-12-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create repository_configs and webhook_execution_logs tables.
    
    This migration creates two new tables:
    1. repository_configs: Stores GitHub repository webhook configurations
    2. webhook_execution_logs: Stores detailed logs of webhook processing runs
    
    The tables are linked via foreign key with cascade delete.
    """
    # Create repository_configs table
    op.create_table(
        'repository_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo_name', sa.String(length=255), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repository_configs_id'), 'repository_configs', ['id'], unique=False)
    op.create_index(op.f('ix_repository_configs_repo_name'), 'repository_configs', ['repo_name'], unique=True)
    
    # Create webhook_execution_logs table
    op.create_table(
        'webhook_execution_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('repo_config_id', sa.Integer(), nullable=True),
        sa.Column('repo_name', sa.String(length=255), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('matched_spell_ids', sa.Text(), nullable=True),
        sa.Column('auto_generated_spell_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('pr_processing_result', sa.Text(), nullable=True),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['repo_config_id'], ['repository_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_execution_logs_id'), 'webhook_execution_logs', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_execution_logs_repo_config_id'), 'webhook_execution_logs', ['repo_config_id'], unique=False)
    op.create_index(op.f('ix_webhook_execution_logs_repo_name'), 'webhook_execution_logs', ['repo_name'], unique=False)
    op.create_index(op.f('ix_webhook_execution_logs_status'), 'webhook_execution_logs', ['status'], unique=False)
    op.create_index(op.f('ix_webhook_execution_logs_executed_at'), 'webhook_execution_logs', ['executed_at'], unique=False)


def downgrade() -> None:
    """
    Drop repository_configs and webhook_execution_logs tables.
    
    This migration reverses the upgrade by removing both tables
    and all their indexes. The foreign key constraint ensures
    webhook_execution_logs is dropped first.
    """
    # Drop webhook_execution_logs table first (has foreign key)
    op.drop_index(op.f('ix_webhook_execution_logs_executed_at'), table_name='webhook_execution_logs')
    op.drop_index(op.f('ix_webhook_execution_logs_status'), table_name='webhook_execution_logs')
    op.drop_index(op.f('ix_webhook_execution_logs_repo_name'), table_name='webhook_execution_logs')
    op.drop_index(op.f('ix_webhook_execution_logs_repo_config_id'), table_name='webhook_execution_logs')
    op.drop_index(op.f('ix_webhook_execution_logs_id'), table_name='webhook_execution_logs')
    op.drop_table('webhook_execution_logs')
    
    # Drop repository_configs table
    op.drop_index(op.f('ix_repository_configs_repo_name'), table_name='repository_configs')
    op.drop_index(op.f('ix_repository_configs_id'), table_name='repository_configs')
    op.drop_table('repository_configs')
