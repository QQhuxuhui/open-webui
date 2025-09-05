"""Unit tests for SMS configuration."""

import os
import pytest
from unittest.mock import patch

from configs.sms import SMSConfig, SMSProvider


class TestSMSConfig:
    """Test SMS configuration management."""
    
    def test_default_config_creation(self):
        """Test creating SMS config with default values."""
        config = SMSConfig()
        
        assert config.provider == SMSProvider.MOCK
        assert config.code_length == 6
        assert config.code_expiry_minutes == 5
        assert config.code_max_attempts == 5
        assert config.phone_rate_per_minute == 1
        assert config.phone_rate_per_hour == 5
        assert config.phone_rate_per_day == 10
        assert config.ip_rate_per_minute == 5
        assert config.ip_rate_per_hour == 20
    
    def test_config_from_env(self):
        """Test creating SMS config from environment variables."""
        env_vars = {
            'SMS_PROVIDER': 'alicloud',
            'SMS_ACCESS_KEY': 'test_access_key',
            'SMS_SECRET_KEY': 'test_secret_key',
            'SMS_TEMPLATE_ID': 'SMS_123456',
            'SMS_SIGN_NAME': 'TestApp',
            'SMS_CODE_LENGTH': '8',
            'SMS_CODE_EXPIRY_MINUTES': '10',
            'SMS_CODE_MAX_ATTEMPTS': '3',
            'SMS_PHONE_RATE_PER_MINUTE': '2',
            'SMS_PHONE_RATE_PER_HOUR': '10',
            'SMS_PHONE_RATE_PER_DAY': '20',
            'SMS_IP_RATE_PER_MINUTE': '10',
            'SMS_IP_RATE_PER_HOUR': '40',
            'SMS_REGION': 'cn-beijing'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SMSConfig.from_env()
            
            assert config.provider == SMSProvider.ALICLOUD
            assert config.access_key == 'test_access_key'
            assert config.secret_key == 'test_secret_key'
            assert config.template_id == 'SMS_123456'
            assert config.sign_name == 'TestApp'
            assert config.code_length == 8
            assert config.code_expiry_minutes == 10
            assert config.code_max_attempts == 3
            assert config.phone_rate_per_minute == 2
            assert config.phone_rate_per_hour == 10
            assert config.phone_rate_per_day == 20
            assert config.ip_rate_per_minute == 10
            assert config.ip_rate_per_hour == 40
            assert config.region == 'cn-beijing'
    
    def test_config_validation_mock_provider(self):
        """Test validation for mock provider (should have no errors)."""
        config = SMSConfig(provider=SMSProvider.MOCK)
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_real_provider_missing_keys(self):
        """Test validation for real provider with missing credentials."""
        config = SMSConfig(
            provider=SMSProvider.ALICLOUD,
            # Missing access_key, secret_key, template_id, sign_name
        )
        errors = config.validate()
        
        assert len(errors) == 4
        assert any('SMS_ACCESS_KEY is required' in error for error in errors)
        assert any('SMS_SECRET_KEY is required' in error for error in errors)
        assert any('SMS_TEMPLATE_ID is required' in error for error in errors)
        assert any('SMS_SIGN_NAME is required' in error for error in errors)
    
    def test_config_validation_real_provider_complete(self):
        """Test validation for real provider with complete configuration."""
        config = SMSConfig(
            provider=SMSProvider.ALICLOUD,
            access_key='test_key',
            secret_key='test_secret',
            template_id='SMS_123456',
            sign_name='TestApp'
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_config_validation_invalid_ranges(self):
        """Test validation for invalid configuration ranges."""
        config = SMSConfig(
            code_length=3,  # Too short
            code_expiry_minutes=31,  # Too long
            code_max_attempts=0,  # Too few
            phone_rate_per_minute=0,  # Too few
            phone_rate_per_hour=0,  # Less than per minute
            phone_rate_per_day=1,  # Less than per hour
            ip_rate_per_minute=0,  # Too few
            ip_rate_per_hour=0  # Less than per minute
        )
        errors = config.validate()
        
        assert len(errors) >= 6
        assert any('SMS code length must be between 4 and 8' in error for error in errors)
        assert any('SMS code expiry must be between 1 and 30 minutes' in error for error in errors)
        assert any('SMS code max attempts must be between 1 and 10' in error for error in errors)
        assert any('Phone rate per minute must be between 1 and 10' in error for error in errors)
        assert any('IP rate per minute must be between 1 and 50' in error for error in errors)
    
    def test_config_to_dict(self):
        """Test converting config to dictionary (excluding sensitive data)."""
        config = SMSConfig(
            provider=SMSProvider.ALICLOUD,
            access_key='secret_key',
            secret_key='secret_secret',
            template_id='SMS_123456',
            sign_name='TestApp'
        )
        
        config_dict = config.to_dict()
        
        # Should include non-sensitive fields
        assert config_dict['provider'] == SMSProvider.ALICLOUD
        assert config_dict['template_id'] == 'SMS_123456'
        assert config_dict['sign_name'] == 'TestApp'
        
        # Should exclude sensitive fields
        assert 'access_key' not in config_dict
        assert 'secret_key' not in config_dict
    
    def test_config_rate_limit_hierarchy(self):
        """Test rate limit configuration hierarchy validation."""
        # Valid hierarchy
        config = SMSConfig(
            phone_rate_per_minute=1,
            phone_rate_per_hour=5,
            phone_rate_per_day=10
        )
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid hierarchy - hour < minute
        config = SMSConfig(
            phone_rate_per_minute=5,
            phone_rate_per_hour=3,  # Less than minute
            phone_rate_per_day=10
        )
        errors = config.validate()
        assert any('Phone rate per hour must be >= rate per minute' in error for error in errors)
        
        # Invalid hierarchy - day < hour
        config = SMSConfig(
            phone_rate_per_minute=1,
            phone_rate_per_hour=5,
            phone_rate_per_day=3  # Less than hour
        )
        errors = config.validate()
        assert any('Phone rate per day must be >= rate per hour' in error for error in errors)