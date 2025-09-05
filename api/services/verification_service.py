"""Real name verification service with secure document handling and encryption."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from PIL import Image
from cryptography.fernet import Fernet
import io

from models.account import Account
from models.compliance import RealNameVerification, VerificationStatus, IDType
from models.engine import db
from utils.file_storage import FileStorage
from utils.cache import cache_manager
from utils.security import sanitize_filename

class VerificationService:
    """Service for real name verification operations."""

    def __init__(self):
        self.file_storage = FileStorage()
        self.cache = cache_manager
        # Initialize encryption key for sensitive data
        self.encryption_key = os.environ.get('VERIFICATION_ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher_suite = Fernet(self.encryption_key)

    def submit_verification(self, user_id: str, verification_data: Dict[str, Any], 
                           front_document_file=None, back_document_file=None) -> Dict[str, Any]:
        """Submit real name verification request."""
        
        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Check if user already has a pending verification
        existing_verification = RealNameVerification.query.filter_by(
            user_id=user_id, 
            status=VerificationStatus.PENDING
        ).first()
        
        if existing_verification:
            raise ValueError("You already have a pending verification request")

        # Validate required fields
        required_fields = ['real_name', 'id_type', 'id_number']
        for field in required_fields:
            if field not in verification_data or not verification_data[field]:
                raise ValueError(f"Missing required field: {field}")

        # Encrypt sensitive ID number
        id_number = verification_data['id_number']
        encrypted_id_number = self.cipher_suite.encrypt(id_number.encode()).decode()

        # Process document uploads
        document_front_url = None
        document_back_url = None
        
        if front_document_file:
            document_front_url = self._process_document_upload(
                user_id, front_document_file, "front"
            )
        
        if back_document_file:
            document_back_url = self._process_document_upload(
                user_id, back_document_file, "back"
            )

        # Create verification record
        verification = RealNameVerification(
            user_id=user_id,
            real_name=verification_data['real_name'],
            id_type=verification_data['id_type'],
            id_number_encrypted=encrypted_id_number,
            document_front_url=document_front_url,
            document_back_url=document_back_url,
            status=VerificationStatus.PENDING
        )

        db.session.add(verification)
        db.session.commit()

        # Log security event
        self._log_security_event(user_id, "Real name verification submitted")

        return {
            'verification_id': verification.id,
            'status': verification.status,
            'message': 'Verification submitted successfully. Review process may take 1-3 business days.'
        }

    def get_user_verification_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's current verification status."""
        
        # Try cache first
        cache_key = f"verification_status:{user_id}"
        cached_status = self.cache.get(cache_key)
        if cached_status:
            return cached_status

        user = Account.query.get(user_id)
        if not user:
            raise ValueError("User not found")

        # Get latest verification record
        verification = RealNameVerification.query.filter_by(
            user_id=user_id
        ).order_by(RealNameVerification.created_at.desc()).first()

        if not verification:
            status_data = {
                'is_verified': False,
                'status': 'not_submitted',
                'can_submit': True,
                'message': 'Real name verification not submitted'
            }
        else:
            status_data = {
                'is_verified': verification.is_approved,
                'status': verification.status,
                'can_submit': verification.status in [VerificationStatus.REJECTED, VerificationStatus.EXPIRED],
                'verification_id': verification.id,
                'submitted_at': verification.created_at.isoformat(),
                'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
                'rejection_reason': verification.rejection_reason,
                'message': self._get_status_message(verification.status)
            }

        # Cache for 10 minutes
        self.cache.set(cache_key, status_data, timeout=600)
        return status_data

    def get_verification_details(self, user_id: str, verification_id: str) -> Dict[str, Any]:
        """Get detailed verification information for user."""
        
        verification = RealNameVerification.query.filter_by(
            id=verification_id, 
            user_id=user_id
        ).first()
        
        if not verification:
            raise ValueError("Verification record not found")

        return {
            'id': verification.id,
            'real_name': verification.real_name,
            'id_type': verification.id_type,
            'status': verification.status,
            'has_front_document': bool(verification.document_front_url),
            'has_back_document': bool(verification.document_back_url),
            'submitted_at': verification.created_at.isoformat(),
            'verified_at': verification.verified_at.isoformat() if verification.verified_at else None,
            'rejection_reason': verification.rejection_reason,
            'verification_time_days': verification.verification_time_days
        }

    def update_verification_status(self, verification_id: str, new_status: str, 
                                 moderator_id: str, rejection_reason: str = None) -> Dict[str, Any]:
        """Update verification status (admin/moderator only)."""
        
        verification = RealNameVerification.query.get(verification_id)
        if not verification:
            raise ValueError("Verification record not found")

        if new_status not in [status.value for status in VerificationStatus]:
            raise ValueError("Invalid verification status")

        # Update verification record
        verification.status = new_status
        verification.verified_by = moderator_id
        
        if new_status == VerificationStatus.APPROVED:
            verification.verified_at = datetime.utcnow()
            verification.rejection_reason = None
            
            # Update user's real name verification status
            user = verification.user
            user.real_name = verification.real_name
            user.real_name_verified = True
            user.real_name_verified_at = datetime.utcnow()
            
        elif new_status == VerificationStatus.REJECTED:
            verification.rejection_reason = rejection_reason or "Verification failed"
            
        verification.updated_at = datetime.utcnow()
        db.session.commit()

        # Clear cache
        self.cache.delete(f"verification_status:{verification.user_id}")

        # Log security event
        self._log_security_event(
            verification.user_id, 
            f"Real name verification {new_status} by moderator {moderator_id}"
        )

        return self.get_verification_details(verification.user_id, verification_id)

    def get_pending_verifications(self, page: int = 1, per_page: int = 20) -> List[Dict[str, Any]]:
        """Get pending verifications for admin review."""
        
        query = RealNameVerification.query.filter_by(
            status=VerificationStatus.PENDING
        ).order_by(RealNameVerification.created_at.asc())

        # Paginate
        offset = (page - 1) * per_page
        verifications = query.offset(offset).limit(per_page).all()

        return [
            {
                'id': v.id,
                'user_id': v.user_id,
                'real_name': v.real_name,
                'id_type': v.id_type,
                'has_documents': bool(v.document_front_url and v.document_back_url),
                'submitted_at': v.created_at.isoformat(),
                'waiting_days': (datetime.utcnow() - v.created_at).days
            }
            for v in verifications
        ]

    def _process_document_upload(self, user_id: str, file, document_type: str) -> str:
        """Process and securely store verification document."""
        
        # Validate image file
        try:
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed for consistency
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
                
        except Exception as e:
            raise ValueError(f"Invalid image file: {e}")

        # Generate secure filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        random_suffix = secrets.token_hex(8)
        filename = f"verification_{user_id}_{document_type}_{timestamp}_{random_suffix}.jpg"

        # Resize image for security and storage efficiency (max 1200px width)
        max_width = 1200
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Save to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='JPEG', quality=85, optimize=True)
        img_bytes.seek(0)

        # Store in secure folder with restricted access
        document_url = self.file_storage.save_file(
            file_data=img_bytes,
            filename=filename,
            folder='verification_documents',  # Separate secure folder
            user_id=user_id
        )

        return document_url

    def _get_status_message(self, status: str) -> str:
        """Get user-friendly status message."""
        
        status_messages = {
            VerificationStatus.PENDING: "Your verification is under review. This may take 1-3 business days.",
            VerificationStatus.APPROVED: "Your real name verification has been approved.",
            VerificationStatus.REJECTED: "Your verification was rejected. Please check the reason and resubmit with correct information.",
            VerificationStatus.EXPIRED: "Your verification has expired. Please submit a new request."
        }
        
        return status_messages.get(status, "Unknown verification status")

    def _log_security_event(self, user_id: str, event: str):
        """Log security-related events."""
        from flask import current_app
        current_app.logger.info(
            f"Verification Security Event - User {user_id}: {event}"
        )

    def cleanup_expired_verifications(self):
        """Cleanup expired pending verifications (90 days)."""
        
        expiry_date = datetime.utcnow() - timedelta(days=90)
        
        expired_verifications = RealNameVerification.query.filter(
            RealNameVerification.status == VerificationStatus.PENDING,
            RealNameVerification.created_at < expiry_date
        ).all()

        for verification in expired_verifications:
            verification.status = VerificationStatus.EXPIRED
            verification.updated_at = datetime.utcnow()
            
            # Clear cache
            self.cache.delete(f"verification_status:{verification.user_id}")

        if expired_verifications:
            db.session.commit()
            
        return len(expired_verifications)

# Initialize service instance
verification_service = VerificationService()