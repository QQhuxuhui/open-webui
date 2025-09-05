"""Tests for phone authentication controllers."""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
import json

from controllers.auth.phone import bp
from models.account import Account, AccountStatus
from models.compliance import ConsentType


@pytest.fixture
def app():
    """Create test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.register_blueprint(bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestPhoneRegistration:
    """Test phone registration endpoint."""
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    @patch('controllers.auth.phone.PhoneAuthService')
    @patch('controllers.auth.phone.AgreementService')
    @patch('controllers.auth.phone.db.session')
    def test_successful_registration(
        self,
        mock_db_session,
        mock_agreement_service,
        mock_phone_auth_service,
        mock_sms_verify,
        client
    ):
        """Test successful phone registration."""
        # Mock SMS verification
        mock_sms_verify.return_value = {'success': True}
        
        # Mock database query
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Mock phone auth service
        mock_account = MagicMock()
        mock_account.id = 'test-user-id'
        mock_account.phone_number = '+8613800138000'
        mock_account.phone_verified = True
        mock_account.nickname = 'TestUser'
        mock_account.created_at.isoformat.return_value = '2024-01-01T00:00:00'
        mock_account.status = AccountStatus.ACTIVE
        
        mock_phone_service = MagicMock()
        mock_phone_service.create_phone_user.return_value = mock_account
        mock_phone_auth_service.return_value = mock_phone_service
        
        # Mock agreement service
        mock_agreement_service.return_value.record_consent.return_value = True
        
        # Test data
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            },
            'user_info': {
                'nickname': 'TestUser',
                'preferred_language': 'zh-CN'
            }
        }
        
        # Make request
        response = client.post(
            '/api/auth/phone/register',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        # Verify response
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['user']['id'] == 'test-user-id'
        assert data['user']['phone_number'] == '+8613800138000'
        assert data['user']['phone_verified'] is True
        
        # Verify service calls
        mock_sms_verify.assert_called_once()
        mock_phone_service.create_phone_user.assert_called_once()
    
    def test_invalid_phone_number(self, client):
        """Test registration with invalid phone number."""
        test_data = {
            'phone_number': 'invalid',
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            }
        }
        
        response = client.post(
            '/api/auth/phone/register',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'validation_error' in data['error']
    
    def test_missing_agreements(self, client):
        """Test registration with missing agreements."""
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456',
            'agreements': {}
        }
        
        response = client.post(
            '/api/auth/phone/register',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'validation_error' in data['error']
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    def test_sms_verification_failed(self, mock_sms_verify, client):
        """Test registration with failed SMS verification."""
        mock_sms_verify.return_value = {'success': False, 'message': 'Invalid code'}
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            }
        }
        
        response = client.post(
            '/api/auth/phone/register',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'verification_failed'
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    @patch('controllers.auth.phone.db.session')
    def test_phone_already_registered(self, mock_db_session, mock_sms_verify, client):
        """Test registration with already registered phone number."""
        mock_sms_verify.return_value = {'success': True}
        
        # Mock existing account
        existing_account = MagicMock()
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_account
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            }
        }
        
        response = client.post(
            '/api/auth/phone/register',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'phone_already_registered'


class TestPhoneLogin:
    """Test phone login endpoint."""
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    @patch('controllers.auth.phone.db.session')
    def test_successful_login(self, mock_db_session, mock_sms_verify, client):
        """Test successful phone login."""
        # Mock SMS verification
        mock_sms_verify.return_value = {'success': True}
        
        # Mock user account
        mock_account = MagicMock()
        mock_account.id = 'test-user-id'
        mock_account.phone_number = '+8613800138000'
        mock_account.phone_verified = True
        mock_account.status = AccountStatus.ACTIVE
        mock_account.name = 'TestUser'
        mock_account.nickname = 'TestUser'
        mock_account.avatar = None
        mock_account.interface_language = 'zh-CN'
        mock_account.interface_theme = None
        mock_account.timezone = 'Asia/Shanghai'
        mock_account.last_login_at = None
        
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_account
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456',
            'remember_me': True
        }
        
        response = client.post(
            '/api/auth/phone/login',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['user']['id'] == 'test-user-id'
        assert data['user']['phone_number'] == '+8613800138000'
        
        # Verify account was updated
        mock_db_session.commit.assert_called()
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    def test_invalid_verification_code(self, mock_sms_verify, client):
        """Test login with invalid verification code."""
        mock_sms_verify.return_value = {'success': False, 'message': 'Invalid code'}
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456'
        }
        
        response = client.post(
            '/api/auth/phone/login',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'verification_failed'
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    @patch('controllers.auth.phone.db.session')
    def test_account_not_found(self, mock_db_session, mock_sms_verify, client):
        """Test login with non-existent account."""
        mock_sms_verify.return_value = {'success': True}
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456'
        }
        
        response = client.post(
            '/api/auth/phone/login',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'account_not_found'
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    @patch('controllers.auth.phone.db.session')
    def test_inactive_account(self, mock_db_session, mock_sms_verify, client):
        """Test login with inactive account."""
        mock_sms_verify.return_value = {'success': True}
        
        mock_account = MagicMock()
        mock_account.status = AccountStatus.BANNED
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_account
        
        test_data = {
            'phone_number': '+8613800138000',
            'verification_code': '123456'
        }
        
        response = client.post(
            '/api/auth/phone/login',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'account_inactive'


class TestCheckPhone:
    """Test check phone availability endpoint."""
    
    @patch('controllers.auth.phone.db.session')
    def test_phone_available(self, mock_db_session, client):
        """Test checking available phone number."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        test_data = {
            'phone_number': '+8613800138000'
        }
        
        response = client.post(
            '/api/auth/phone/check-phone',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['available'] is True
        assert data['registered'] is False
    
    @patch('controllers.auth.phone.db.session')
    def test_phone_registered(self, mock_db_session, client):
        """Test checking registered phone number."""
        existing_account = MagicMock()
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_account
        
        test_data = {
            'phone_number': '+8613800138000'
        }
        
        response = client.post(
            '/api/auth/phone/check-phone',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['available'] is False
        assert data['registered'] is True
    
    def test_missing_phone_number(self, client):
        """Test checking without phone number."""
        test_data = {}
        
        response = client.post(
            '/api/auth/phone/check-phone',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'missing_parameter'


class TestAgreements:
    """Test agreement endpoints."""
    
    @patch('controllers.auth.phone.AgreementService')
    def test_get_agreements(self, mock_agreement_service, client):
        """Test getting agreements."""
        mock_service = MagicMock()
        mock_service.get_agreements.return_value = {
            'privacy_policy': {
                'version': '1.0',
                'content': 'Privacy policy content',
                'last_updated': '2024-01-01T00:00:00'
            },
            'terms_of_service': {
                'version': '1.0',
                'content': 'Terms of service content',
                'last_updated': '2024-01-01T00:00:00'
            }
        }
        mock_agreement_service.return_value = mock_service
        
        response = client.get('/api/auth/phone/agreements')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'agreements' in data
        assert 'privacy_policy' in data['agreements']
        assert 'terms_of_service' in data['agreements']
    
    @patch('controllers.auth.phone.AgreementService')
    def test_record_consent(self, mock_agreement_service, client):
        """Test recording consent."""
        mock_service = MagicMock()
        mock_service.record_consent.return_value = True
        mock_agreement_service.return_value = mock_service
        
        test_data = {
            'account_id': 'test-user-id',
            'consents': [
                {
                    'consent_type': 'privacy_policy',
                    'agreed': True,
                    'version': '1.0'
                }
            ]
        }
        
        response = client.post(
            '/api/auth/phone/agreements/consent',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['recorded_count'] == 1
        
        # Verify service call
        mock_service.record_consent.assert_called_once()
    
    def test_record_consent_missing_parameters(self, client):
        """Test recording consent with missing parameters."""
        test_data = {}
        
        response = client.post(
            '/api/auth/phone/agreements/consent',
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'missing_parameters'