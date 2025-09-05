"""Add profile modification history table

Revision ID: 002
Revises: 001
Create Date: 2025-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Text, Boolean, DateTime, Index


# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add profile_modification_history table."""
    op.create_table(
        'profile_modification_history',
        sa.Column('id', sa.String(36), nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('field_name', sa.String(50), nullable=False),
        sa.Column('field_label', sa.String(100), nullable=True),
        sa.Column('old_value', sa.Text, nullable=True),
        sa.Column('new_value', sa.Text, nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text, nullable=False),
        sa.Column('verification_required', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id', name='profile_modification_history_pkey'),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('profile_history_user_id_idx', 'profile_modification_history', ['user_id'])
    op.create_index('profile_history_field_name_idx', 'profile_modification_history', ['field_name'])
    op.create_index('profile_history_created_at_idx', 'profile_modification_history', ['created_at'])


def downgrade():
    """Drop profile_modification_history table."""
    op.drop_table('profile_modification_history')