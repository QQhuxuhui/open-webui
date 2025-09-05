"""Integration tests for phone authentication flow."""

import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

from controllers.auth.phone import bp
from models.account import Account, AccountStatus
from models.compliance import UserConsent, ConsentType, SMSPurpose
from extensions.ext_database import db


class TestPhoneAuthIntegration:
    """Integration tests for complete phone authentication flow."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, app_with_db):
        """Set up test method."""
        self.app = app_with_db
        self.client = app_with_db.test_client()
        
        with app_with_db.app_context():
            # Clean up database
            db.session.query(UserConsent).delete()
            db.session.query(Account).delete()
            db.session.commit()
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    def test_complete_registration_flow(self, mock_sms_verify):
        """Test complete phone registration flow."""
        mock_sms_verify.return_value = {'success': True}
        
        phone_number = '+8613800138001'
        
        # Step 1: Check phone availability
        response = self.client.post(
            '/api/auth/phone/check-phone',
            data=json.dumps({'phone_number': phone_number}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['available'] is True
        
        # Step 2: Get agreements
        response = self.client.get('/api/auth/phone/agreements')
        assert response.status_code == 200
        agreements_data = json.loads(response.data)
        assert agreements_data['success'] is True
        
        # Step 3: Register with phone
        registration_data = {
            'phone_number': phone_number,
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {
                    'version': agreements_data['agreements']['privacy_policy']['version'],
                    'agreed': True
                },
                'terms_of_service': {
                    'version': agreements_data['agreements']['terms_of_service']['version'],
                    'agreed': True
                }
            },
            'user_info': {
                'nickname': 'IntegrationTestUser',
                'preferred_language': 'zh-CN'
            }
        }
        
        with self.app.app_context():
            response = self.client.post(
                '/api/auth/phone/register',
                data=json.dumps(registration_data),
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            user_id = data['user']['id']
            
            # Verify account was created in database
            account = db.session.query(Account).filter_by(id=user_id).first()
            assert account is not None
            assert account.phone_number == phone_number
            assert account.phone_verified is True
            assert account.nickname == 'IntegrationTestUser'
            assert account.status == AccountStatus.ACTIVE
            
            # Verify consents were recorded
            consents = db.session.query(UserConsent).filter_by(account_id=user_id).all()
            assert len(consents) == 2
            
            consent_types = {consent.consent_type for consent in consents}
            assert ConsentType.PRIVACY_POLICY in consent_types
            assert ConsentType.TERMS_OF_SERVICE in consent_types
            
            for consent in consents:
                assert consent.agreed is True
                assert consent.ip_address is not None
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    def test_complete_login_flow(self, mock_sms_verify):
        """Test complete phone login flow."""
        mock_sms_verify.return_value = {'success': True}
        
        phone_number = '+8613800138002'
        
        with self.app.app_context():
            # First create a user account
            account = Account(
                name='LoginTestUser',
                email=f'phone_user_test@temp.local',
                phone_number=phone_number,
                phone_verified=True,
                nickname='LoginTestUser',
                interface_language='zh-CN',
                status=AccountStatus.ACTIVE,
                initialized_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.session.add(account)
            db.session.commit()
            account_id = account.id
        
        # Test login
        login_data = {
            'phone_number': phone_number,
            'verification_code': '123456',
            'remember_me': True
        }
        
        with self.app.app_context():
            response = self.client.post(
                '/api/auth/phone/login',
                data=json.dumps(login_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['user']['id'] == account_id
            assert data['user']['phone_number'] == phone_number
            
            # Verify login information was updated
            updated_account = db.session.query(Account).filter_by(id=account_id).first()
            assert updated_account.last_login_at is not None
            assert updated_account.last_login_ip is not None
    
    def test_phone_already_registered_flow(self):
        """Test flow when phone number is already registered."""
        phone_number = '+8613800138003'
        
        with self.app.app_context():
            # Create existing account
            account = Account(
                name='ExistingUser',
                email=f'existing_user@temp.local',
                phone_number=phone_number,
                phone_verified=True,
                status=AccountStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.session.add(account)
            db.session.commit()
        
        # Check phone availability - should show as registered
        response = self.client.post(
            '/api/auth/phone/check-phone',
            data=json.dumps({'phone_number': phone_number}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['available'] is False
        assert data['registered'] is True
        
        # Attempt registration - should fail
        registration_data = {
            'phone_number': phone_number,
            'verification_code': '123456',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            }
        }
        
        with patch('controllers.auth.phone.sms_service.verify_code') as mock_sms_verify:
            mock_sms_verify.return_value = {'success': True}
            
            response = self.client.post(
                '/api/auth/phone/register',
                data=json.dumps(registration_data),
                content_type='application/json'
            )
            
            assert response.status_code == 409
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error'] == 'phone_already_registered'
    
    @patch('controllers.auth.phone.sms_service.verify_code')
    def test_invalid_sms_verification_flow(self, mock_sms_verify):
        """Test flow with invalid SMS verification."""
        mock_sms_verify.return_value = {'success': False, 'message': 'Invalid verification code'}
        
        # Test registration with invalid code
        registration_data = {
            'phone_number': '+8613800138004',
            'verification_code': '000000',
            'agreements': {
                'privacy_policy': {'version': '1.0', 'agreed': True},
                'terms_of_service': {'version': '1.0', 'agreed': True}
            }
        }
        
        response = self.client.post(
            '/api/auth/phone/register',
            data=json.dumps(registration_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'verification_failed'
        
        # Test login with invalid code
        login_data = {
            'phone_number': '+8613800138004',
            'verification_code': '000000'
        }
        
        response = self.client.post(
            '/api/auth/phone/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'verification_failed'
    
    def test_agreement_consent_flow(self):
        """Test agreement consent recording flow."""
        with self.app.app_context():
            # Create user account
            account = Account(
                name='ConsentTestUser',
                email='consent_test@temp.local',
                phone_number='+8613800138005',
                phone_verified=True,
                status=AccountStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.session.add(account)
            db.session.commit()
            account_id = account.id
        
        # Record consents
        consent_data = {
            'account_id': account_id,
            'consents': [
                {
                    'consent_type': 'privacy_policy',
                    'agreed': True,
                    'version': '1.0'
                },
                {
                    'consent_type': 'terms_of_service',
                    'agreed': True,
                    'version': '1.0'
                }
            ]
        }
        
        response = self.client.post(
            '/api/auth/phone/agreements/consent',
            data=json.dumps(consent_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['recorded_count'] == 2
        
        # Verify consents were recorded in database
        with self.app.app_context():
            consents = db.session.query(UserConsent).filter_by(account_id=account_id).all()
            assert len(consents) == 2
            
            for consent in consents:
                assert consent.agreed is True
                assert consent.version == '1.0'
                assert consent.ip_address is not None
                assert consent.recorded_at is not None
    
    def test_inactive_account_login_flow(self):
        """Test login flow with inactive account."""
        phone_number = '+8613800138006'
        
        with self.app.app_context():
            # Create inactive account
            account = Account(
                name='InactiveUser',
                email='inactive_user@temp.local',
                phone_number=phone_number,
                phone_verified=True,
                status=AccountStatus.BANNED,  # Inactive status
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.session.add(account)
            db.session.commit()
        
        login_data = {
            'phone_number': phone_number,
            'verification_code': '123456'
        }
        
        with patch('controllers.auth.phone.sms_service.verify_code') as mock_sms_verify:
            mock_sms_verify.return_value = {'success': True}
            
            response = self.client.post(
                '/api/auth/phone/login',
                data=json.dumps(login_data),
                content_type='application/json'
            )
            
            assert response.status_code == 403
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error'] == 'account_inactive'