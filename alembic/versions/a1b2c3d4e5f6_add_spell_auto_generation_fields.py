"""Add spell auto-generation fields

Revision ID: a1b2c3d4e5f6
Revises: 52609355075f
Create Date: 2024-12-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '52609355075f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add auto-generation tracking fields to spells table.
    
    This migration adds three new columns to support automatic spell generation:
    - auto_generated: Flag indicating if spell was auto-generated (0=manual, 1=auto)
    - confidence_score: Confidence score for auto-generated spells (0-100)
    - human_reviewed: Flag indicating if spell has been reviewed (0=not reviewed, 1=reviewed)
    """
    # Add new columns with default values
    op.add_column('spells', sa.Column('auto_generated', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('spells', sa.Column('confidence_score', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('spells', sa.Column('human_reviewed', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """
    Remove auto-generation tracking fields from spells table.
    
    This migration reverses the upgrade by removing the three columns
    added for auto-generation tracking.
    """
    op.drop_column('spells', 'human_reviewed')
    op.drop_column('spells', 'confidence_score')
    op.drop_column('spells', 'auto_generated')
