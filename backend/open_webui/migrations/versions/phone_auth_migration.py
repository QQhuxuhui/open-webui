"""Add phone field to users table for Chinese compliance

Revision ID: phone_auth_001
Revises: 
Create Date: 2025-09-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'phone_auth_001'
down_revision = None  # 将在实际环境中设置为最新的revision
branch_labels = None
depends_on = None


def upgrade():
    # 添加phone字段到user表
    op.add_column('user', sa.Column('phone', sa.String(20), nullable=True, unique=True))
    
    # 添加phone索引
    op.create_index('idx_user_phone', 'user', ['phone'], unique=True)


def downgrade():
    # 删除phone索引
    op.drop_index('idx_user_phone', table_name='user')
    
    # 删除phone字段
    op.drop_column('user', 'phone')