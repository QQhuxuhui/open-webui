"""Story 1.2 acceptance criteria validation tests."""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock

from configs.sms import SMSConfig, SMSProvider
from services.sms import SMSFactory, sms_service
from services.sms.rate_limiter import rate_limiter
from models.compliance import SMSPurpose


class TestStory12AcceptanceCriteria:
    """Validate Story 1.2 acceptance criteria implementation."""
    
    def test_ac1_sms_adapter_providers(self):
        """AC1: SMS服务适配器实现 - Test SMS adapter implementation with multiple providers."""
        # Test Mock provider
        config_mock = SMSConfig(provider=SMSProvider.MOCK)
        adapter_mock = SMSFactory.create_adapter(config_mock)
        assert adapter_mock is not None
        assert adapter_mock.get_provider_name() == 'Mock SMS'
        
        # Test Alicloud provider registration
        config_ali = SMSConfig(
            provider=SMSProvider.ALICLOUD,
            access_key='test_key',
            secret_key='test_secret',
            template_id='SMS_123456',
            sign_name='TestApp'
        )
        adapter_ali = SMSFactory.create_adapter(config_ali)
        assert adapter_ali is not None
        assert adapter_ali.get_provider_name() == 'Alibaba Cloud SMS'
        
        # Test Tencent provider registration
        config_tencent = SMSConfig(
            provider=SMSProvider.TENCENT,
            access_key='test_key',
            secret_key='test_secret',
            template_id='SMS_123456',
            sign_name='TestApp'
        )
        adapter_tencent = SMSFactory.create_adapter(config_tencent)
        assert adapter_tencent is not None
        assert adapter_tencent.get_provider_name() == 'Tencent Cloud SMS'
        
        # Test unified interface
        assert hasattr(adapter_mock, 'send_sms')
        assert hasattr(adapter_mock, 'check_health')
        assert hasattr(adapter_ali, 'send_sms')
        assert hasattr(adapter_ali, 'check_health')
    
    def test_ac2_configuration_management(self):
        """AC2: 配置管理系统 - Test SMS configuration management."""
        # Test environment variable configuration
        config = SMSConfig.from_env()
        assert config is not None
        assert config.provider in [SMSProvider.MOCK, SMSProvider.ALICLOUD, SMSProvider.TENCENT, SMSProvider.HUAWEI]
        
        # Test configuration validation
        valid_config = SMSConfig(
            provider=SMSProvider.ALICLOUD,
            access_key='test_key',
            secret_key='test_secret',
            template_id='SMS_123456',
            sign_name='TestApp'
        )
        errors = valid_config.validate()
        assert len(errors) == 0
        
        # Test invalid configuration
        invalid_config = SMSConfig(
            provider=SMSProvider.ALICLOUD
            # Missing required fields
        )
        errors = invalid_config.validate()
        assert len(errors) > 0
        
        # Test runtime configuration switching
        SMSFactory.clear_cache()
        adapter1 = SMSFactory.create_adapter(SMSConfig(provider=SMSProvider.MOCK))
        adapter2 = SMSFactory.create_adapter(valid_config)
        assert adapter1.get_provider_name() != adapter2.get_provider_name()
    
    @pytest.mark.asyncio
    async def test_ac3_verification_code_flow(self):
        """AC3: 验证码完整流程 - Test complete verification code flow."""
        config = SMSConfig(
            provider=SMSProvider.MOCK,
            code_length=8,  # Test configurable length
            code_expiry_minutes=10,  # Test configurable expiry
            sign_name='TestApp'
        )
        
        with patch('services.sms.sms_service.sms_config', config):
            with patch('services.sms.sms_service.get_db'):
                # Test code generation
                service = sms_service
                code = service._generate_code()
                assert len(code) == 8  # Configurable length
                assert code.isdigit()
                
                # Test code hashing
                hash1 = service._hash_code('123456')
                hash2 = service._hash_code('123456')
                hash3 = service._hash_code('654321')
                assert hash1 == hash2  # Same code produces same hash
                assert hash1 != hash3  # Different codes produce different hashes
                assert len(hash1) == 64  # SHA-256 produces 64-char hex string
                
                # Test phone number validation through adapter
                adapter = SMSFactory.create_adapter(config)
                assert adapter._validate_phone_number('+8613800138000') is True
                assert adapter._validate_phone_number('invalid') is False
    
    def test_ac4_rate_limiting_and_anti_spam(self):
        """AC4: 防刷和频率限制 - Test rate limiting and anti-spam mechanisms."""
        config = SMSConfig(
            phone_rate_per_minute=2,
            phone_rate_per_hour=5,
            phone_rate_per_day=10,
            ip_rate_per_minute=3,
            ip_rate_per_hour=15
        )
        
        limiter = rate_limiter
        limiter.clear_all_rate_limits()
        
        phone = '+8613800138000'
        ip = '192.168.1.100'
        
        # Test phone number rate limiting
        for i in range(2):  # Within limit
            allowed, error = limiter.check_phone_rate_limit(phone)
            assert allowed is True
            assert error is None
        
        # Exceed limit
        allowed, error = limiter.check_phone_rate_limit(phone)
        assert allowed is False
        assert 'per minute' in error
        
        # Test IP address rate limiting
        limiter.clear_all_rate_limits()
        for i in range(3):  # Within limit
            allowed, error = limiter.check_ip_rate_limit(ip)
            assert allowed is True
        
        # Exceed limit
        allowed, error = limiter.check_ip_rate_limit(ip)
        assert allowed is False
        assert 'per minute' in error
        
        # Test combined rate limiting
        limiter.clear_all_rate_limits()
        allowed, error = limiter.check_rate_limits(phone, ip)
        assert allowed is True
        
        # Test rate limit status reporting
        status = limiter.get_rate_limit_status(phone, ip)
        assert 'phone_limits' in status
        assert 'ip_limits' in status
        assert len(status['phone_limits']) == 3  # minute, hour, day
        assert len(status['ip_limits']) == 2   # minute, hour
    
    @pytest.mark.asyncio
    async def test_ac5_health_check_and_degradation(self):
        """AC5: 健康检查和降级 - Test health check and graceful degradation."""
        config = SMSConfig(provider=SMSProvider.MOCK)
        adapter = SMSFactory.create_adapter(config)
        
        # Test successful health check
        is_healthy = await adapter.check_health()
        assert is_healthy is True
        assert adapter.is_healthy() is True
        assert adapter.get_last_health_check() is not None
        
        # Test health check with failure
        from services.sms.providers.mock import MockSMSAdapter
        if isinstance(adapter, MockSMSAdapter):
            adapter.set_should_fail(True)
            is_healthy = await adapter.check_health()
            assert is_healthy is False
            assert adapter.is_healthy() is False
        
        # Test service health status
        service = sms_service
        health_status = await service.get_health_status()
        assert 'status' in health_status
        assert 'provider' in health_status
        assert 'config_valid' in health_status
        
        # Test configuration validation as part of health
        invalid_config = SMSConfig(provider=SMSProvider.ALICLOUD)  # Missing required fields
        errors = invalid_config.validate()
        assert len(errors) > 0
    
    def test_api_endpoints_specification(self):
        """Test that API endpoints match the specification."""
        from controllers.auth.sms import bp as auth_bp
        from controllers.system.sms import bp as system_bp
        
        # Check auth blueprint endpoints
        auth_rules = [rule.rule for rule in auth_bp.url_map.iter_rules()]
        assert '/api/auth/send-sms' in [rule for rule in auth_rules if 'send-sms' in rule]
        assert '/api/auth/verify-sms' in [rule for rule in auth_rules if 'verify-sms' in rule]
        
        # Check system blueprint endpoints  
        system_rules = [rule.rule for rule in system_bp.url_map.iter_rules()]
        assert '/api/system/sms/health' in [rule for rule in system_rules if 'health' in rule]
    
    def test_environment_variable_support(self):
        """Test support for all required environment variables."""
        import os
        from unittest.mock import patch
        
        env_vars = {
            'SMS_PROVIDER': 'alicloud',
            'SMS_ACCESS_KEY': 'test_access_key',
            'SMS_SECRET_KEY': 'test_secret_key',
            'SMS_TEMPLATE_ID': 'SMS_123456',
            'SMS_SIGN_NAME': 'TestApp',
            'SMS_CODE_LENGTH': '6',
            'SMS_CODE_EXPIRY_MINUTES': '5',
            'SMS_CODE_MAX_ATTEMPTS': '5',
            'SMS_PHONE_RATE_PER_MINUTE': '1',
            'SMS_PHONE_RATE_PER_HOUR': '5',
            'SMS_PHONE_RATE_PER_DAY': '10',
            'SMS_IP_RATE_PER_MINUTE': '5',
            'SMS_IP_RATE_PER_HOUR': '20',
            'SMS_REGION': 'cn-beijing',
            'SMS_ENDPOINT': 'sms.example.com'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SMSConfig.from_env()
            
            assert config.provider == SMSProvider.ALICLOUD
            assert config.access_key == 'test_access_key'
            assert config.secret_key == 'test_secret_key'
            assert config.template_id == 'SMS_123456'
            assert config.sign_name == 'TestApp'
            assert config.code_length == 6
            assert config.code_expiry_minutes == 5
            assert config.code_max_attempts == 5
            assert config.phone_rate_per_minute == 1
            assert config.phone_rate_per_hour == 5
            assert config.phone_rate_per_day == 10
            assert config.ip_rate_per_minute == 5
            assert config.ip_rate_per_hour == 20
            assert config.region == 'cn-beijing'
            assert config.endpoint == 'sms.example.com'
    
    def test_security_requirements(self):
        """Test security requirements implementation."""
        service = sms_service
        
        # Test code hashing (not plaintext storage)
        code = '123456'
        hash_result = service._hash_code(code)
        assert hash_result != code  # Must be hashed, not plaintext
        assert len(hash_result) == 64  # SHA-256 hash length
        
        # Test phone number validation
        adapter = SMSFactory.create_adapter(SMSConfig(provider=SMSProvider.MOCK))
        assert adapter._validate_phone_number('+8613800138000') is True
        assert adapter._validate_phone_number('invalid') is False
        
        # Test configuration excludes sensitive data in to_dict()
        config = SMSConfig(
            access_key='sensitive_key',
            secret_key='sensitive_secret',
            template_id='SMS_123456'
        )
        config_dict = config.to_dict()
        assert 'access_key' not in config_dict
        assert 'secret_key' not in config_dict
        assert 'template_id' in config_dict  # Non-sensitive data included
    
    def test_rate_limiting_specifications(self):
        """Test that rate limiting matches the specified rules."""
        config = SMSConfig(
            phone_rate_per_minute=1,
            phone_rate_per_hour=5,
            phone_rate_per_day=10,
            ip_rate_per_minute=5,
            ip_rate_per_hour=20
        )
        
        # Validate configuration matches specification
        assert config.phone_rate_per_minute == 1
        assert config.phone_rate_per_hour == 5
        assert config.phone_rate_per_day == 10
        assert config.ip_rate_per_minute == 5
        assert config.ip_rate_per_hour == 20
        
        # Test hierarchy validation
        errors = config.validate()
        assert len(errors) == 0  # Should be valid hierarchy
        
        # Test invalid hierarchy
        invalid_config = SMSConfig(
            phone_rate_per_minute=5,
            phone_rate_per_hour=3,  # Less than per minute
            phone_rate_per_day=2    # Less than per hour
        )
        errors = invalid_config.validate()
        assert len(errors) > 0  # Should have validation errors
    
    @pytest.mark.asyncio
    async def test_provider_abstraction(self):
        """Test that provider differences are properly abstracted."""
        # Test that all providers implement the same interface
        providers = [
            (SMSProvider.MOCK, {}),
            (SMSProvider.ALICLOUD, {
                'access_key': 'test_key',
                'secret_key': 'test_secret', 
                'template_id': 'SMS_123456',
                'sign_name': 'TestApp'
            }),
            (SMSProvider.TENCENT, {
                'access_key': 'test_key',
                'secret_key': 'test_secret',
                'template_id': 'SMS_123456', 
                'sign_name': 'TestApp'
            })
        ]
        
        for provider, extra_config in providers:
            config = SMSConfig(provider=provider, **extra_config)
            adapter = SMSFactory.create_adapter(config)
            
            # All adapters should have the same interface
            assert hasattr(adapter, 'send_sms')
            assert hasattr(adapter, 'check_health')
            assert hasattr(adapter, 'get_provider_name')
            assert hasattr(adapter, 'is_healthy')
            assert hasattr(adapter, 'get_last_health_check')
            
            # All should return health status
            health = await adapter.check_health()
            assert isinstance(health, bool)
            
            # All should have provider names
            name = adapter.get_provider_name()
            assert isinstance(name, str)
            assert len(name) > 0