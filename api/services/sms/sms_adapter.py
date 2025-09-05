"""Base SMS adapter interface and result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import StrEnum
from datetime import datetime

from configs.sms import SMSConfig
from models.compliance import SMSPurpose


class SMSStatus(StrEnum):
    """SMS sending status."""
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    INVALID_NUMBER = "invalid_number"
    PROVIDER_ERROR = "provider_error"
    NETWORK_ERROR = "network_error"


@dataclass
class SMSResult:
    """Result of SMS sending operation."""
    status: SMSStatus
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    cost: Optional[float] = None  # Cost in provider's currency
    sent_at: Optional[datetime] = None
    
    @property
    def is_success(self) -> bool:
        """Check if SMS was sent successfully."""
        return self.status == SMSStatus.SUCCESS
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if SMS failed due to rate limiting."""
        return self.status == SMSStatus.RATE_LIMITED


class SMSAdapter(ABC):
    """Base class for SMS service adapters."""
    
    def __init__(self, config: SMSConfig):
        """Initialize SMS adapter with configuration."""
        self.config = config
        self._last_health_check: Optional[datetime] = None
        self._is_healthy = True
    
    @abstractmethod
    async def send_sms(
        self,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> SMSResult:
        """
        Send SMS verification code to phone number.
        
        Args:
            phone_number: Target phone number in international format
            verification_code: Verification code to send
            purpose: Purpose of the verification (registration, login, etc.)
            template_vars: Additional template variables
            
        Returns:
            SMSResult with status and details
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if SMS provider service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return self.__class__.__name__.replace('SMSAdapter', '')
    
    def is_healthy(self) -> bool:
        """Get cached health status."""
        return self._is_healthy
    
    def get_last_health_check(self) -> Optional[datetime]:
        """Get timestamp of last health check."""
        return self._last_health_check
    
    def _update_health_status(self, is_healthy: bool) -> None:
        """Update health status and timestamp."""
        self._is_healthy = is_healthy
        self._last_health_check = datetime.utcnow()
    
    def _normalize_phone_number(self, phone_number: str) -> str:
        """
        Normalize phone number to international format.
        
        Args:
            phone_number: Raw phone number
            
        Returns:
            Normalized phone number (e.g., +8613800138000)
        """
        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if missing (assume China +86 for now)
        if not phone_number.startswith('+'):
            if digits.startswith('86'):
                return f'+{digits}'
            elif len(digits) == 11 and digits.startswith('1'):
                return f'+86{digits}'
            else:
                return f'+{digits}'
        
        return phone_number
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        normalized = self._normalize_phone_number(phone_number)
        
        # Basic validation - starts with + and has 10-15 digits
        if not normalized.startswith('+'):
            return False
            
        digits = normalized[1:]  # Remove +
        if not digits.isdigit():
            return False
            
        if len(digits) < 10 or len(digits) > 15:
            return False
            
        return True
    
    def _get_template_content(self, purpose: SMSPurpose) -> str:
        """
        Get SMS template content based on purpose.
        
        Args:
            purpose: SMS purpose
            
        Returns:
            Template content string
        """
        templates = {
            SMSPurpose.REGISTRATION: "【{sign_name}】您的注册验证码为：{code}，{expiry}分钟内有效，请勿泄露。",
            SMSPurpose.LOGIN: "【{sign_name}】您的登录验证码为：{code}，{expiry}分钟内有效，请勿泄露。", 
            SMSPurpose.PHONE_CHANGE: "【{sign_name}】您的手机变更验证码为：{code}，{expiry}分钟内有效，请勿泄露。",
            SMSPurpose.PASSWORD_RESET: "【{sign_name}】您的密码重置验证码为：{code}，{expiry}分钟内有效，请勿泄露。"
        }
        return templates.get(purpose, templates[SMSPurpose.REGISTRATION])