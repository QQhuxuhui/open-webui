"""Profile modification history model for security audit and tracking."""

import sqlalchemy as sa
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from .types import StringUUID


class ProfileModificationHistory(Base):
    """Profile modification history for security audit and tracking."""
    __tablename__ = "profile_modification_history"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="profile_modification_history_pkey"),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        Index("profile_history_user_id_idx", "user_id"),
        Index("profile_history_field_name_idx", "field_name"),
        Index("profile_history_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)  # nickname, phone_number, avatar_url, etc.
    field_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Human-readable field name
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    verification_required: Mapped[bool] = mapped_column(Boolean, server_default=sa.text('false'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)

    # Relationships
    user = relationship("Account", back_populates="profile_modifications")

    @property
    def is_sensitive_field(self) -> bool:
        """Check if the field is considered sensitive and requires additional security."""
        sensitive_fields = ["phone_number", "real_name", "email"]
        return self.field_name in sensitive_fields

    @classmethod
    def create_history_record(
        cls,
        user_id: str,
        field_name: str,
        old_value: Optional[str],
        new_value: str,
        ip_address: str,
        user_agent: str,
        field_label: Optional[str] = None,
        verification_required: bool = False
    ) -> "ProfileModificationHistory":
        """Create a new profile modification history record."""
        return cls(
            user_id=user_id,
            field_name=field_name,
            field_label=field_label,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            verification_required=verification_required or cls._is_sensitive_field(field_name)
        )

    @staticmethod
    def _is_sensitive_field(field_name: str) -> bool:
        """Check if a field is considered sensitive."""
        sensitive_fields = ["phone_number", "real_name", "email"]
        return field_name in sensitive_fields