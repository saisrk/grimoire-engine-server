"""Add spell applications table

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2025-12-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2d3e4f5g6h7'
down_revision = 'b1c2d3e4f5g6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create the spell_applications table.
    
    This migration creates the spell_applications table to track each time
    a spell is applied to generate a context-aware patch. The table stores
    the failing context, generated patch, and metadata.
    """
    op.create_table(
        'spell_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spell_id', sa.Integer(), nullable=False),
        sa.Column('repository', sa.String(length=500), nullable=False),
        sa.Column('commit_sha', sa.String(length=40), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('failing_test', sa.String(length=500), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('patch', sa.Text(), nullable=False),
        sa.Column('files_touched', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['spell_id'], ['spells.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spell_applications_id'), 'spell_applications', ['id'], unique=False)
    op.create_index(op.f('ix_spell_applications_spell_id'), 'spell_applications', ['spell_id'], unique=False)


def downgrade() -> None:
    """
    Drop the spell_applications table.
    
    This migration reverses the upgrade by removing the spell_applications
    table and all its indexes from the database.
    """
    op.drop_index(op.f('ix_spell_applications_spell_id'), table_name='spell_applications')
    op.drop_index(op.f('ix_spell_applications_id'), table_name='spell_applications')
    op.drop_table('spell_applications')
