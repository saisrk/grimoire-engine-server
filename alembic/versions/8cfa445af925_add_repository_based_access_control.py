"""add_repository_based_access_control

Revision ID: 8cfa445af925
Revises: c2d3e4f5g6h7
Create Date: 2025-12-11 17:19:02.791019

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8cfa445af925'
down_revision = 'c2d3e4f5g6h7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add repository-based access control foreign key relationships.
    
    This migration adds:
    1. user_id foreign key to repository_configs table (with CASCADE delete)
    2. repository_id foreign key to spells table (with RESTRICT delete to prevent data loss)
    3. Appropriate indexes for the new foreign key columns
    
    Note: Columns are initially nullable to handle existing data. A separate data migration
    will populate these fields and then make them NOT NULL.
    
    Requirements: 3.2, 1.4, 10.1
    """
    # Add user_id foreign key to repository_configs table using batch mode for SQLite
    with op.batch_alter_table('repository_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_repository_configs_user_id', 
            'users', 
            ['user_id'], 
            ['id'], 
            ondelete='CASCADE'  # When user is deleted, delete their repositories
        )
        batch_op.create_index('ix_repository_configs_user_id', ['user_id'], unique=False)
    
    # Add repository_id foreign key to spells table using batch mode for SQLite
    with op.batch_alter_table('spells', schema=None) as batch_op:
        batch_op.add_column(sa.Column('repository_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_spells_repository_id', 
            'repository_configs', 
            ['repository_id'], 
            ['id'], 
            ondelete='RESTRICT'  # Prevent repository deletion if spells exist
        )
        batch_op.create_index('ix_spells_repository_id', ['repository_id'], unique=False)


def downgrade() -> None:
    """
    Remove repository-based access control foreign key relationships.
    
    This migration reverses the upgrade by removing the foreign key
    constraints and columns added for repository-based access control.
    """
    # Remove repository_id foreign key from spells table using batch mode for SQLite
    with op.batch_alter_table('spells', schema=None) as batch_op:
        batch_op.drop_index('ix_spells_repository_id')
        batch_op.drop_constraint('fk_spells_repository_id', type_='foreignkey')
        batch_op.drop_column('repository_id')
    
    # Remove user_id foreign key from repository_configs table using batch mode for SQLite
    with op.batch_alter_table('repository_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_repository_configs_user_id')
        batch_op.drop_constraint('fk_repository_configs_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
