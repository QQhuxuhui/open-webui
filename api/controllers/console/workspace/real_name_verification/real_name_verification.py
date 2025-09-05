"""
Real name verification API endpoints for identity verification processes.
"""
import logging
from flask import request
from flask_restful import Resource, marshal_with, fields, reqparse
from werkzeug.exceptions import InternalServerError

from controllers.console.workspace.error import AccountNotInitializedError
from libs.login import login_required, current_user
from libs.helper import extract_remote_ip, get_user_agent
from models.account import Account
from models.compliance import RealNameVerification, VerificationStatus, IDType
from services.real_name_verification_service import RealNameVerificationService
from services.account_service import AccountService
from extensions.ext_database import db

logger = logging.getLogger(__name__)

# API response field definitions
verification_fields = {
    'id': fields.String,
    'status': fields.String,
    'real_name': fields.String,
    'id_type': fields.String,
    'rejection_reason': fields.String,
    'verified_at': fields.DateTime,
    'created_at': fields.DateTime,
    'updated_at': fields.DateTime,
    'is_approved': fields.Boolean,
    'is_pending': fields.Boolean,
    'has_documents': fields.Boolean
}

verification_list_fields = {
    'data': fields.List(fields.Nested(verification_fields)),
    'total': fields.Integer,
    'page': fields.Integer,
    'has_next': fields.Boolean
}

verification_stats_fields = {
    'total_verifications': fields.Integer,
    'pending_verifications': fields.Integer,
    'approved_verifications': fields.Integer,
    'rejected_verifications': fields.Integer,
    'verified_users': fields.Integer,
    'approval_rate': fields.Float
}


class RealNameVerificationSubmitApi(Resource):
    """Submit real name verification request."""
    
    @login_required
    @marshal_with(verification_fields)
    def post(self):
        """Submit a new real name verification request."""
        try:
            account = current_user
            
            # Parse form data and files
            parser = reqparse.RequestParser()
            parser.add_argument('real_name', type=str, required=True, location='form')
            parser.add_argument('id_type', type=str, required=True, location='form')
            parser.add_argument('id_number', type=str, required=True, location='form')
            args = parser.parse_args()
            
            # Validate ID type
            if args['id_type'] not in [IDType.NATIONAL_ID, IDType.PASSPORT, IDType.DRIVERS_LICENSE, IDType.OTHER]:
                raise ValueError("Invalid ID type")
            
            # Get uploaded files
            document_front_file = request.files.get('document_front')
            document_back_file = request.files.get('document_back')
            
            if not document_front_file:
                raise ValueError("Front document is required")
            
            # Get client info
            ip_address = extract_remote_ip(request)
            user_agent = get_user_agent(request)
            
            # Submit verification
            verification = RealNameVerificationService.submit_verification(
                account=account,
                real_name=args['real_name'],
                id_type=args['id_type'],
                id_number=args['id_number'],
                document_front_file=document_front_file,
                document_back_file=document_back_file,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return {
                'id': verification.id,
                'status': verification.status,
                'real_name': verification.real_name,
                'id_type': verification.id_type,
                'rejection_reason': verification.rejection_reason,
                'verified_at': verification.verified_at,
                'created_at': verification.created_at,
                'updated_at': verification.updated_at,
                'is_approved': verification.is_approved,
                'is_pending': verification.is_pending,
                'has_documents': bool(verification.document_front_url)
            }
            
        except ValueError as e:
            logger.error(f"Validation error in verification submission: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to submit verification: {e}")
            raise InternalServerError("Failed to submit verification request")


class RealNameVerificationStatusApi(Resource):
    """Get current verification status for user."""
    
    @login_required
    def get(self):
        """Get the current verification status for the logged-in user."""
        try:
            account = current_user
            status = RealNameVerificationService.get_user_verification_status(account)
            
            if not status:
                return {
                    'status': None,
                    'message': 'No verification requests found'
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get verification status: {e}")
            raise InternalServerError("Failed to retrieve verification status")


class RealNameVerificationResubmitApi(Resource):
    """Resubmit rejected verification with updated information."""
    
    @login_required
    @marshal_with(verification_fields)
    def post(self, verification_id):
        """Resubmit a rejected verification with updated information."""
        try:
            account = current_user
            
            # Parse optional update data
            parser = reqparse.RequestParser()
            parser.add_argument('real_name', type=str, required=False, location='form')
            parser.add_argument('id_type', type=str, required=False, location='form')
            parser.add_argument('id_number', type=str, required=False, location='form')
            args = parser.parse_args()
            
            # Get uploaded files
            document_front_file = request.files.get('document_front')
            document_back_file = request.files.get('document_back')
            
            # Resubmit verification
            verification = RealNameVerificationService.resubmit_verification(
                account=account,
                verification_id=verification_id,
                real_name=args['real_name'],
                id_type=args['id_type'],
                id_number=args['id_number'],
                document_front_file=document_front_file,
                document_back_file=document_back_file
            )
            
            return {
                'id': verification.id,
                'status': verification.status,
                'real_name': verification.real_name,
                'id_type': verification.id_type,
                'rejection_reason': verification.rejection_reason,
                'verified_at': verification.verified_at,
                'created_at': verification.created_at,
                'updated_at': verification.updated_at,
                'is_approved': verification.is_approved,
                'is_pending': verification.is_pending,
                'has_documents': bool(verification.document_front_url)
            }
            
        except ValueError as e:
            logger.error(f"Validation error in verification resubmission: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to resubmit verification: {e}")
            raise InternalServerError("Failed to resubmit verification request")


class RealNameVerificationApproveApi(Resource):
    """Approve verification request (admin only)."""
    
    @login_required
    @marshal_with(verification_fields)
    def post(self, verification_id):
        """Approve a verification request."""
        try:
            verifier = current_user
            
            # Check if user has admin permissions
            if not verifier.is_admin():
                raise ValueError("Insufficient permissions to approve verifications")
            
            # Parse optional notes
            parser = reqparse.RequestParser()
            parser.add_argument('notes', type=str, required=False, location='json')
            args = parser.parse_args()
            
            verification = RealNameVerificationService.approve_verification(
                verification_id=verification_id,
                verifier=verifier,
                notes=args.get('notes')
            )
            
            return {
                'id': verification.id,
                'status': verification.status,
                'real_name': verification.real_name,
                'id_type': verification.id_type,
                'rejection_reason': verification.rejection_reason,
                'verified_at': verification.verified_at,
                'created_at': verification.created_at,
                'updated_at': verification.updated_at,
                'is_approved': verification.is_approved,
                'is_pending': verification.is_pending,
                'has_documents': bool(verification.document_front_url)
            }
            
        except ValueError as e:
            logger.error(f"Validation error in verification approval: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to approve verification: {e}")
            raise InternalServerError("Failed to approve verification")


class RealNameVerificationRejectApi(Resource):
    """Reject verification request (admin only)."""
    
    @login_required
    @marshal_with(verification_fields)
    def post(self, verification_id):
        """Reject a verification request."""
        try:
            verifier = current_user
            
            # Check if user has admin permissions
            if not verifier.is_admin():
                raise ValueError("Insufficient permissions to reject verifications")
            
            # Parse rejection reason
            parser = reqparse.RequestParser()
            parser.add_argument('rejection_reason', type=str, required=True, location='json')
            args = parser.parse_args()
            
            verification = RealNameVerificationService.reject_verification(
                verification_id=verification_id,
                verifier=verifier,
                rejection_reason=args['rejection_reason']
            )
            
            return {
                'id': verification.id,
                'status': verification.status,
                'real_name': verification.real_name,
                'id_type': verification.id_type,
                'rejection_reason': verification.rejection_reason,
                'verified_at': verification.verified_at,
                'created_at': verification.created_at,
                'updated_at': verification.updated_at,
                'is_approved': verification.is_approved,
                'is_pending': verification.is_pending,
                'has_documents': bool(verification.document_front_url)
            }
            
        except ValueError as e:
            logger.error(f"Validation error in verification rejection: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to reject verification: {e}")
            raise InternalServerError("Failed to reject verification")


class RealNameVerificationPendingApi(Resource):
    """Get pending verifications for admin review."""
    
    @login_required
    @marshal_with(verification_list_fields)
    def get(self):
        """Get pending verifications for admin review."""
        try:
            verifier = current_user
            
            # Check if user has admin permissions
            if not verifier.is_admin():
                raise ValueError("Insufficient permissions to view pending verifications")
            
            # Parse pagination parameters
            parser = reqparse.RequestParser()
            parser.add_argument('page', type=int, default=1, location='args')
            parser.add_argument('limit', type=int, default=20, location='args')
            args = parser.parse_args()
            
            result = RealNameVerificationService.get_pending_verifications(
                page=args['page'],
                limit=args['limit']
            )
            
            return result
            
        except ValueError as e:
            logger.error(f"Validation error in pending verifications: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to get pending verifications: {e}")
            raise InternalServerError("Failed to retrieve pending verifications")


class RealNameVerificationStatsApi(Resource):
    """Get verification statistics for admin dashboard."""
    
    @login_required
    @marshal_with(verification_stats_fields)
    def get(self):
        """Get verification statistics."""
        try:
            verifier = current_user
            
            # Check if user has admin permissions
            if not verifier.is_admin():
                raise ValueError("Insufficient permissions to view verification statistics")
            
            stats = RealNameVerificationService.get_verification_statistics()
            return stats
            
        except ValueError as e:
            logger.error(f"Validation error in verification stats: {e}")
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to get verification statistics: {e}")
            raise InternalServerError("Failed to retrieve verification statistics")