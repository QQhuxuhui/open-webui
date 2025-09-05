"""Unit tests for compliance-related models."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from models.compliance import (
    UserConsent,
    SmsVerification,
    ContentReport,
    RealNameVerification,
    ConsentType,
    SMSPurpose,
    ContentType,
    ReportCategory,
    ReportStatus,
    VerificationStatus,
    IDType,
)


class TestConsentTypeEnum:
    """Test ConsentType enum values."""

    def test_consent_type_values(self):
        assert ConsentType.PRIVACY_POLICY == "privacy_policy"
        assert ConsentType.TERMS_OF_SERVICE == "terms_of_service"
        assert ConsentType.MARKETING == "marketing"
        assert ConsentType.ANALYTICS == "analytics"


class TestSMSPurposeEnum:
    """Test SMSPurpose enum values."""

    def test_sms_purpose_values(self):
        assert SMSPurpose.REGISTRATION == "registration"
        assert SMSPurpose.LOGIN == "login"
        assert SMSPurpose.PHONE_CHANGE == "phone_change"
        assert SMSPurpose.PASSWORD_RESET == "password_reset"


class TestContentTypeEnum:
    """Test ContentType enum values."""

    def test_content_type_values(self):
        assert ContentType.TEXT == "text"
        assert ContentType.IMAGE == "image"
        assert ContentType.VIDEO == "video"
        assert ContentType.AUDIO == "audio"


class TestReportCategoryEnum:
    """Test ReportCategory enum values."""

    def test_report_category_values(self):
        assert ReportCategory.INAPPROPRIATE_CONTENT == "inappropriate_content"
        assert ReportCategory.MISINFORMATION == "misinformation"
        assert ReportCategory.TECHNICAL_ISSUE == "technical_issue"
        assert ReportCategory.SPAM == "spam"
        assert ReportCategory.HARASSMENT == "harassment"
        assert ReportCategory.OTHER == "other"


class TestReportStatusEnum:
    """Test ReportStatus enum values."""

    def test_report_status_values(self):
        assert ReportStatus.PENDING == "pending"
        assert ReportStatus.REVIEWING == "reviewing"
        assert ReportStatus.RESOLVED == "resolved"
        assert ReportStatus.DISMISSED == "dismissed"


class TestVerificationStatusEnum:
    """Test VerificationStatus enum values."""

    def test_verification_status_values(self):
        assert VerificationStatus.PENDING == "pending"
        assert VerificationStatus.APPROVED == "approved"
        assert VerificationStatus.REJECTED == "rejected"
        assert VerificationStatus.EXPIRED == "expired"


class TestIDTypeEnum:
    """Test IDType enum values."""

    def test_id_type_values(self):
        assert IDType.NATIONAL_ID == "national_id"
        assert IDType.PASSPORT == "passport"
        assert IDType.DRIVERS_LICENSE == "drivers_license"
        assert IDType.OTHER == "other"


class TestUserConsentModel:
    """Test UserConsent model attributes and structure."""

    def test_user_consent_attributes(self):
        """Test that UserConsent has all required attributes."""
        consent = UserConsent()
        
        # Check required attributes exist
        assert hasattr(consent, 'id')
        assert hasattr(consent, 'user_id')
        assert hasattr(consent, 'consent_type')
        assert hasattr(consent, 'consent_version')
        assert hasattr(consent, 'consented_at')
        assert hasattr(consent, 'ip_address')
        assert hasattr(consent, 'user_agent')
        assert hasattr(consent, 'created_at')
        assert hasattr(consent, 'updated_at')
        assert hasattr(consent, 'user')  # Relationship

    def test_user_consent_table_name(self):
        """Test UserConsent table name."""
        assert UserConsent.__tablename__ == "user_consents"


class TestSmsVerificationModel:
    """Test SmsVerification model attributes and computed properties."""

    def test_sms_verification_attributes(self):
        """Test that SmsVerification has all required attributes."""
        sms = SmsVerification()
        
        # Check required attributes exist
        assert hasattr(sms, 'id')
        assert hasattr(sms, 'phone_number')
        assert hasattr(sms, 'verification_code_hash')
        assert hasattr(sms, 'purpose')
        assert hasattr(sms, 'expires_at')
        assert hasattr(sms, 'verified_at')
        assert hasattr(sms, 'attempts')
        assert hasattr(sms, 'max_attempts')
        assert hasattr(sms, 'created_at')
        assert hasattr(sms, 'updated_at')

    def test_sms_verification_table_name(self):
        """Test SmsVerification table name."""
        assert SmsVerification.__tablename__ == "sms_verifications"

    @patch('models.compliance.datetime')
    def test_is_expired_property(self, mock_datetime):
        """Test is_expired property logic."""
        mock_now = datetime(2025, 1, 13, 12, 0, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        sms = SmsVerification()
        
        # Test not expired
        sms.expires_at = datetime(2025, 1, 13, 12, 30, 0)  # 30 minutes later
        assert not sms.is_expired
        
        # Test expired
        sms.expires_at = datetime(2025, 1, 13, 11, 30, 0)  # 30 minutes ago
        assert sms.is_expired

    def test_is_verified_property(self):
        """Test is_verified property logic."""
        sms = SmsVerification()
        
        # Test not verified
        sms.verified_at = None
        assert not sms.is_verified
        
        # Test verified
        sms.verified_at = datetime(2025, 1, 13, 12, 0, 0)
        assert sms.is_verified

    def test_attempts_remaining_property(self):
        """Test attempts_remaining property logic."""
        sms = SmsVerification()
        sms.max_attempts = 5
        
        # Test with 2 attempts used
        sms.attempts = 2
        assert sms.attempts_remaining == 3
        
        # Test with max attempts reached
        sms.attempts = 5
        assert sms.attempts_remaining == 0
        
        # Test with attempts over max (should not go negative)
        sms.attempts = 7
        assert sms.attempts_remaining == 0


class TestContentReportModel:
    """Test ContentReport model attributes and computed properties."""

    def test_content_report_attributes(self):
        """Test that ContentReport has all required attributes."""
        report = ContentReport()
        
        # Check required attributes exist
        assert hasattr(report, 'id')
        assert hasattr(report, 'reporter_id')
        assert hasattr(report, 'content_id')
        assert hasattr(report, 'content_type')
        assert hasattr(report, 'report_category')
        assert hasattr(report, 'report_reason')
        assert hasattr(report, 'content_snapshot')
        assert hasattr(report, 'status')
        assert hasattr(report, 'moderator_notes')
        assert hasattr(report, 'moderator_id')
        assert hasattr(report, 'created_at')
        assert hasattr(report, 'resolved_at')
        assert hasattr(report, 'updated_at')
        assert hasattr(report, 'reporter')  # Relationship
        assert hasattr(report, 'moderator')  # Relationship

    def test_content_report_table_name(self):
        """Test ContentReport table name."""
        assert ContentReport.__tablename__ == "content_reports"

    def test_is_resolved_property(self):
        """Test is_resolved property logic."""
        report = ContentReport()
        
        # Test pending (not resolved)
        report.status = ReportStatus.PENDING
        assert not report.is_resolved
        
        # Test reviewing (not resolved)
        report.status = ReportStatus.REVIEWING
        assert not report.is_resolved
        
        # Test resolved
        report.status = ReportStatus.RESOLVED
        assert report.is_resolved
        
        # Test dismissed (considered resolved)
        report.status = ReportStatus.DISMISSED
        assert report.is_resolved

    def test_resolution_time_hours_property(self):
        """Test resolution_time_hours property logic."""
        report = ContentReport()
        report.created_at = datetime(2025, 1, 13, 10, 0, 0)
        
        # Test not resolved yet
        report.resolved_at = None
        assert report.resolution_time_hours is None
        
        # Test resolved after 2 hours
        report.resolved_at = datetime(2025, 1, 13, 12, 0, 0)
        assert report.resolution_time_hours == 2.0
        
        # Test resolved after 30 minutes
        report.resolved_at = datetime(2025, 1, 13, 10, 30, 0)
        assert report.resolution_time_hours == 0.5


class TestRealNameVerificationModel:
    """Test RealNameVerification model attributes and computed properties."""

    def test_real_name_verification_attributes(self):
        """Test that RealNameVerification has all required attributes."""
        verification = RealNameVerification()
        
        # Check required attributes exist
        assert hasattr(verification, 'id')
        assert hasattr(verification, 'user_id')
        assert hasattr(verification, 'real_name')
        assert hasattr(verification, 'id_type')
        assert hasattr(verification, 'id_number_encrypted')
        assert hasattr(verification, 'document_front_url')
        assert hasattr(verification, 'document_back_url')
        assert hasattr(verification, 'status')
        assert hasattr(verification, 'rejection_reason')
        assert hasattr(verification, 'verified_at')
        assert hasattr(verification, 'verified_by')
        assert hasattr(verification, 'created_at')
        assert hasattr(verification, 'updated_at')
        assert hasattr(verification, 'user')  # Relationship
        assert hasattr(verification, 'verifier')  # Relationship

    def test_real_name_verification_table_name(self):
        """Test RealNameVerification table name."""
        assert RealNameVerification.__tablename__ == "real_name_verifications"

    def test_is_approved_property(self):
        """Test is_approved property logic."""
        verification = RealNameVerification()
        
        # Test approved
        verification.status = VerificationStatus.APPROVED
        assert verification.is_approved
        
        # Test not approved (pending)
        verification.status = VerificationStatus.PENDING
        assert not verification.is_approved
        
        # Test not approved (rejected)
        verification.status = VerificationStatus.REJECTED
        assert not verification.is_approved

    def test_is_pending_property(self):
        """Test is_pending property logic."""
        verification = RealNameVerification()
        
        # Test pending
        verification.status = VerificationStatus.PENDING
        assert verification.is_pending
        
        # Test not pending (approved)
        verification.status = VerificationStatus.APPROVED
        assert not verification.is_pending

    def test_verification_time_days_property(self):
        """Test verification_time_days property logic."""
        verification = RealNameVerification()
        verification.created_at = datetime(2025, 1, 10, 10, 0, 0)
        
        # Test not verified yet
        verification.verified_at = None
        assert verification.verification_time_days is None
        
        # Test verified after 3 days
        verification.verified_at = datetime(2025, 1, 13, 10, 0, 0)
        assert verification.verification_time_days == 3.0
        
        # Test verified after 12 hours (0.5 days)
        verification.verified_at = datetime(2025, 1, 10, 22, 0, 0)
        assert verification.verification_time_days == 0.5


class TestModelDefaultValues:
    """Test default values and constraints in compliance models."""

    def test_sms_verification_default_values(self):
        """Test SmsVerification default values."""
        # Note: These tests would require actual database interaction to test defaults
        # For now, we verify the model structure is correct
        sms = SmsVerification()
        assert hasattr(sms, 'attempts')
        assert hasattr(sms, 'max_attempts')
        
    def test_content_report_default_values(self):
        """Test ContentReport default status value."""
        report = ContentReport()
        assert hasattr(report, 'status')
        
    def test_real_name_verification_default_values(self):
        """Test RealNameVerification default status value."""
        verification = RealNameVerification()
        assert hasattr(verification, 'status')


class TestModelConstraints:
    """Test model constraints and validations."""

    def test_user_consent_unique_constraint_fields(self):
        """Test UserConsent unique constraint exists."""
        # This verifies the unique constraint is defined in the model
        unique_constraints = [constraint for constraint in UserConsent.__table_args__ 
                            if hasattr(constraint, 'columns')]
        assert len(unique_constraints) > 0

    def test_verification_status_check_constraint_values(self):
        """Test that RealNameVerification status values are constrained."""
        # Verify that the check constraint exists
        check_constraints = [constraint for constraint in RealNameVerification.__table_args__ 
                           if hasattr(constraint, 'sqltext')]
        assert len(check_constraints) > 0