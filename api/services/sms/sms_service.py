"""Main SMS service for verification code management."""

import secrets
import string
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from configs.sms import SMSConfig, sms_config
from models.compliance import SmsVerification, SMSPurpose
from models.base import get_db
from .sms_factory import SMSFactory
from .sms_adapter import SMSResult, SMSStatus

logger = logging.getLogger(__name__)


class SMSServiceError(Exception):
    """Base exception for SMS service errors."""
    pass


class RateLimitExceededError(SMSServiceError):
    """Raised when SMS rate limit is exceeded."""
    pass


class VerificationCodeError(SMSServiceError):
    """Raised when verification code operations fail."""
    pass


class SMSService:
    """Main SMS service for managing verification codes."""
    
    def __init__(self, config: Optional[SMSConfig] = None):
        """Initialize SMS service."""
        self.config = config or sms_config
        self._adapter = None
        
    @property
    def adapter(self):
        """Get SMS adapter instance (lazy loading)."""
        if self._adapter is None:
            self._adapter = SMSFactory.create_adapter(self.config)
        return self._adapter
    
    async def send_verification_code(
        self,
        phone_number: str,
        purpose: SMSPurpose,
        ip_address: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS verification code to phone number.
        
        Args:
            phone_number: Target phone number
            purpose: Purpose of verification
            ip_address: Client IP address for rate limiting
            template_vars: Additional template variables
            
        Returns:
            Dictionary with result information
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            SMSServiceError: If SMS service fails
        """
        with get_db() as db:
            # Check rate limits
            self._check_rate_limits(db, phone_number, ip_address)
            
            # Generate verification code
            verification_code = self._generate_code()
            
            # Send SMS through adapter
            result = await self.adapter.send_sms(
                phone_number=phone_number,
                verification_code=verification_code,
                purpose=purpose,
                template_vars=template_vars
            )
            
            if result.is_success:
                # Store verification record
                sms_verification = self._store_verification(
                    db, phone_number, verification_code, purpose
                )
                
                logger.info(
                    f"SMS sent successfully: phone={phone_number}, "
                    f"purpose={purpose}, message_id={result.message_id}"
                )
                
                return {
                    'success': True,
                    'verification_id': sms_verification.id,
                    'message_id': result.message_id,
                    'expires_at': sms_verification.expires_at.isoformat(),
                    'attempts_remaining': sms_verification.attempts_remaining,
                    'provider': self.adapter.get_provider_name()
                }
            else:
                # Handle different failure scenarios
                if result.is_rate_limited:
                    raise RateLimitExceededError("SMS rate limit exceeded by provider")
                else:
                    logger.error(
                        f"SMS send failed: phone={phone_number}, "
                        f"status={result.status}, error={result.error_message}"
                    )
                    raise SMSServiceError(f"Failed to send SMS: {result.error_message}")
    
    def verify_code(
        self,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose,
        auto_cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Verify SMS verification code.
        
        Args:
            phone_number: Phone number to verify
            verification_code: Code to verify
            purpose: Purpose of verification
            auto_cleanup: Whether to cleanup after verification
            
        Returns:
            Dictionary with verification result
            
        Raises:
            VerificationCodeError: If verification fails
        """
        with get_db() as db:
            # Find active verification record
            sms_verification = db.query(SmsVerification).filter(
                and_(
                    SmsVerification.phone_number == phone_number,
                    SmsVerification.purpose == purpose,
                    SmsVerification.verified_at.is_(None),
                    SmsVerification.expires_at > datetime.utcnow()
                )
            ).order_by(SmsVerification.created_at.desc()).first()
            
            if not sms_verification:
                raise VerificationCodeError("No valid verification code found")
            
            # Check if too many attempts
            if sms_verification.attempts >= sms_verification.max_attempts:
                raise VerificationCodeError("Too many verification attempts")
            
            # Increment attempt count
            sms_verification.attempts += 1
            
            # Verify code
            code_hash = self._hash_code(verification_code)
            
            if sms_verification.verification_code_hash == code_hash:
                # Success - mark as verified
                sms_verification.verified_at = datetime.utcnow()
                db.commit()
                
                # Cleanup expired codes if requested
                if auto_cleanup:
                    self.cleanup_expired_codes()
                
                logger.info(
                    f"SMS verification successful: phone={phone_number}, purpose={purpose}"
                )
                
                return {
                    'success': True,
                    'verified': True,
                    'verification_id': sms_verification.id,
                    'verified_at': sms_verification.verified_at.isoformat()
                }
            else:
                # Failed verification
                db.commit()  # Save attempt count
                
                attempts_remaining = max(0, sms_verification.max_attempts - sms_verification.attempts)
                
                logger.warning(
                    f"SMS verification failed: phone={phone_number}, "
                    f"purpose={purpose}, attempts_remaining={attempts_remaining}"
                )
                
                if attempts_remaining == 0:
                    raise VerificationCodeError("Verification code attempts exhausted")
                else:
                    raise VerificationCodeError(f"Invalid verification code. {attempts_remaining} attempts remaining")
    
    def get_verification_status(
        self,
        phone_number: str,
        purpose: SMSPurpose
    ) -> Optional[Dict[str, Any]]:
        """
        Get status of most recent verification for phone/purpose.
        
        Args:
            phone_number: Phone number to check
            purpose: Purpose of verification
            
        Returns:
            Dictionary with status information or None if not found
        """
        with get_db() as db:
            sms_verification = db.query(SmsVerification).filter(
                and_(
                    SmsVerification.phone_number == phone_number,
                    SmsVerification.purpose == purpose
                )
            ).order_by(SmsVerification.created_at.desc()).first()
            
            if not sms_verification:
                return None
            
            return {
                'verification_id': sms_verification.id,
                'phone_number': sms_verification.phone_number,
                'purpose': sms_verification.purpose,
                'is_verified': sms_verification.is_verified,
                'is_expired': sms_verification.is_expired,
                'attempts': sms_verification.attempts,
                'attempts_remaining': sms_verification.attempts_remaining,
                'expires_at': sms_verification.expires_at.isoformat(),
                'created_at': sms_verification.created_at.isoformat(),
                'verified_at': sms_verification.verified_at.isoformat() if sms_verification.verified_at else None
            }
    
    def cleanup_expired_codes(self) -> int:
        """
        Clean up expired verification codes.
        
        Returns:
            Number of codes cleaned up
        """
        with get_db() as db:
            expired_count = db.query(SmsVerification).filter(
                SmsVerification.expires_at < datetime.utcnow()
            ).count()
            
            if expired_count > 0:
                db.query(SmsVerification).filter(
                    SmsVerification.expires_at < datetime.utcnow()
                ).delete()
                db.commit()
                
                logger.info(f"Cleaned up {expired_count} expired SMS verification codes")
            
            return expired_count
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get SMS service health status.
        
        Returns:
            Dictionary with health status information
        """
        try:
            is_healthy = await self.adapter.check_health()
            
            return {
                'status': 'healthy' if is_healthy else 'down',
                'provider': self.adapter.get_provider_name(),
                'last_check': self.adapter.get_last_health_check().isoformat() if self.adapter.get_last_health_check() else None,
                'config_valid': len(self.config.validate()) == 0
            }
        except Exception as e:
            logger.error(f"SMS health check failed: {e}")
            return {
                'status': 'down',
                'provider': self.adapter.get_provider_name() if hasattr(self, 'adapter') else 'unknown',
                'last_check': None,
                'error': str(e),
                'config_valid': len(self.config.validate()) == 0
            }
    
    def _generate_code(self) -> str:
        """Generate random verification code."""
        length = self.config.code_length
        digits = string.digits
        return ''.join(secrets.choice(digits) for _ in range(length))
    
    def _hash_code(self, code: str) -> str:
        """Hash verification code for secure storage."""
        # Use SHA-256 with salt (phone number as simple salt)
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    def _store_verification(
        self,
        db: Session,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose
    ) -> SmsVerification:
        """Store verification record in database."""
        # Hash the verification code
        code_hash = self._hash_code(verification_code)
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(minutes=self.config.code_expiry_minutes)
        
        # Create verification record
        sms_verification = SmsVerification(
            phone_number=phone_number,
            verification_code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=self.config.code_max_attempts
        )
        
        db.add(sms_verification)
        db.commit()
        db.refresh(sms_verification)
        
        return sms_verification
    
    def _check_rate_limits(
        self,
        db: Session,
        phone_number: str,
        ip_address: Optional[str]
    ) -> None:
        """
        Check SMS rate limits for phone number and IP address.
        
        Args:
            db: Database session
            phone_number: Phone number to check
            ip_address: IP address to check
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        now = datetime.utcnow()
        
        # Check phone number rate limits
        phone_limits = [
            (timedelta(minutes=1), self.config.phone_rate_per_minute, "minute"),
            (timedelta(hours=1), self.config.phone_rate_per_hour, "hour"),
            (timedelta(days=1), self.config.phone_rate_per_day, "day")
        ]
        
        for time_window, limit, period_name in phone_limits:
            since = now - time_window
            count = db.query(SmsVerification).filter(
                and_(
                    SmsVerification.phone_number == phone_number,
                    SmsVerification.created_at >= since
                )
            ).count()
            
            if count >= limit:
                raise RateLimitExceededError(
                    f"Phone number rate limit exceeded: {count}/{limit} per {period_name}"
                )
        
        # Check IP address rate limits if provided
        if ip_address:
            # Note: We'd need to store IP addresses in the verification table
            # For now, we'll implement a simple in-memory rate limiter
            # In production, consider using Redis or similar
            pass


# Global SMS service instance
sms_service = SMSService()