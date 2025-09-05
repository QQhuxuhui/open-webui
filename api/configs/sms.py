"""SMS service configuration management."""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import StrEnum


class SMSProvider(StrEnum):
    """Supported SMS providers."""
    MOCK = "mock"
    ALICLOUD = "alicloud"  
    TENCENT = "tencent"
    HUAWEI = "huawei"


@dataclass
class SMSConfig:
    """SMS service configuration."""
    # Provider settings
    provider: SMSProvider = SMSProvider.MOCK
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    
    # SMS template settings
    template_id: Optional[str] = None
    sign_name: Optional[str] = None
    
    # Verification code settings
    code_length: int = 6
    code_expiry_minutes: int = 5
    code_max_attempts: int = 5
    
    # Rate limiting settings
    phone_rate_per_minute: int = 1
    phone_rate_per_hour: int = 5  
    phone_rate_per_day: int = 10
    ip_rate_per_minute: int = 5
    ip_rate_per_hour: int = 20
    
    # Health check settings
    health_check_interval: int = 300  # 5 minutes
    health_check_timeout: int = 10    # 10 seconds
    
    # Regional settings
    region: Optional[str] = None
    endpoint: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'SMSConfig':
        """Create SMS config from environment variables."""
        return cls(
            provider=SMSProvider(os.getenv('SMS_PROVIDER', SMSProvider.MOCK)),
            access_key=os.getenv('SMS_ACCESS_KEY'),
            secret_key=os.getenv('SMS_SECRET_KEY'),
            template_id=os.getenv('SMS_TEMPLATE_ID'),
            sign_name=os.getenv('SMS_SIGN_NAME'),
            
            code_length=int(os.getenv('SMS_CODE_LENGTH', '6')),
            code_expiry_minutes=int(os.getenv('SMS_CODE_EXPIRY_MINUTES', '5')),
            code_max_attempts=int(os.getenv('SMS_CODE_MAX_ATTEMPTS', '5')),
            
            phone_rate_per_minute=int(os.getenv('SMS_PHONE_RATE_PER_MINUTE', '1')),
            phone_rate_per_hour=int(os.getenv('SMS_PHONE_RATE_PER_HOUR', '5')),
            phone_rate_per_day=int(os.getenv('SMS_PHONE_RATE_PER_DAY', '10')),
            ip_rate_per_minute=int(os.getenv('SMS_IP_RATE_PER_MINUTE', '5')),
            ip_rate_per_hour=int(os.getenv('SMS_IP_RATE_PER_HOUR', '20')),
            
            health_check_interval=int(os.getenv('SMS_HEALTH_CHECK_INTERVAL', '300')),
            health_check_timeout=int(os.getenv('SMS_HEALTH_CHECK_TIMEOUT', '10')),
            
            region=os.getenv('SMS_REGION'),
            endpoint=os.getenv('SMS_ENDPOINT')
        )

    def validate(self) -> List[str]:
        """Validate SMS configuration and return list of errors."""
        errors = []
        
        # Validate provider-specific settings
        if self.provider != SMSProvider.MOCK:
            if not self.access_key:
                errors.append(f"SMS_ACCESS_KEY is required for provider {self.provider}")
            if not self.secret_key:
                errors.append(f"SMS_SECRET_KEY is required for provider {self.provider}")
            if not self.template_id:
                errors.append(f"SMS_TEMPLATE_ID is required for provider {self.provider}")
            if not self.sign_name:
                errors.append(f"SMS_SIGN_NAME is required for provider {self.provider}")
        
        # Validate numeric settings
        if self.code_length < 4 or self.code_length > 8:
            errors.append("SMS code length must be between 4 and 8 digits")
        if self.code_expiry_minutes < 1 or self.code_expiry_minutes > 30:
            errors.append("SMS code expiry must be between 1 and 30 minutes")
        if self.code_max_attempts < 1 or self.code_max_attempts > 10:
            errors.append("SMS code max attempts must be between 1 and 10")
            
        # Validate rate limiting settings
        if self.phone_rate_per_minute < 1 or self.phone_rate_per_minute > 10:
            errors.append("Phone rate per minute must be between 1 and 10")
        if self.phone_rate_per_hour < self.phone_rate_per_minute:
            errors.append("Phone rate per hour must be >= rate per minute")  
        if self.phone_rate_per_day < self.phone_rate_per_hour:
            errors.append("Phone rate per day must be >= rate per hour")
            
        if self.ip_rate_per_minute < 1 or self.ip_rate_per_minute > 50:
            errors.append("IP rate per minute must be between 1 and 50")
        if self.ip_rate_per_hour < self.ip_rate_per_minute:
            errors.append("IP rate per hour must be >= rate per minute")
            
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excluding sensitive data)."""
        return {
            'provider': self.provider,
            'template_id': self.template_id,
            'sign_name': self.sign_name,
            'code_length': self.code_length,
            'code_expiry_minutes': self.code_expiry_minutes,
            'code_max_attempts': self.code_max_attempts,
            'phone_rate_per_minute': self.phone_rate_per_minute,
            'phone_rate_per_hour': self.phone_rate_per_hour,
            'phone_rate_per_day': self.phone_rate_per_day,
            'ip_rate_per_minute': self.ip_rate_per_minute,
            'ip_rate_per_hour': self.ip_rate_per_hour,
            'health_check_interval': self.health_check_interval,
            'health_check_timeout': self.health_check_timeout,
            'region': self.region,
            'endpoint': self.endpoint,
            # Sensitive fields excluded: access_key, secret_key
        }


# Global SMS configuration instance
sms_config = SMSConfig.from_env()