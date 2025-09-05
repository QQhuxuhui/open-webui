"""Profile management service with security audit and change tracking."""

import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PIL import Image
import io

from models.account import Account
from models.compliance import UserConsent, SmsVerification
from models.engine import db
from utils.file_storage import FileStorage
from utils.cache import cache_manager
from utils.security import sanitize_filename

class ProfileChangeLog(db.Model):
    """Profile change log for security audit."""
    __tablename__ = 'profile_change_logs'
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="profile_change_log_pkey"),
        db.Index("profile_change_logs_user_id_idx", "user_id"),
        db.Index("profile_change_logs_created_at_idx", "created_at"),
        db.Index("profile_change_logs_type_idx", "change_type"),
    )

    id: str = db.Column(db.String, server_default=db.text("uuid_generate_v4()"), nullable=False)
    user_id: str = db.Column(db.String, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    change_type: str = db.Column(db.String(50), nullable=False)  # nickname, phone_number, email, avatar, etc.
    old_value: str = db.Column(db.Text, nullable=True)
    new_value: str = db.Column(db.Text, nullable=True)
    ip_address: str = db.Column(db.String(45), nullable=True)
    user_agent: str = db.Column(db.Text, nullable=True)
    reason: str = db.Column(db.Text, nullable=True)
    created_at: datetime = db.Column(db.DateTime, server_default=db.text('now()'), nullable=False)

    # Relationships
    user = db.relationship("Account", backref="profile_changes")


class IdentityVerificationToken(db.Model):
    """Temporary tokens for identity verification."""
    __tablename__ = 'identity_verification_tokens'
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="identity_verification_token_pkey"),
        db.Index("identity_verification_tokens_user_id_idx", "user_id"),
        db.Index("identity_verification_tokens_expires_at_idx", "expires_at"),
    )

    id: str = db.Column(db.String, server_default=db.text("uuid_generate_v4()"), nullable=False)
    user_id: str = db.Column(db.String, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    token: str = db.Column(db.String(128), nullable=False, unique=True)
    purpose: str = db.Column(db.String(50), nullable=False)
    expires_at: datetime = db.Column(db.DateTime, nullable=False)
    created_at: datetime = db.Column(db.DateTime, server_default=db.text('now()'), nullable=False)
    used_at: datetime = db.Column(db.DateTime, nullable=True)


class ProfileService:
    """Service for profile management operations."""

    def __init__(self):
        self.file_storage = FileStorage()
        self.cache = cache_manager

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user profile information."""
        
        # Try cache first
        cache_key = f"profile:{user_id}"
        cached_profile = self.cache.get(cache_key)
        if cached_profile:
            return cached_profile

        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Get consent information
        consents = UserConsent.query.filter_by(user_id=user_id).all()
        consent_data = {}
        for consent in consents:
            consent_data[consent.consent_type] = {
                'version': consent.consent_version,
                'consented_at': consent.consented_at.isoformat(),
                'ip_address': consent.ip_address
            }

        profile_data = {
            # Basic information
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'nickname': user.nickname,
            'real_name': user.real_name,
            'avatar_url': user.avatar_url,
            'avatar': user.avatar,  # Legacy field
            
            # Phone information
            'phone_number': user.phone_number,
            'phone_verified': user.phone_verified,
            
            # Verification status
            'real_name_verified': user.real_name_verified,
            'real_name_verified_at': user.real_name_verified_at.isoformat() if user.real_name_verified_at else None,
            
            # Account settings
            'interface_language': user.interface_language,
            'interface_theme': user.interface_theme,
            'timezone': user.timezone,
            
            # Account status
            'status': user.status,
            'last_active_at': user.last_active_at.isoformat() if user.last_active_at else None,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat(),
            
            # Consent information
            'consents': consent_data,
            
            # Profile completion
            'profile_completion': self._calculate_profile_completion(user)
        }

        # Cache for 5 minutes
        self.cache.set(cache_key, profile_data, timeout=300)
        
        return profile_data

    def update_user_profile(self, user_id: str, updates: Dict[str, Any], 
                           ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Update user profile with change tracking."""
        
        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        changes_made = []
        
        # Track changes and update fields
        for field, new_value in updates.items():
            if hasattr(user, field):
                old_value = getattr(user, field)
                
                # Skip if value hasn't changed
                if old_value == new_value:
                    continue
                
                # Log the change
                change_log = ProfileChangeLog(
                    user_id=user_id,
                    change_type=field,
                    old_value=str(old_value) if old_value else None,
                    new_value=str(new_value) if new_value else None,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                db.session.add(change_log)
                
                # Update the field
                setattr(user, field, new_value)
                changes_made.append(field)

        if changes_made:
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Clear cache
            self.cache.delete(f"profile:{user_id}")
            
            # Log security event for sensitive changes
            sensitive_fields = ['phone_number', 'email', 'real_name']
            if any(field in sensitive_fields for field in changes_made):
                self._log_security_event(user_id, f"Profile updated: {', '.join(changes_made)}", ip_address)

        return self.get_user_profile(user_id)

    def process_and_save_avatar(self, user_id: str, file, ip_address: str = None, user_agent: str = None) -> str:
        """Process and save user avatar with multiple sizes."""
        
        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Read and validate image
        try:
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Convert RGBA to RGB if needed
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
        except Exception as e:
            raise ValueError(f"Invalid image file: {e}")

        # Generate unique filename
        file_extension = 'jpg'
        filename_base = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Create different sizes
        sizes = {
            'original': (400, 400),
            'medium': (200, 200),
            'small': (100, 100),
            'thumb': (50, 50)
        }
        
        avatar_urls = {}
        
        for size_name, (width, height) in sizes.items():
            # Resize image
            resized_image = image.resize((width, height), Image.Resampling.LANCZOS)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            resized_image.save(img_bytes, format='JPEG', quality=85, optimize=True)
            img_bytes.seek(0)
            
            # Generate filename
            filename = f"{filename_base}_{size_name}.{file_extension}"
            
            # Save to storage
            avatar_url = self.file_storage.save_file(
                file_data=img_bytes,
                filename=filename,
                folder='avatars',
                user_id=user_id
            )
            
            avatar_urls[size_name] = avatar_url

        # Update user record
        old_avatar = user.avatar_url
        user.avatar_url = avatar_urls['medium']  # Use medium size as default
        user.avatar = avatar_urls['medium']  # Legacy field
        user.updated_at = datetime.utcnow()
        
        # Log change
        change_log = ProfileChangeLog(
            user_id=user_id,
            change_type='avatar',
            old_value=old_avatar,
            new_value=user.avatar_url,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(change_log)
        db.session.commit()
        
        # Clear cache
        self.cache.delete(f"profile:{user_id}")
        
        # Clean up old avatar files
        if old_avatar:
            self._cleanup_old_avatar(old_avatar)
        
        return user.avatar_url

    def change_phone_number(self, user_id: str, new_phone: str, 
                           ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Change user's phone number with security audit."""
        
        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Check if phone is already in use
        existing_user = Account.query.filter(
            Account.phone_number == new_phone,
            Account.id != user_id
        ).first()
        
        if existing_user:
            raise ValueError("Phone number is already in use")

        old_phone = user.phone_number
        
        # Update phone number
        user.phone_number = new_phone
        user.phone_verified = True  # Since verification was required
        user.updated_at = datetime.utcnow()
        
        # Log change
        change_log = ProfileChangeLog(
            user_id=user_id,
            change_type='phone_number',
            old_value=old_phone,
            new_value=new_phone,
            ip_address=ip_address,
            user_agent=user_agent,
            reason='Phone number change with SMS verification'
        )
        db.session.add(change_log)
        db.session.commit()
        
        # Clear cache
        self.cache.delete(f"profile:{user_id}")
        
        # Log security event
        self._log_security_event(
            user_id, 
            f"Phone number changed from {old_phone} to {new_phone}", 
            ip_address
        )
        
        return self.get_user_profile(user_id)

    def get_change_history(self, user_id: str, change_type: str = None, 
                          page: int = 1, per_page: int = 20) -> List[Dict[str, Any]]:
        """Get user's profile change history."""
        
        query = ProfileChangeLog.query.filter_by(user_id=user_id)
        
        if change_type:
            query = query.filter_by(change_type=change_type)
        
        query = query.order_by(ProfileChangeLog.created_at.desc())
        
        # Paginate
        offset = (page - 1) * per_page
        changes = query.offset(offset).limit(per_page).all()
        
        return [
            {
                'id': change.id,
                'change_type': change.change_type,
                'old_value': change.old_value,
                'new_value': change.new_value,
                'ip_address': change.ip_address,
                'user_agent': change.user_agent,
                'reason': change.reason,
                'created_at': change.created_at.isoformat()
            }
            for change in changes
        ]

    def generate_identity_token(self, user_id: str, purpose: str = 'profile_change') -> str:
        """Generate temporary identity verification token."""
        
        # Clean up expired tokens
        IdentityVerificationToken.query.filter(
            IdentityVerificationToken.expires_at < datetime.utcnow()
        ).delete()
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Create token record
        verification_token = IdentityVerificationToken(
            user_id=user_id,
            token=hashlib.sha256(token.encode()).hexdigest(),
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        
        db.session.add(verification_token)
        db.session.commit()
        
        return token

    def verify_identity_token(self, user_id: str, token: str, purpose: str = 'profile_change') -> bool:
        """Verify identity token."""
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        verification_token = IdentityVerificationToken.query.filter_by(
            user_id=user_id,
            token=token_hash,
            purpose=purpose,
            used_at=None
        ).filter(
            IdentityVerificationToken.expires_at > datetime.utcnow()
        ).first()
        
        if verification_token:
            verification_token.used_at = datetime.utcnow()
            db.session.commit()
            return True
            
        return False

    def get_profile_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get profile completion and activity statistics."""
        
        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Calculate profile completion
        completion_score = self._calculate_profile_completion(user)
        
        # Get recent activity
        recent_changes = ProfileChangeLog.query.filter_by(user_id=user_id)\
            .filter(ProfileChangeLog.created_at >= datetime.utcnow() - timedelta(days=30))\
            .count()
        
        # Get consent status
        consents = UserConsent.query.filter_by(user_id=user_id).count()
        
        return {
            'profile_completion': completion_score,
            'recent_changes_30d': recent_changes,
            'total_consents': consents,
            'account_age_days': (datetime.utcnow() - user.created_at).days,
            'last_profile_update': user.updated_at.isoformat(),
            'verification_status': {
                'phone_verified': user.phone_verified,
                'real_name_verified': user.real_name_verified,
                'email_verified': bool(user.email)  # Assuming email presence indicates verification
            }
        }

    def _calculate_profile_completion(self, user: Account) -> int:
        """Calculate profile completion percentage."""
        
        fields = {
            'nickname': 15,        # Required field
            'email': 15,          # Contact method
            'phone_number': 20,   # Contact method + verification
            'real_name': 10,      # Personal info
            'avatar_url': 15,     # Profile picture
            'interface_language': 5,  # Preferences
            'timezone': 5,        # Preferences
            'phone_verified': 10, # Verification status
            'real_name_verified': 5  # Verification status
        }
        
        total_score = 0
        for field, score in fields.items():
            value = getattr(user, field, None)
            if field in ['phone_verified', 'real_name_verified']:
                if value:
                    total_score += score
            elif value:
                total_score += score
        
        return total_score

    def _log_security_event(self, user_id: str, event: str, ip_address: str = None):
        """Log security-related events."""
        # This would integrate with a security event logging system
        # For now, we'll use the application logger
        from flask import current_app
        current_app.logger.warning(
            f"Security Event - User {user_id}: {event} from IP {ip_address}"
        )

    def _cleanup_old_avatar(self, old_avatar_url: str):
        """Clean up old avatar files."""
        try:
            # Extract filename from URL and delete related files
            if old_avatar_url:
                self.file_storage.delete_file(old_avatar_url)
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(f"Failed to cleanup old avatar: {e}")

# Create tables if they don't exist
def create_profile_tables():
    """Create profile-related tables."""
    with db.engine.connect() as conn:
        db.metadata.create_all(bind=conn, tables=[
            ProfileChangeLog.__table__,
            IdentityVerificationToken.__table__
        ])