"""update user table

Revision ID: 3af16a1c9fb6
Revises: 018012973d35
Create Date: 2025-08-21 02:07:18.078283

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "3af16a1c9fb6"
down_revision: Union[str, None] = "018012973d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection
    conn = op.get_bind()

    # Helper function to check if column exists
    def column_exists(table_name, column_name):
        result = conn.execute(
            text(f"SELECT 1 FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = '{column_name}'")
        )
        return result.fetchone() is not None

    # Add columns only if they don't exist
    if not column_exists("user", "username"):
        op.add_column("user", sa.Column("username", sa.String(length=50), nullable=True))

    if not column_exists("user", "bio"):
        op.add_column("user", sa.Column("bio", sa.Text(), nullable=True))

    if not column_exists("user", "gender"):
        op.add_column("user", sa.Column("gender", sa.Text(), nullable=True))

    if not column_exists("user", "date_of_birth"):
        op.add_column("user", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    # Get database connection
    conn = op.get_bind()

    # Helper function to check if column exists
    def column_exists(table_name, column_name):
        result = conn.execute(
            text(f"SELECT 1 FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = '{column_name}'")
        )
        return result.fetchone() is not None

    # Drop columns only if they exist
    if column_exists("user", "username"):
        op.drop_column("user", "username")

    if column_exists("user", "bio"):
        op.drop_column("user", "bio")

    if column_exists("user", "gender"):
        op.drop_column("user", "gender")

    if column_exists("user", "date_of_birth"):
        op.drop_column("user", "date_of_birth")
