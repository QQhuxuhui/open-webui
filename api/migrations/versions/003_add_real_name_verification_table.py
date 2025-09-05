"""Add real name verification table

Revision ID: 003_add_real_name_verification_table
Revises: 002_add_profile_history_table
Create Date: 2025-01-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_add_real_name_verification_table'
down_revision = '002_add_profile_history_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create real_name_verifications table
    op.create_table('real_name_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('real_name', sa.String(length=255), nullable=False),
        sa.Column('id_type', sa.String(length=20), nullable=False),
        sa.Column('id_number_encrypted', sa.Text(), nullable=False),
        sa.Column('document_front_url', sa.String(length=500), nullable=True),
        sa.Column('document_back_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'expired')", name='valid_verification_status'),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='real_name_verification_pkey')
    )
    
    # Create indexes for performance
    op.create_index('real_name_verifications_user_idx', 'real_name_verifications', ['user_id'])
    op.create_index('real_name_verifications_status_idx', 'real_name_verifications', ['status'])
    op.create_index('real_name_verifications_created_at_idx', 'real_name_verifications', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('real_name_verifications_created_at_idx', table_name='real_name_verifications')
    op.drop_index('real_name_verifications_status_idx', table_name='real_name_verifications')
    op.drop_index('real_name_verifications_user_idx', table_name='real_name_verifications')
    
    # Drop table
    op.drop_table('real_name_verifications')