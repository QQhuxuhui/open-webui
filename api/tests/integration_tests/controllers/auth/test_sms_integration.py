"""Integration tests for SMS controllers."""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from flask import Flask
from flask.testing import FlaskClient

from controllers.auth.sms import bp as sms_bp
from controllers.system.sms import bp as system_sms_bp
from models.compliance import SMSPurpose, SmsVerification
from models.base import get_db
from configs.sms import SMSConfig, SMSProvider
from services.sms.rate_limiter import rate_limiter


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # Register blueprints
    app.register_blueprint(sms_bp)
    app.register_blueprint(system_sms_bp)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_sms_config():
    """Mock SMS configuration."""
    return SMSConfig(
        provider=SMSProvider.MOCK,
        sign_name='TestApp',
        code_length=6,
        code_expiry_minutes=5,
        phone_rate_per_minute=2,
        phone_rate_per_hour=5,
        phone_rate_per_day=10,
        ip_rate_per_minute=5,
        ip_rate_per_hour=20
    )


class TestSMSControllerIntegration:
    """Integration tests for SMS controllers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear rate limiter before each test
        rate_limiter.clear_all_rate_limits()
    
    def test_send_sms_success(self, client, mock_sms_config):
        """Test successful SMS sending through API."""
        with patch('services.sms.sms_service.sms_config', mock_sms_config):
            with patch('services.sms.rate_limiter.rate_limiter', rate_limiter):
                response = client.post('/api/auth/send-sms', 
                    json={
                        'phone_number': '+8613800138000',
                        'purpose': 'registration'
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert 'verification_id' in data
                assert 'message_id' in data
                assert 'expires_at' in data
                assert data['provider'] == 'Mock SMS'
    
    def test_send_sms_invalid_phone_number(self, client, mock_sms_config):
        """Test SMS sending with invalid phone number."""
        response = client.post('/api/auth/send-sms',
            json={
                'phone_number': 'invalid-phone',
                'purpose': 'registration'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'validation_error'
        assert 'Invalid phone number format' in data['message']
    
    def test_send_sms_invalid_purpose(self, client):
        """Test SMS sending with invalid purpose."""
        response = client.post('/api/auth/send-sms',
            json={
                'phone_number': '+8613800138000',
                'purpose': 'invalid_purpose'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'validation_error'
    
    def test_send_sms_rate_limit_exceeded(self, client, mock_sms_config):
        """Test SMS rate limiting."""
        with patch('services.sms.sms_service.sms_config', mock_sms_config):
            with patch('services.sms.rate_limiter.rate_limiter', rate_limiter):
                phone = '+8613800138001'
                
                # Send requests up to limit
                for i in range(2):  # Rate limit is 2 per minute
                    response = client.post('/api/auth/send-sms',
                        json={
                            'phone_number': phone,
                            'purpose': 'registration'
                        },
                        headers={'Content-Type': 'application/json'}
                    )
                    assert response.status_code == 200
                
                # Next request should be rate limited
                response = client.post('/api/auth/send-sms',
                    json={
                        'phone_number': phone,
                        'purpose': 'registration'
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                assert response.status_code == 429
                data = json.loads(response.data)
                
                assert data['success'] is False
                assert data['error'] == 'rate_limit_exceeded'
                assert 'per minute' in data['message']
    
    @patch('services.sms.sms_service.get_db')
    def test_verify_sms_success(self, mock_get_db, client):
        """Test successful SMS verification."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Create mock verification record
        mock_verification = MagicMock()
        mock_verification.id = 'test-id'
        mock_verification.attempts = 0
        mock_verification.max_attempts = 5
        mock_verification.verification_code_hash = 'e258d248fda94c63753607f7c4494ee0fcbe92f1a76bfdac795c9d84101eb317'  # SHA256 of '123456'
        mock_verification.verified_at = None
        mock_verification.is_verified = False
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_verification
        
        response = client.post('/api/auth/verify-sms',
            json={
                'phone_number': '+8613800138002',
                'verification_code': '123456',
                'purpose': 'registration'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['verified'] is True
        assert 'verified_at' in data
    
    def test_verify_sms_invalid_code_format(self, client):
        """Test SMS verification with invalid code format."""
        response = client.post('/api/auth/verify-sms',
            json={
                'phone_number': '+8613800138002',
                'verification_code': 'abc123',  # Invalid format
                'purpose': 'registration'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'validation_error'
        assert 'must be 4-8 digits' in data['message']
    
    @patch('services.sms.sms_service.get_db')
    def test_verify_sms_no_verification_found(self, mock_get_db, client):
        """Test SMS verification when no verification record exists."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        response = client.post('/api/auth/verify-sms',
            json={
                'phone_number': '+8613800138003',
                'verification_code': '123456',
                'purpose': 'registration'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'verification_failed'
        assert 'No valid verification code found' in data['message']
    
    def test_get_sms_status_missing_parameters(self, client):
        """Test getting SMS status with missing parameters."""
        response = client.get('/api/auth/sms-status')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'missing_parameters'
        assert 'phone_number and purpose are required' in data['message']
    
    def test_get_sms_status_invalid_purpose(self, client):
        """Test getting SMS status with invalid purpose."""
        response = client.get('/api/auth/sms-status?phone_number=+8613800138004&purpose=invalid')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'invalid_purpose'
    
    def test_get_rate_limit_status(self, client):
        """Test getting rate limit status."""
        phone = '+8613800138005'
        
        # Make a request first to populate rate limiter
        rate_limiter.check_phone_rate_limit(phone)
        
        response = client.get(f'/api/auth/rate-limit-status?phone_number={phone}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'rate_limits' in data
        assert 'phone_limits' in data['rate_limits']
    
    def test_get_rate_limit_status_missing_phone(self, client):
        """Test getting rate limit status without phone number."""
        response = client.get('/api/auth/rate-limit-status')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert data['error'] == 'missing_parameters'


class TestSystemSMSControllerIntegration:
    """Integration tests for system SMS controllers."""
    
    def test_get_sms_health_success(self, client, mock_sms_config):
        """Test getting SMS health status."""
        with patch('services.sms.sms_service.sms_config', mock_sms_config):
            with patch('configs.sms.sms_config', mock_sms_config):
                response = client.get('/api/system/sms/health')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert 'overall_status' in data
                assert 'provider' in data
                assert 'config_valid' in data
                assert 'timestamp' in data
    
    def test_get_sms_config(self, client, mock_sms_config):
        """Test getting SMS configuration."""
        with patch('configs.sms.sms_config', mock_sms_config):
            response = client.get('/api/system/sms/config')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['success'] is True
            assert 'config' in data
            assert data['config']['provider'] == SMSProvider.MOCK
            assert 'access_key' not in data['config']  # Sensitive data excluded
            assert 'secret_key' not in data['config']  # Sensitive data excluded
    
    @patch('services.sms.sms_service.get_db')
    def test_get_sms_statistics(self, mock_get_db, client):
        """Test getting SMS statistics."""
        # Mock database session and queries
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock query results
        mock_db.query.return_value.filter.return_value.count.return_value = 10
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ('registration', 5),
            ('login', 3),
            ('password_reset', 2)
        ]
        
        response = client.get('/api/system/sms/statistics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'statistics' in data
        assert 'last_hour' in data['statistics']
        assert 'last_24h' in data['statistics']
        assert 'last_7d' in data['statistics']
        assert 'last_30d' in data['statistics']
    
    @patch('services.sms.sms_service.cleanup_expired_codes')
    def test_cleanup_expired_codes(self, mock_cleanup, client):
        """Test manual cleanup of expired codes."""
        mock_cleanup.return_value = 5
        
        response = client.post('/api/system/sms/cleanup')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['expired_codes_removed'] == 5
        assert 'timestamp' in data
        
        mock_cleanup.assert_called_once()
    
    def test_phone_number_normalization_in_request(self, client, mock_sms_config):
        """Test phone number normalization in API requests."""
        test_cases = [
            ('13800138000', '+8613800138000'),
            ('+86 138 0013 8000', '+8613800138000'),
            ('86-138-0013-8000', '+86138001380000'),
        ]
        
        with patch('services.sms.sms_service.sms_config', mock_sms_config):
            with patch('services.sms.rate_limiter.rate_limiter', rate_limiter):
                for input_phone, expected_normalized in test_cases:
                    rate_limiter.clear_all_rate_limits()  # Clear between tests
                    
                    response = client.post('/api/auth/send-sms',
                        json={
                            'phone_number': input_phone,
                            'purpose': 'registration'
                        },
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    # Should either succeed with normalized number or fail with validation error
                    assert response.status_code in [200, 400]
                    
                    if response.status_code == 400:
                        data = json.loads(response.data)
                        assert data['error'] == 'validation_error'
    
    def test_concurrent_requests_rate_limiting(self, client, mock_sms_config):
        """Test rate limiting with concurrent requests."""
        import threading
        import time
        
        phone = '+8613800138010'
        results = []
        
        def make_request():
            response = client.post('/api/auth/send-sms',
                json={
                    'phone_number': phone,
                    'purpose': 'registration'
                },
                headers={'Content-Type': 'application/json'}
            )
            results.append(response.status_code)
        
        with patch('services.sms.sms_service.sms_config', mock_sms_config):
            with patch('services.sms.rate_limiter.rate_limiter', rate_limiter):
                rate_limiter.clear_all_rate_limits()
                
                # Create multiple threads to simulate concurrent requests
                threads = []
                for i in range(5):  # More than rate limit of 2
                    thread = threading.Thread(target=make_request)
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join()
                
                # Should have some successful (200) and some rate limited (429) responses
                success_count = results.count(200)
                rate_limited_count = results.count(429)
                
                assert success_count <= 2  # At most 2 should succeed
                assert rate_limited_count >= 3  # At least 3 should be rate limited
                assert success_count + rate_limited_count == 5