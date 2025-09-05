"""Mock SMS adapter for development and testing."""

import asyncio
import random
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from ..sms_adapter import SMSAdapter, SMSResult, SMSStatus
from models.compliance import SMSPurpose

logger = logging.getLogger(__name__)


class MockSMSAdapter(SMSAdapter):
    """Mock SMS adapter for development and testing."""
    
    def __init__(self, config):
        """Initialize mock SMS adapter."""
        super().__init__(config)
        self._sent_messages = []  # Store sent messages for testing
        self._should_fail = False  # For testing failure scenarios
        self._failure_rate = 0.0   # Simulate random failures (0.0 - 1.0)
    
    async def send_sms(
        self,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> SMSResult:
        """
        Mock SMS sending - logs the message instead of sending.
        
        Args:
            phone_number: Target phone number
            verification_code: Verification code to send
            purpose: Purpose of verification
            template_vars: Additional template variables
            
        Returns:
            SMSResult with mock data
        """
        # Validate phone number
        if not self._validate_phone_number(phone_number):
            return SMSResult(
                status=SMSStatus.INVALID_NUMBER,
                error_message=f"Invalid phone number format: {phone_number}",
                sent_at=datetime.utcnow()
            )
        
        # Normalize phone number
        normalized_phone = self._normalize_phone_number(phone_number)
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate random failures if configured
        if self._should_fail or (self._failure_rate > 0 and random.random() < self._failure_rate):
            return SMSResult(
                status=SMSStatus.PROVIDER_ERROR,
                error_message="Mock SMS provider error",
                sent_at=datetime.utcnow()
            )
        
        # Generate mock message ID
        message_id = f"mock_{uuid4().hex[:8]}"
        
        # Get template content
        template_content = self._get_template_content(purpose)
        
        # Format message
        message_content = template_content.format(
            sign_name=self.config.sign_name or "MockApp",
            code=verification_code,
            expiry=self.config.code_expiry_minutes,
            **(template_vars or {})
        )
        
        # Store message for testing purposes
        sent_message = {
            'message_id': message_id,
            'phone_number': normalized_phone,
            'verification_code': verification_code,
            'purpose': purpose,
            'content': message_content,
            'sent_at': datetime.utcnow()
        }
        self._sent_messages.append(sent_message)
        
        # Log the mock SMS (for development)
        logger.info(
            f"[MOCK SMS] To: {normalized_phone}, "
            f"Code: {verification_code}, "
            f"Purpose: {purpose}, "
            f"Message: {message_content}"
        )
        
        return SMSResult(
            status=SMSStatus.SUCCESS,
            message_id=message_id,
            provider_response={
                'mock_provider': 'success',
                'message_content': message_content,
                'phone_number': normalized_phone
            },
            cost=0.05,  # Mock cost in RMB
            sent_at=datetime.utcnow()
        )
    
    async def check_health(self) -> bool:
        """
        Mock health check - always returns True unless configured otherwise.
        
        Returns:
            Always True (healthy) for mock provider
        """
        # Simulate health check delay
        await asyncio.sleep(0.01)
        
        is_healthy = not self._should_fail
        self._update_health_status(is_healthy)
        
        logger.debug(f"Mock SMS health check: {is_healthy}")
        return is_healthy
    
    def get_sent_messages(self) -> list:
        """Get list of sent messages (for testing)."""
        return self._sent_messages.copy()
    
    def clear_sent_messages(self) -> None:
        """Clear sent messages list (for testing)."""
        self._sent_messages.clear()
    
    def set_should_fail(self, should_fail: bool) -> None:
        """Configure mock adapter to fail (for testing)."""
        self._should_fail = should_fail
    
    def set_failure_rate(self, failure_rate: float) -> None:
        """Set random failure rate between 0.0 and 1.0 (for testing)."""
        self._failure_rate = max(0.0, min(1.0, failure_rate))
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Mock SMS"