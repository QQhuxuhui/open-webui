"""
Real name verification service for identity verification processes.
"""
import logging
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet

from extensions.ext_database import db
from extensions.ext_storage import storage
from models.account import Account
from models.compliance import RealNameVerification, VerificationStatus, IDType
from models.profile_history import ProfileModificationHistory
from services.account_service import AccountService
from libs.datetime_utils import naive_utc_now
from configs import dify_config

logger = logging.getLogger(__name__)


class RealNameVerificationService:
    """Service for handling real name verification operations."""
    
    # Encryption key for sensitive data (should be from config in production)
    _encryption_key = dify_config.SECRET_KEY[:32].ljust(32, '0').encode('utf-8')
    
    @staticmethod
    def _get_fernet() -> Fernet:
        """Get Fernet encryption instance."""
        return Fernet(Fernet.generate_key())  # In production, use a stored key
    
    @staticmethod
    def _encrypt_sensitive_data(data: str) -> str:
        """Encrypt sensitive data like ID numbers."""
        try:
            fernet = RealNameVerificationService._get_fernet()
            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt sensitive data: {e}")
            raise ValueError("Failed to encrypt sensitive information")
    
    @staticmethod
    def _decrypt_sensitive_data(encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            fernet = RealNameVerificationService._get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt sensitive data: {e}")
            raise ValueError("Failed to decrypt sensitive information")
    
    @staticmethod
    def upload_verification_document(
        account: Account,
        document_file,
        document_type: str  # "front" or "back"
    ) -> str:
        """
        Upload and securely store verification documents.
        
        Args:
            account: User account
            document_file: Uploaded file
            document_type: Type of document (front/back)
            
        Returns:
            Secure document URL
        """
        try:
            # Validate file type
            if not document_file.content_type or not document_file.content_type.startswith('image/'):
                raise ValueError("Document must be an image file")
            
            # Validate file size (10MB limit for documents)
            document_file.seek(0, 2)
            file_size = document_file.tell()
            document_file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                raise ValueError("Document file too large. Maximum size is 10MB")
            
            # Generate secure filename
            file_extension = os.path.splitext(document_file.filename)[1] or '.jpg'
            document_filename = f"verification_docs/{account.id}/{uuid.uuid4().hex}_{document_type}{file_extension}"
            
            # Store document securely
            document_url = storage.save(document_filename, document_file)
            
            logger.info(f"Verification document uploaded for user {account.id}: {document_type}")
            return document_url
            
        except Exception as e:
            logger.error(f"Failed to upload verification document: {e}")
            raise
    
    @staticmethod
    def submit_verification(
        account: Account,
        real_name: str,
        id_type: str,
        id_number: str,
        document_front_file=None,
        document_back_file=None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> RealNameVerification:
        """
        Submit a new real name verification request.
        
        Args:
            account: User account
            real_name: Real name to verify
            id_type: Type of ID document
            id_number: ID number (will be encrypted)
            document_front_file: Front side of document
            document_back_file: Back side of document (optional)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created verification record
        """
        try:
            # Check if user already has a pending verification
            existing_verification = db.session.query(RealNameVerification)\
                .filter_by(user_id=account.id, status=VerificationStatus.PENDING)\
                .first()
            
            if existing_verification:
                raise ValueError("You already have a pending verification request")
            
            # Validate ID type
            if id_type not in [IDType.NATIONAL_ID, IDType.PASSPORT, IDType.DRIVERS_LICENSE, IDType.OTHER]:
                raise ValueError("Invalid ID type")
            
            # Encrypt ID number
            encrypted_id_number = RealNameVerificationService._encrypt_sensitive_data(id_number)
            
            # Upload documents if provided
            document_front_url = None
            document_back_url = None
            
            if document_front_file:
                document_front_url = RealNameVerificationService.upload_verification_document(
                    account, document_front_file, "front"
                )
            
            if document_back_file:
                document_back_url = RealNameVerificationService.upload_verification_document(
                    account, document_back_file, "back"
                )
            
            # Create verification record
            verification = RealNameVerification(
                user_id=account.id,
                real_name=real_name,
                id_type=id_type,
                id_number_encrypted=encrypted_id_number,
                document_front_url=document_front_url,
                document_back_url=document_back_url,
                status=VerificationStatus.PENDING,
                created_at=naive_utc_now(),
                updated_at=naive_utc_now()
            )
            
            db.session.add(verification)
            
            # Log the verification submission
            AccountService.log_profile_modification(
                account=account,
                field_name="real_name_verification",
                old_value=None,
                new_value="submitted",
                field_label="Real Name Verification",
                verification_required=True
            )
            
            db.session.commit()
            
            logger.info(f"Real name verification submitted for user {account.id}")
            return verification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to submit verification: {e}")
            raise
    
    @staticmethod
    def get_user_verification_status(account: Account) -> Optional[Dict[str, Any]]:
        """
        Get the current verification status for a user.
        
        Args:
            account: User account
            
        Returns:
            Verification status information
        """
        try:
            verification = db.session.query(RealNameVerification)\
                .filter_by(user_id=account.id)\
                .order_by(RealNameVerification.created_at.desc())\
                .first()
            
            if not verification:
                return None
            
            return {
                "id": verification.id,
                "status": verification.status,
                "real_name": verification.real_name,
                "id_type": verification.id_type,
                "rejection_reason": verification.rejection_reason,
                "verified_at": verification.verified_at,
                "created_at": verification.created_at,
                "updated_at": verification.updated_at,
                "is_approved": verification.is_approved,
                "is_pending": verification.is_pending,
                "has_documents": bool(verification.document_front_url)
            }
            
        except Exception as e:
            logger.error(f"Failed to get verification status: {e}")
            return None
    
    @staticmethod
    def resubmit_verification(
        account: Account,
        verification_id: str,
        real_name: Optional[str] = None,
        id_type: Optional[str] = None,
        id_number: Optional[str] = None,
        document_front_file=None,
        document_back_file=None
    ) -> RealNameVerification:
        """
        Resubmit a rejected verification with updated information.
        
        Args:
            account: User account
            verification_id: ID of the previous verification
            real_name: Updated real name (optional)
            id_type: Updated ID type (optional)
            id_number: Updated ID number (optional)
            document_front_file: Updated front document (optional)
            document_back_file: Updated back document (optional)
            
        Returns:
            Updated verification record
        """
        try:
            # Get the existing verification
            verification = db.session.query(RealNameVerification)\
                .filter_by(id=verification_id, user_id=account.id)\
                .first()
            
            if not verification:
                raise ValueError("Verification record not found")
            
            if verification.status not in [VerificationStatus.REJECTED, VerificationStatus.EXPIRED]:
                raise ValueError("Can only resubmit rejected or expired verifications")
            
            # Update fields if provided
            if real_name:
                verification.real_name = real_name
            
            if id_type:
                verification.id_type = id_type
            
            if id_number:
                verification.id_number_encrypted = RealNameVerificationService._encrypt_sensitive_data(id_number)
            
            # Upload new documents if provided
            if document_front_file:
                verification.document_front_url = RealNameVerificationService.upload_verification_document(
                    account, document_front_file, "front"
                )
            
            if document_back_file:
                verification.document_back_url = RealNameVerificationService.upload_verification_document(
                    account, document_back_file, "back"
                )
            
            # Reset status to pending
            verification.status = VerificationStatus.PENDING
            verification.rejection_reason = None
            verification.verified_at = None
            verification.verified_by = None
            verification.updated_at = naive_utc_now()
            
            # Log the resubmission
            AccountService.log_profile_modification(
                account=account,
                field_name="real_name_verification",
                old_value=f"{verification.status}",
                new_value="resubmitted",
                field_label="Real Name Verification",
                verification_required=True
            )
            
            db.session.commit()
            
            logger.info(f"Verification resubmitted for user {account.id}")
            return verification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to resubmit verification: {e}")
            raise
    
    @staticmethod
    def approve_verification(
        verification_id: str,
        verifier: Account,
        notes: Optional[str] = None
    ) -> RealNameVerification:
        """
        Approve a verification request (admin function).
        
        Args:
            verification_id: ID of verification to approve
            verifier: Admin user performing the approval
            notes: Optional approval notes
            
        Returns:
            Updated verification record
        """
        try:
            verification = db.session.query(RealNameVerification)\
                .filter_by(id=verification_id)\
                .first()
            
            if not verification:
                raise ValueError("Verification record not found")
            
            if verification.status != VerificationStatus.PENDING:
                raise ValueError("Can only approve pending verifications")
            
            # Update verification status
            verification.status = VerificationStatus.APPROVED
            verification.verified_at = naive_utc_now()
            verification.verified_by = verifier.id
            verification.updated_at = naive_utc_now()
            
            # Update user account
            user = db.session.query(Account).filter_by(id=verification.user_id).first()
            if user:
                user.real_name = verification.real_name
                user.real_name_verified = True
                user.real_name_verified_at = verification.verified_at
                user.updated_at = naive_utc_now()
            
            db.session.commit()
            
            logger.info(f"Verification approved: {verification_id} by {verifier.id}")
            return verification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to approve verification: {e}")
            raise
    
    @staticmethod
    def reject_verification(
        verification_id: str,
        verifier: Account,
        rejection_reason: str
    ) -> RealNameVerification:
        """
        Reject a verification request (admin function).
        
        Args:
            verification_id: ID of verification to reject
            verifier: Admin user performing the rejection
            rejection_reason: Reason for rejection
            
        Returns:
            Updated verification record
        """
        try:
            verification = db.session.query(RealNameVerification)\
                .filter_by(id=verification_id)\
                .first()
            
            if not verification:
                raise ValueError("Verification record not found")
            
            if verification.status != VerificationStatus.PENDING:
                raise ValueError("Can only reject pending verifications")
            
            # Update verification status
            verification.status = VerificationStatus.REJECTED
            verification.rejection_reason = rejection_reason
            verification.verified_at = naive_utc_now()
            verification.verified_by = verifier.id
            verification.updated_at = naive_utc_now()
            
            db.session.commit()
            
            logger.info(f"Verification rejected: {verification_id} by {verifier.id}")
            return verification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reject verification: {e}")
            raise
    
    @staticmethod
    def get_pending_verifications(page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Get pending verifications for admin review.
        
        Args:
            page: Page number
            limit: Items per page
            
        Returns:
            Paginated verification records
        """
        try:
            offset = (page - 1) * limit
            
            query = db.session.query(RealNameVerification)\
                .filter_by(status=VerificationStatus.PENDING)\
                .order_by(RealNameVerification.created_at)
            
            total = query.count()
            verifications = query.offset(offset).limit(limit).all()
            
            # Convert to dict format
            data = []
            for verification in verifications:
                user = db.session.query(Account).filter_by(id=verification.user_id).first()
                data.append({
                    "id": verification.id,
                    "user_id": verification.user_id,
                    "user_name": user.name if user else "Unknown",
                    "user_email": user.email if user else "Unknown",
                    "real_name": verification.real_name,
                    "id_type": verification.id_type,
                    "has_front_document": bool(verification.document_front_url),
                    "has_back_document": bool(verification.document_back_url),
                    "created_at": verification.created_at,
                    "updated_at": verification.updated_at
                })
            
            has_next = offset + limit < total
            
            return {
                "data": data,
                "has_next": has_next,
                "page": page,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Failed to get pending verifications: {e}")
            raise
    
    @staticmethod
    def get_verification_statistics() -> Dict[str, Any]:
        """
        Get verification statistics for admin dashboard.
        
        Returns:
            Verification statistics
        """
        try:
            total_verifications = db.session.query(RealNameVerification).count()
            pending_verifications = db.session.query(RealNameVerification)\
                .filter_by(status=VerificationStatus.PENDING).count()
            approved_verifications = db.session.query(RealNameVerification)\
                .filter_by(status=VerificationStatus.APPROVED).count()
            rejected_verifications = db.session.query(RealNameVerification)\
                .filter_by(status=VerificationStatus.REJECTED).count()
            
            verified_users = db.session.query(Account)\
                .filter_by(real_name_verified=True).count()
            
            return {
                "total_verifications": total_verifications,
                "pending_verifications": pending_verifications,
                "approved_verifications": approved_verifications,
                "rejected_verifications": rejected_verifications,
                "verified_users": verified_users,
                "approval_rate": (approved_verifications / total_verifications * 100) if total_verifications > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get verification statistics: {e}")
            return {
                "total_verifications": 0,
                "pending_verifications": 0,
                "approved_verifications": 0,
                "rejected_verifications": 0,
                "verified_users": 0,
                "approval_rate": 0
            }