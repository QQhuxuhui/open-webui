"""Unit tests for Mock SMS adapter."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock

from configs.sms import SMSConfig, SMSProvider
from services.sms.providers.mock import MockSMSAdapter
from services.sms.sms_adapter import SMSStatus
from models.compliance import SMSPurpose


class TestMockSMSAdapter:
    """Test Mock SMS adapter implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = SMSConfig(
            provider=SMSProvider.MOCK,
            sign_name='TestApp',
            code_length=6,
            code_expiry_minutes=5
        )
        self.adapter = MockSMSAdapter(self.config)
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS sending."""
        result = await self.adapter.send_sms(
            phone_number='+8613800138000',
            verification_code='123456',
            purpose=SMSPurpose.REGISTRATION
        )
        
        assert result.is_success
        assert result.status == SMSStatus.SUCCESS
        assert result.message_id is not None
        assert result.message_id.startswith('mock_')
        assert result.cost == 0.05
        assert result.sent_at is not None
        assert isinstance(result.sent_at, datetime)
    
    @pytest.mark.asyncio
    async def test_send_sms_invalid_phone_number(self):
        """Test SMS sending with invalid phone number."""
        result = await self.adapter.send_sms(
            phone_number='invalid',
            verification_code='123456',
            purpose=SMSPurpose.REGISTRATION
        )
        
        assert not result.is_success
        assert result.status == SMSStatus.INVALID_NUMBER
        assert 'Invalid phone number format' in result.error_message
        assert result.message_id is None
    
    @pytest.mark.asyncio
    async def test_send_sms_with_failure_configured(self):
        """Test SMS sending when failure is configured."""
        self.adapter.set_should_fail(True)
        
        result = await self.adapter.send_sms(
            phone_number='+8613800138000',
            verification_code='123456',
            purpose=SMSPurpose.LOGIN
        )
        
        assert not result.is_success
        assert result.status == SMSStatus.PROVIDER_ERROR
        assert 'Mock SMS provider error' in result.error_message
    
    @pytest.mark.asyncio
    async def test_send_sms_with_random_failure_rate(self):
        """Test SMS sending with random failure rate."""
        self.adapter.set_failure_rate(1.0)  # 100% failure rate
        
        result = await self.adapter.send_sms(
            phone_number='+8613800138000',
            verification_code='123456',
            purpose=SMSPurpose.PASSWORD_RESET
        )
        
        assert not result.is_success
        assert result.status == SMSStatus.PROVIDER_ERROR
    
    @pytest.mark.asyncio
    async def test_send_sms_message_storage(self):
        """Test that sent messages are stored for testing purposes."""
        self.adapter.clear_sent_messages()
        
        await self.adapter.send_sms(
            phone_number='+8613800138001',
            verification_code='111111',
            purpose=SMSPurpose.REGISTRATION
        )
        
        await self.adapter.send_sms(
            phone_number='+8613800138002',
            verification_code='222222',
            purpose=SMSPurpose.LOGIN
        )
        
        sent_messages = self.adapter.get_sent_messages()
        assert len(sent_messages) == 2
        
        assert sent_messages[0]['phone_number'] == '+8613800138001'
        assert sent_messages[0]['verification_code'] == '111111'
        assert sent_messages[0]['purpose'] == SMSPurpose.REGISTRATION
        
        assert sent_messages[1]['phone_number'] == '+8613800138002'
        assert sent_messages[1]['verification_code'] == '222222'
        assert sent_messages[1]['purpose'] == SMSPurpose.LOGIN
    
    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test health check when adapter is healthy."""
        is_healthy = await self.adapter.check_health()
        
        assert is_healthy is True
        assert self.adapter.is_healthy() is True
        assert self.adapter.get_last_health_check() is not None
    
    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check when adapter is configured to fail."""
        self.adapter.set_should_fail(True)
        
        is_healthy = await self.adapter.check_health()
        
        assert is_healthy is False
        assert self.adapter.is_healthy() is False
        assert self.adapter.get_last_health_check() is not None
    
    def test_phone_number_normalization(self):
        """Test phone number normalization."""
        # Test various phone number formats
        test_cases = [
            ('+8613800138000', '+8613800138000'),
            ('13800138000', '+8613800138000'),
            ('8613800138000', '+868613800138000'),  # Adds + prefix
            ('+86 138 0013 8000', '+8613800138000'),  # Should be handled by validation
        ]
        
        for input_phone, expected in test_cases:
            if 'validation' not in expected:  # Skip validation test cases
                normalized = self.adapter._normalize_phone_number(input_phone)
                assert normalized == expected
    
    def test_phone_number_validation(self):
        """Test phone number validation."""
        valid_numbers = [
            '+8613800138000',
            '+14155552345',
            '+442071234567'
        ]
        
        invalid_numbers = [
            'invalid',
            '123',  # Too short
            '+123456789012345678',  # Too long
            'abc123def456',
            ''
        ]
        
        for number in valid_numbers:
            assert self.adapter._validate_phone_number(number) is True
        
        for number in invalid_numbers:
            assert self.adapter._validate_phone_number(number) is False
    
    @pytest.mark.asyncio
    async def test_template_content_generation(self):
        """Test SMS template content generation."""
        result = await self.adapter.send_sms(
            phone_number='+8613800138000',
            verification_code='123456',
            purpose=SMSPurpose.REGISTRATION
        )
        
        sent_messages = self.adapter.get_sent_messages()
        message_content = sent_messages[-1]['content']
        
        assert '123456' in message_content
        assert 'TestApp' in message_content or 'MockApp' in message_content
        assert str(self.config.code_expiry_minutes) in message_content
    
    def test_provider_name(self):
        """Test provider name retrieval."""
        name = self.adapter.get_provider_name()
        assert name == 'Mock SMS'
    
    def test_failure_rate_bounds(self):
        """Test that failure rate is properly bounded."""
        # Test setting failure rate outside bounds
        self.adapter.set_failure_rate(-0.5)  # Below 0
        assert self.adapter._failure_rate == 0.0
        
        self.adapter.set_failure_rate(1.5)  # Above 1
        assert self.adapter._failure_rate == 1.0
        
        self.adapter.set_failure_rate(0.3)  # Valid range
        assert self.adapter._failure_rate == 0.3
    
    def test_sent_messages_management(self):
        """Test sent messages list management."""
        # Initially empty
        assert len(self.adapter.get_sent_messages()) == 0
        
        # Add some mock messages (for testing internal state)
        self.adapter._sent_messages.append({
            'message_id': 'test_1',
            'phone_number': '+8613800138000',
            'verification_code': '123456'
        })
        
        assert len(self.adapter.get_sent_messages()) == 1
        
        # Clear messages
        self.adapter.clear_sent_messages()
        assert len(self.adapter.get_sent_messages()) == 0