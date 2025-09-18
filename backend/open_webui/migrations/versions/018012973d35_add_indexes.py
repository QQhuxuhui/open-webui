"""Add indexes

Revision ID: 018012973d35
Revises: d31026856c01
Create Date: 2025-08-13 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "018012973d35"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None


def upgrade():
    # Get database connection
    conn = op.get_bind()

    # Helper function to check if index exists
    def index_exists(index_name, table_name):
        result = conn.execute(
            text(f"SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}' AND tablename = '{table_name}'")
        )
        return result.fetchone() is not None

    # Chat table indexes - check before creating
    if not index_exists("folder_id_idx", "chat"):
        op.create_index("folder_id_idx", "chat", ["folder_id"])

    if not index_exists("user_id_pinned_idx", "chat"):
        op.create_index("user_id_pinned_idx", "chat", ["user_id", "pinned"])

    if not index_exists("user_id_archived_idx", "chat"):
        op.create_index("user_id_archived_idx", "chat", ["user_id", "archived"])

    if not index_exists("updated_at_user_id_idx", "chat"):
        op.create_index("updated_at_user_id_idx", "chat", ["updated_at", "user_id"])

    if not index_exists("folder_id_user_id_idx", "chat"):
        op.create_index("folder_id_user_id_idx", "chat", ["folder_id", "user_id"])

    # Tag table index
    if not index_exists("user_id_idx", "tag"):
        op.create_index("user_id_idx", "tag", ["user_id"])

    # Function table index
    if not index_exists("is_global_idx", "function"):
        op.create_index("is_global_idx", "function", ["is_global"])


def downgrade():
    # Get database connection
    conn = op.get_bind()

    # Helper function to check if index exists
    def index_exists(index_name, table_name):
        result = conn.execute(
            text(f"SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}' AND tablename = '{table_name}'")
        )
        return result.fetchone() is not None

    # Chat table indexes - check before dropping
    if index_exists("folder_id_idx", "chat"):
        op.drop_index("folder_id_idx", table_name="chat")

    if index_exists("user_id_pinned_idx", "chat"):
        op.drop_index("user_id_pinned_idx", table_name="chat")

    if index_exists("user_id_archived_idx", "chat"):
        op.drop_index("user_id_archived_idx", table_name="chat")

    if index_exists("updated_at_user_id_idx", "chat"):
        op.drop_index("updated_at_user_id_idx", table_name="chat")

    if index_exists("folder_id_user_id_idx", "chat"):
        op.drop_index("folder_id_user_id_idx", table_name="chat")

    # Tag table index
    if index_exists("user_id_idx", "tag"):
        op.drop_index("user_id_idx", table_name="tag")

    # Function table index
    if index_exists("is_global_idx", "function"):
        op.drop_index("is_global_idx", table_name="function")
