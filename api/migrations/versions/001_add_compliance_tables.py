"""add compliance tables and extend accounts model

Revision ID: 001_compliance
Revises: 6dcb43972bdc
Create Date: 2025-01-13 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_compliance'
down_revision = '6dcb43972bdc'
branch_labels = None
depends_on = None


def upgrade():
    """Add compliance tables and extend accounts model with new fields."""
    
    # Extend accounts table with new compliance fields
    op.add_column('accounts', sa.Column('phone_number', sa.String(20), nullable=True))
    op.add_column('accounts', sa.Column('phone_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('accounts', sa.Column('real_name', sa.String(255), nullable=True))
    op.add_column('accounts', sa.Column('real_name_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('accounts', sa.Column('real_name_verified_at', sa.DateTime(), nullable=True))
    op.add_column('accounts', sa.Column('nickname', sa.String(255), nullable=True))
    op.add_column('accounts', sa.Column('avatar_url', sa.String(500), nullable=True))
    
    # Create indexes for phone number lookup (unique constraint for non-null values)
    op.create_index('account_phone_number_idx', 'accounts', ['phone_number'], unique=True, 
                    postgresql_where=sa.text('phone_number IS NOT NULL'))
    
    # Create user_consents table
    op.create_table('user_consents',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('consent_type', sa.String(50), nullable=False),
        sa.Column('consent_version', sa.String(20), nullable=False),
        sa.Column('consented_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # Ensure unique consent per user per type per version
        sa.UniqueConstraint('user_id', 'consent_type', 'consent_version', name='unique_user_consent_version')
    )
    
    # Create indexes for user_consents
    op.create_index('user_consents_user_id_idx', 'user_consents', ['user_id'])
    op.create_index('user_consents_type_idx', 'user_consents', ['consent_type'])
    op.create_index('user_consents_created_at_idx', 'user_consents', ['created_at'])
    
    # Create sms_verifications table
    op.create_table('sms_verifications',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('verification_code_hash', sa.String(255), nullable=False),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default=sa.text('5'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for sms_verifications (anti-brute-force)
    op.create_index('sms_verifications_phone_purpose_idx', 'sms_verifications', ['phone_number', 'purpose'])
    op.create_index('sms_verifications_expires_at_idx', 'sms_verifications', ['expires_at'])
    op.create_index('sms_verifications_created_at_idx', 'sms_verifications', ['created_at'])
    
    # Create content_reports table
    op.create_table('content_reports',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('reporter_id', postgresql.UUID(), nullable=False),
        sa.Column('content_id', sa.String(255), nullable=False),
        sa.Column('content_type', sa.String(20), nullable=False),
        sa.Column('report_category', sa.String(50), nullable=False),
        sa.Column('report_reason', sa.Text(), nullable=True),
        sa.Column('content_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('moderator_notes', sa.Text(), nullable=True),
        sa.Column('moderator_id', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reporter_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['moderator_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for content_reports (performance optimization)
    op.create_index('content_reports_reporter_idx', 'content_reports', ['reporter_id'])
    op.create_index('content_reports_content_idx', 'content_reports', ['content_id', 'content_type'])
    op.create_index('content_reports_status_idx', 'content_reports', ['status'])
    op.create_index('content_reports_created_at_idx', 'content_reports', ['created_at'])
    op.create_index('content_reports_category_idx', 'content_reports', ['report_category'])
    
    # Create real_name_verifications table  
    op.create_table('real_name_verifications',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('real_name', sa.String(255), nullable=False),
        sa.Column('id_type', sa.String(20), nullable=False),
        sa.Column('id_number_encrypted', sa.Text(), nullable=False),
        sa.Column('document_front_url', sa.String(500), nullable=True),
        sa.Column('document_back_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verified_by', postgresql.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        # Add check constraint for valid statuses
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'expired')", name='valid_verification_status')
    )
    
    # Create indexes for real_name_verifications (status constraints)
    op.create_index('real_name_verifications_user_idx', 'real_name_verifications', ['user_id'])
    op.create_index('real_name_verifications_status_idx', 'real_name_verifications', ['status'])
    op.create_index('real_name_verifications_created_at_idx', 'real_name_verifications', ['created_at'])
    
    # Extend messages table to support AI content identification
    op.add_column('messages', sa.Column('ai_generated', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('messages', sa.Column('ai_model_info', postgresql.JSONB(), nullable=True))
    op.add_column('messages', sa.Column('content_labels', postgresql.JSONB(), nullable=True))
    
    # Create index for AI content queries
    op.create_index('messages_ai_generated_idx', 'messages', ['ai_generated'])


def downgrade():
    """Remove compliance tables and revert accounts model changes."""
    
    # Remove indexes first
    op.drop_index('messages_ai_generated_idx', table_name='messages')
    op.drop_index('real_name_verifications_created_at_idx', table_name='real_name_verifications')
    op.drop_index('real_name_verifications_status_idx', table_name='real_name_verifications')
    op.drop_index('real_name_verifications_user_idx', table_name='real_name_verifications')
    op.drop_index('content_reports_category_idx', table_name='content_reports')
    op.drop_index('content_reports_created_at_idx', table_name='content_reports')
    op.drop_index('content_reports_status_idx', table_name='content_reports')
    op.drop_index('content_reports_content_idx', table_name='content_reports')
    op.drop_index('content_reports_reporter_idx', table_name='content_reports')
    op.drop_index('sms_verifications_created_at_idx', table_name='sms_verifications')
    op.drop_index('sms_verifications_expires_at_idx', table_name='sms_verifications')
    op.drop_index('sms_verifications_phone_purpose_idx', table_name='sms_verifications')
    op.drop_index('user_consents_created_at_idx', table_name='user_consents')
    op.drop_index('user_consents_type_idx', table_name='user_consents')
    op.drop_index('user_consents_user_id_idx', table_name='user_consents')
    op.drop_index('account_phone_number_idx', table_name='accounts')
    
    # Drop tables
    op.drop_table('real_name_verifications')
    op.drop_table('content_reports')
    op.drop_table('sms_verifications') 
    op.drop_table('user_consents')
    
    # Remove columns from messages table
    op.drop_column('messages', 'content_labels')
    op.drop_column('messages', 'ai_model_info')
    op.drop_column('messages', 'ai_generated')
    
    # Remove columns from accounts table
    op.drop_column('accounts', 'avatar_url')
    op.drop_column('accounts', 'nickname')
    op.drop_column('accounts', 'real_name_verified_at')
    op.drop_column('accounts', 'real_name_verified')
    op.drop_column('accounts', 'real_name')
    op.drop_column('accounts', 'phone_verified')
    op.drop_column('accounts', 'phone_number')