"""Compliance-related models for user verification, content reporting, and consent tracking."""

import enum
import sqlalchemy as sa
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import DateTime, String, Text, Boolean, Integer, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base
from .types import StringUUID


class ConsentType(enum.StrEnum):
    """Types of consent that users can provide."""
    PRIVACY_POLICY = "privacy_policy"
    TERMS_OF_SERVICE = "terms_of_service"
    MARKETING = "marketing"
    ANALYTICS = "analytics"


class SMSPurpose(enum.StrEnum):
    """Purposes for SMS verification."""
    REGISTRATION = "registration"
    LOGIN = "login"
    PHONE_CHANGE = "phone_change"
    PASSWORD_RESET = "password_reset"


class ContentType(enum.StrEnum):
    """Types of content that can be reported."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class ReportCategory(enum.StrEnum):
    """Categories for content reports."""
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    MISINFORMATION = "misinformation"
    TECHNICAL_ISSUE = "technical_issue"
    SPAM = "spam"
    HARASSMENT = "harassment"
    OTHER = "other"


class ReportStatus(enum.StrEnum):
    """Status of content reports."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class VerificationStatus(enum.StrEnum):
    """Status of real name verifications."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class IDType(enum.StrEnum):
    """Types of identification documents."""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    OTHER = "other"


class UserConsent(Base):
    """User consent records for privacy policy, terms of service, etc."""
    __tablename__ = "user_consents"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="user_consent_pkey"),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'consent_type', 'consent_version', name='unique_user_consent_version'),
        Index("user_consents_user_id_idx", "user_id"),
        Index("user_consents_type_idx", "consent_type"),
        Index("user_consents_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)

    # Relationships
    user = relationship("Account", back_populates="consents")


class SmsVerification(Base):
    """SMS verification codes for phone number validation."""
    __tablename__ = "sms_verifications"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="sms_verification_pkey"),
        Index("sms_verifications_phone_purpose_idx", "phone_number", "purpose"),
        Index("sms_verifications_expires_at_idx", "expires_at"),
        Index("sms_verifications_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, server_default=sa.text('0'), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=sa.text('5'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)

    @property
    def is_expired(self) -> bool:
        """Check if the verification code has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_verified(self) -> bool:
        """Check if the verification has been completed."""
        return self.verified_at is not None

    @property
    def attempts_remaining(self) -> int:
        """Get number of attempts remaining."""
        return max(0, self.max_attempts - self.attempts)


class ContentReport(Base):
    """Content reports for inappropriate, harmful, or incorrect AI-generated content."""
    __tablename__ = "content_reports"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="content_report_pkey"),
        sa.ForeignKeyConstraint(['reporter_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['moderator_id'], ['accounts.id'], ondelete='SET NULL'),
        Index("content_reports_reporter_idx", "reporter_id"),
        Index("content_reports_content_idx", "content_id", "content_type"),
        Index("content_reports_status_idx", "status"),
        Index("content_reports_created_at_idx", "created_at"),
        Index("content_reports_category_idx", "report_category"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    reporter_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    content_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    report_category: Mapped[str] = mapped_column(String(50), nullable=False)
    report_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'pending'"), nullable=False)
    moderator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderator_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)

    # Relationships
    reporter = relationship("Account", foreign_keys=[reporter_id], back_populates="content_reports")
    moderator = relationship("Account", foreign_keys=[moderator_id])

    @property
    def is_resolved(self) -> bool:
        """Check if the report has been resolved."""
        return self.status in [ReportStatus.RESOLVED, ReportStatus.DISMISSED]

    @property
    def resolution_time_hours(self) -> Optional[float]:
        """Calculate resolution time in hours."""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return delta.total_seconds() / 3600
        return None


class RealNameVerification(Base):
    """Real name verification records for identity verification."""
    __tablename__ = "real_name_verifications"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="real_name_verification_pkey"),
        sa.ForeignKeyConstraint(['user_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['accounts.id'], ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'expired')", 
                          name='valid_verification_status'),
        Index("real_name_verifications_user_idx", "user_id"),
        Index("real_name_verifications_status_idx", "status"),
        Index("real_name_verifications_created_at_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, server_default=sa.text("uuid_generate_v4()"))
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    real_name: Mapped[str] = mapped_column(String(255), nullable=False)
    id_type: Mapped[str] = mapped_column(String(20), nullable=False)
    id_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    document_front_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    document_back_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default=sa.text("'pending'"), nullable=False)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=sa.text('now()'), nullable=False)

    # Relationships
    user = relationship("Account", foreign_keys=[user_id], back_populates="real_name_verifications")
    verifier = relationship("Account", foreign_keys=[verified_by])

    @property
    def is_approved(self) -> bool:
        """Check if the verification is approved."""
        return self.status == VerificationStatus.APPROVED

    @property
    def is_pending(self) -> bool:
        """Check if the verification is pending."""
        return self.status == VerificationStatus.PENDING

    @property
    def verification_time_days(self) -> Optional[float]:
        """Calculate verification processing time in days."""
        if self.verified_at:
            delta = self.verified_at - self.created_at
            return delta.total_seconds() / 86400
        return None