"""Phone-based authentication service."""

import logging
import base64
from typing import Optional, Dict, Any
from datetime import datetime

from models.account import Account, AccountStatus
from extensions.ext_database import db
from libs.password import hash_password, generate_password_salt

logger = logging.getLogger(__name__)


class PhoneAuthService:
    """Service for phone-based authentication operations."""
    
    def create_phone_user(
        self,
        phone_number: str,
        password: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None
    ) -> Account:
        """
        Create a new user account with phone number.
        
        Args:
            phone_number: Verified phone number
            password: Optional password for the account
            user_info: Optional user information dictionary
            client_ip: Client IP address for audit trail
            
        Returns:
            Created Account instance
            
        Raises:
            ValueError: If phone number is already registered
            Exception: If account creation fails
        """
        try:
            # Check if phone number is already registered
            existing_account = db.session.query(Account).filter_by(phone_number=phone_number).first()
            if existing_account:
                raise ValueError(f"Phone number {phone_number} is already registered")
            
            # Prepare user info
            user_info = user_info or {}
            
            # Generate default values
            nickname = user_info.get('nickname') or self._generate_default_nickname(phone_number)
            preferred_language = user_info.get('preferred_language', 'zh-CN')
            
            # Generate name from nickname or phone
            name = nickname or f"用户{phone_number[-4:]}"
            
            # Create email placeholder (required by Account model)
            email = f"phone_{phone_number.replace('+', '').replace(' ', '')}_temp@temp.local"
            
            # Handle password
            password_hash = None
            password_salt = None
            if password:
                password_salt = generate_password_salt()
                password_hash = hash_password(password, base64.b64decode(password_salt)).decode('utf-8')
            
            # Create account
            account = Account(
                name=name,
                email=email,
                password=password_hash,
                password_salt=password_salt,
                phone_number=phone_number,
                phone_verified=True,  # Phone is verified through SMS
                nickname=nickname,
                interface_language=preferred_language,
                interface_theme=user_info.get('interface_theme'),
                timezone=user_info.get('timezone', 'Asia/Shanghai'),
                status=AccountStatus.ACTIVE,
                initialized_at=datetime.utcnow(),
                last_login_at=datetime.utcnow(),
                last_login_ip=client_ip,
                last_active_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add to database session
            db.session.add(account)
            db.session.flush()  # Get the account ID
            
            # Update email with account ID to make it unique
            account.email = f"phone_user_{account.id}@temp.local"
            
            # Commit the transaction
            db.session.commit()
            
            logger.info(f"Created phone user account: {account.id} for phone: {phone_number[:8]}****")
            return account
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create phone user account: {e}", exc_info=True)
            raise
    
    def authenticate_phone_user(
        self,
        phone_number: str,
        client_ip: Optional[str] = None
    ) -> Optional[Account]:
        """
        Authenticate user by verified phone number.
        
        Args:
            phone_number: Verified phone number
            client_ip: Client IP address for audit trail
            
        Returns:
            Account instance if found and active, None otherwise
        """
        try:
            account = db.session.query(Account).filter_by(
                phone_number=phone_number,
                phone_verified=True
            ).first()
            
            if not account:
                logger.warning(f"Phone authentication failed - account not found: {phone_number[:8]}****")
                return None
            
            if account.status != AccountStatus.ACTIVE:
                logger.warning(f"Phone authentication failed - account not active: {account.id}")
                return None
            
            # Update last activity
            account.last_login_at = datetime.utcnow()
            account.last_login_ip = client_ip
            account.last_active_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Phone authentication successful: {account.id}")
            return account
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to authenticate phone user: {e}", exc_info=True)
            return None
    
    def update_phone_user_profile(
        self,
        account_id: str,
        user_info: Dict[str, Any]
    ) -> bool:
        """
        Update user profile information.
        
        Args:
            account_id: Account ID
            user_info: Dictionary of user information to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            account = db.session.query(Account).filter_by(id=account_id).first()
            if not account:
                logger.warning(f"Account not found for profile update: {account_id}")
                return False
            
            # Update allowed fields
            updateable_fields = {
                'nickname': 'nickname',
                'preferred_language': 'interface_language',
                'interface_theme': 'interface_theme',
                'timezone': 'timezone',
                'avatar_url': 'avatar'
            }
            
            updated_fields = []
            for user_field, account_field in updateable_fields.items():
                if user_field in user_info:
                    setattr(account, account_field, user_info[user_field])
                    updated_fields.append(user_field)
            
            if updated_fields:
                account.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated profile for account {account_id}: {updated_fields}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update phone user profile: {e}", exc_info=True)
            return False
    
    @staticmethod
    def change_phone_number(
        account: Account,
        old_phone: Optional[str],
        new_phone: str,
        old_phone_code: Optional[str],
        new_phone_code: str,
        client_ip: Optional[str] = None
    ) -> bool:
        """
        Change user's phone number after verification.
        
        Args:
            account: Account instance
            old_phone: Current phone number (optional if not set)
            new_phone: New verified phone number
            old_phone_code: Verification code for old phone (optional if no old phone)
            new_phone_code: Verification code for new phone
            client_ip: Client IP address for audit trail
            
        Returns:
            True if change successful, False otherwise
        """
        try:
            from services.sms.sms_service import SmsService
            from services.account_service import AccountService
            
            # Verify old phone code if old phone exists
            if old_phone and old_phone_code:
                if not SmsService.verify_code(old_phone, old_phone_code, 'phone_change_old'):
                    logger.warning(f"Old phone verification failed for account {account.id}")
                    raise ValueError("Old phone verification failed")
            
            # Verify new phone code
            if not SmsService.verify_code(new_phone, new_phone_code, 'phone_change_new'):
                logger.warning(f"New phone verification failed for account {account.id}")
                raise ValueError("New phone verification failed")
            
            # Check if new phone number is already registered
            existing_account = db.session.query(Account).filter_by(phone_number=new_phone).first()
            if existing_account and existing_account.id != account.id:
                logger.warning(f"New phone number already registered: {new_phone[:8]}****")
                raise ValueError("New phone number is already registered")
            
            # Update phone number using AccountService to log the change
            old_phone_display = old_phone[:8] + "****" if old_phone else "Not set"
            new_phone_display = new_phone[:8] + "****"
            
            AccountService.update_account(account, phone_number=new_phone, phone_verified=True)
            
            logger.info(f"Phone number changed for account {account.id}: {old_phone_display} -> {new_phone_display}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to change phone number: {e}", exc_info=True)
            raise
    
    def _generate_default_nickname(self, phone_number: str) -> str:
        """
        Generate a default nickname from phone number.
        
        Args:
            phone_number: Phone number
            
        Returns:
            Generated nickname
        """
        # Extract last 4 digits
        digits = ''.join(filter(str.isdigit, phone_number))
        if len(digits) >= 4:
            suffix = digits[-4:]
        else:
            suffix = digits
        
        return f"用户{suffix}"
    
    def get_phone_user_stats(self) -> Dict[str, Any]:
        """
        Get statistics about phone-registered users.
        
        Returns:
            Dictionary with user statistics
        """
        try:
            total_phone_users = db.session.query(Account).filter(
                Account.phone_number.isnot(None),
                Account.phone_verified == True
            ).count()
            
            active_phone_users = db.session.query(Account).filter(
                Account.phone_number.isnot(None),
                Account.phone_verified == True,
                Account.status == AccountStatus.ACTIVE
            ).count()
            
            recent_registrations = db.session.query(Account).filter(
                Account.phone_number.isnot(None),
                Account.phone_verified == True,
                Account.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
            
            return {
                'total_phone_users': total_phone_users,
                'active_phone_users': active_phone_users,
                'recent_registrations_today': recent_registrations
            }
            
        except Exception as e:
            logger.error(f"Failed to get phone user stats: {e}", exc_info=True)
            return {
                'total_phone_users': 0,
                'active_phone_users': 0,
                'recent_registrations_today': 0
            }