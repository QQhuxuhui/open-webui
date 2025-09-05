"""Integration tests for compliance models and database operations."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

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
from models.account import Account


# Note: These are basic structural integration tests
# Full database integration tests would require test database setup


class TestComplianceModelsIntegration:
    """Test compliance models integration and data validation."""

    def test_user_consent_model_instantiation(self):
        """Test UserConsent model can be instantiated with valid data."""
        consent_data = {
            'user_id': str(uuid.uuid4()),
            'consent_type': ConsentType.PRIVACY_POLICY,
            'consent_version': '1.0',
            'consented_at': datetime.utcnow(),
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...',
        }
        
        consent = UserConsent(**consent_data)
        assert consent.user_id == consent_data['user_id']
        assert consent.consent_type == consent_data['consent_type']
        assert consent.consent_version == consent_data['consent_version']

    def test_sms_verification_model_instantiation(self):
        """Test SmsVerification model can be instantiated with valid data."""
        sms_data = {
            'phone_number': '+1234567890',
            'verification_code_hash': 'hashed_code_here',
            'purpose': SMSPurpose.REGISTRATION,
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'attempts': 0,
            'max_attempts': 5,
        }
        
        sms = SmsVerification(**sms_data)
        assert sms.phone_number == sms_data['phone_number']
        assert sms.purpose == sms_data['purpose']
        assert sms.attempts == 0
        assert sms.max_attempts == 5

    def test_content_report_model_instantiation(self):
        """Test ContentReport model can be instantiated with valid data."""
        report_data = {
            'reporter_id': str(uuid.uuid4()),
            'content_id': 'message_123',
            'content_type': ContentType.TEXT,
            'report_category': ReportCategory.INAPPROPRIATE_CONTENT,
            'report_reason': 'Contains inappropriate language',
            'content_snapshot': {'message': 'original content here'},
            'status': ReportStatus.PENDING,
        }
        
        report = ContentReport(**report_data)
        assert report.reporter_id == report_data['reporter_id']
        assert report.content_type == report_data['content_type']
        assert report.report_category == report_data['report_category']
        assert report.status == report_data['status']

    def test_real_name_verification_model_instantiation(self):
        """Test RealNameVerification model can be instantiated with valid data."""
        verification_data = {
            'user_id': str(uuid.uuid4()),
            'real_name': 'John Doe',
            'id_type': IDType.NATIONAL_ID,
            'id_number_encrypted': 'encrypted_id_number',
            'status': VerificationStatus.PENDING,
        }
        
        verification = RealNameVerification(**verification_data)
        assert verification.user_id == verification_data['user_id']
        assert verification.real_name == verification_data['real_name']
        assert verification.id_type == verification_data['id_type']
        assert verification.status == verification_data['status']

    def test_sms_verification_computed_properties(self):
        """Test SmsVerification computed properties work correctly."""
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        sms = SmsVerification(
            phone_number='+1234567890',
            verification_code_hash='hash',
            purpose=SMSPurpose.LOGIN,
            expires_at=expires_at,
            attempts=2,
            max_attempts=5
        )
        
        # Test attempts_remaining
        assert sms.attempts_remaining == 3
        
        # Test is_verified (should be False since verified_at is None)
        assert not sms.is_verified
        
        # Set verified_at
        sms.verified_at = datetime.utcnow()
        assert sms.is_verified

    def test_content_report_computed_properties(self):
        """Test ContentReport computed properties work correctly."""
        created_time = datetime.utcnow() - timedelta(hours=2)
        resolved_time = datetime.utcnow()
        
        report = ContentReport(
            reporter_id=str(uuid.uuid4()),
            content_id='msg_123',
            content_type=ContentType.TEXT,
            report_category=ReportCategory.SPAM,
            status=ReportStatus.RESOLVED,
            created_at=created_time,
            resolved_at=resolved_time
        )
        
        # Test is_resolved
        assert report.is_resolved
        
        # Test resolution_time_hours
        assert report.resolution_time_hours == 2.0
        
        # Test with unresolved report
        report.status = ReportStatus.PENDING
        assert not report.is_resolved

    def test_real_name_verification_computed_properties(self):
        """Test RealNameVerification computed properties work correctly."""
        created_time = datetime.utcnow() - timedelta(days=3)
        verified_time = datetime.utcnow()
        
        verification = RealNameVerification(
            user_id=str(uuid.uuid4()),
            real_name='Jane Smith',
            id_type=IDType.PASSPORT,
            id_number_encrypted='encrypted',
            status=VerificationStatus.APPROVED,
            created_at=created_time,
            verified_at=verified_time
        )
        
        # Test is_approved
        assert verification.is_approved
        
        # Test is_pending
        assert not verification.is_pending
        
        # Test verification_time_days
        assert verification.verification_time_days == 3.0
        
        # Test with pending verification
        verification.status = VerificationStatus.PENDING
        assert not verification.is_approved
        assert verification.is_pending

    def test_enum_values_consistency(self):
        """Test that enum values are consistent with expected string values."""
        # Test ConsentType
        assert ConsentType.PRIVACY_POLICY.value == 'privacy_policy'
        assert ConsentType.TERMS_OF_SERVICE.value == 'terms_of_service'
        
        # Test SMSPurpose
        assert SMSPurpose.REGISTRATION.value == 'registration'
        assert SMSPurpose.LOGIN.value == 'login'
        
        # Test ContentType
        assert ContentType.TEXT.value == 'text'
        assert ContentType.IMAGE.value == 'image'
        
        # Test ReportCategory
        assert ReportCategory.INAPPROPRIATE_CONTENT.value == 'inappropriate_content'
        assert ReportCategory.MISINFORMATION.value == 'misinformation'
        
        # Test ReportStatus
        assert ReportStatus.PENDING.value == 'pending'
        assert ReportStatus.RESOLVED.value == 'resolved'
        
        # Test VerificationStatus
        assert VerificationStatus.PENDING.value == 'pending'
        assert VerificationStatus.APPROVED.value == 'approved'
        
        # Test IDType
        assert IDType.NATIONAL_ID.value == 'national_id'
        assert IDType.PASSPORT.value == 'passport'

    def test_model_table_names(self):
        """Test that all compliance models have correct table names."""
        assert UserConsent.__tablename__ == 'user_consents'
        assert SmsVerification.__tablename__ == 'sms_verifications'
        assert ContentReport.__tablename__ == 'content_reports'
        assert RealNameVerification.__tablename__ == 'real_name_verifications'

    def test_model_relationships_exist(self):
        """Test that model relationships are properly defined."""
        # UserConsent should have user relationship
        assert hasattr(UserConsent, 'user')
        
        # ContentReport should have reporter and moderator relationships
        assert hasattr(ContentReport, 'reporter')
        assert hasattr(ContentReport, 'moderator')
        
        # RealNameVerification should have user and verifier relationships
        assert hasattr(RealNameVerification, 'user')
        assert hasattr(RealNameVerification, 'verifier')

    def test_account_model_extensions(self):
        """Test that Account model has new compliance fields."""
        account = Account()
        
        # Test new compliance fields exist
        assert hasattr(account, 'phone_number')
        assert hasattr(account, 'phone_verified')
        assert hasattr(account, 'real_name')
        assert hasattr(account, 'real_name_verified')
        assert hasattr(account, 'real_name_verified_at')
        assert hasattr(account, 'nickname')
        assert hasattr(account, 'avatar_url')
        
        # Test new relationships exist
        assert hasattr(account, 'consents')
        assert hasattr(account, 'content_reports')
        assert hasattr(account, 'real_name_verifications')

    def test_data_validation_edge_cases(self):
        """Test model behavior with edge cases and boundary values."""
        # Test SMS verification with max attempts reached
        sms = SmsVerification(
            phone_number='+1234567890',
            verification_code_hash='hash',
            purpose=SMSPurpose.LOGIN,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            attempts=5,
            max_attempts=5
        )
        assert sms.attempts_remaining == 0
        
        # Test SMS verification with attempts over max
        sms.attempts = 7
        assert sms.attempts_remaining == 0  # Should not go negative
        
        # Test content report resolution time with same timestamps
        report = ContentReport(
            reporter_id=str(uuid.uuid4()),
            content_id='msg_123',
            content_type=ContentType.TEXT,
            report_category=ReportCategory.OTHER,
            status=ReportStatus.RESOLVED
        )
        now = datetime.utcnow()
        report.created_at = now
        report.resolved_at = now
        assert report.resolution_time_hours == 0.0

    @patch('models.compliance.datetime')
    def test_sms_verification_expiration_logic(self, mock_datetime):
        """Test SMS verification expiration logic with mocked time."""
        base_time = datetime(2025, 1, 13, 12, 0, 0)
        mock_datetime.utcnow.return_value = base_time
        
        # Create SMS with expiration 10 minutes from base time
        sms = SmsVerification(
            phone_number='+1234567890',
            verification_code_hash='hash',
            purpose=SMSPurpose.REGISTRATION,
            expires_at=base_time + timedelta(minutes=10)
        )
        
        # Should not be expired at base time
        assert not sms.is_expired
        
        # Mock time to 15 minutes later (5 minutes past expiration)
        mock_datetime.utcnow.return_value = base_time + timedelta(minutes=15)
        assert sms.is_expired