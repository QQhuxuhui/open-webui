"""Add phone_verification table for SMS code verification

Revision ID: phone_verification_001
Revises: phone_auth_001
Create Date: 2025-09-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'phone_verification_001'
down_revision = 'phone_auth_001'  
branch_labels = None
depends_on = None


def upgrade():
    # 创建phone_verification表
    op.create_table('phone_verification',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.BigInteger(), nullable=True),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('attempts', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_phone_verification_phone'), 'phone_verification', ['phone'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_phone_verification_phone'), table_name='phone_verification')
    op.drop_table('phone_verification')