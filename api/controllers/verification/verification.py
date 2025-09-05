"""Real name verification controller with secure document handling."""

import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from services.verification_service import verification_service
from models.compliance import IDType
from utils.security import get_client_ip, get_user_agent
from decorators.rate_limit import rate_limit

verification_bp = Blueprint('verification', __name__, url_prefix='/api/verification')

# Configuration
ALLOWED_DOCUMENT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS


@verification_bp.route('/status', methods=['GET'])
@login_required
def get_verification_status():
    """Get current user's verification status."""
    try:
        status_data = verification_service.get_user_verification_status(current_user.id)
        return jsonify({
            'success': True,
            'data': status_data
        })
    except Exception as e:
        current_app.logger.error(f"Get verification status error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve verification status'
        }), 500


@verification_bp.route('/submit', methods=['POST'])
@login_required
@rate_limit("verification_submit", per_minute=2)
def submit_verification():
    """Submit real name verification request."""
    try:
        # Get form data
        real_name = request.form.get('real_name')
        id_type = request.form.get('id_type')
        id_number = request.form.get('id_number')
        
        # Validate required fields
        if not all([real_name, id_type, id_number]):
            return jsonify({
                'success': False,
                'error': 'Real name, ID type, and ID number are required'
            }), 400

        # Validate ID type
        if id_type not in [t.value for t in IDType]:
            return jsonify({
                'success': False,
                'error': 'Invalid ID type'
            }), 400

        # Validate real name length
        real_name = real_name.strip()
        if len(real_name) < 2 or len(real_name) > 50:
            return jsonify({
                'success': False,
                'error': 'Real name must be between 2 and 50 characters'
            }), 400

        # Validate ID number (basic format check)
        id_number = id_number.strip()
        if len(id_number) < 8 or len(id_number) > 20:
            return jsonify({
                'success': False,
                'error': 'ID number must be between 8 and 20 characters'
            }), 400

        # Get uploaded documents
        front_document = request.files.get('front_document')
        back_document = request.files.get('back_document')
        
        # Validate front document (required)
        if not front_document or front_document.filename == '':
            return jsonify({
                'success': False,
                'error': 'Front document image is required'
            }), 400

        if not allowed_file(front_document.filename):
            return jsonify({
                'success': False,
                'error': f'Front document must be one of: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
            }), 400

        # Check front document size
        front_document.seek(0, os.SEEK_END)
        front_size = front_document.tell()
        front_document.seek(0)
        
        if front_size > MAX_DOCUMENT_SIZE:
            return jsonify({
                'success': False,
                'error': f'Front document size must be less than {MAX_DOCUMENT_SIZE // (1024*1024)}MB'
            }), 400

        # Validate back document if provided
        back_document_validated = None
        if back_document and back_document.filename != '':
            if not allowed_file(back_document.filename):
                return jsonify({
                    'success': False,
                    'error': f'Back document must be one of: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
                }), 400

            back_document.seek(0, os.SEEK_END)
            back_size = back_document.tell()
            back_document.seek(0)
            
            if back_size > MAX_DOCUMENT_SIZE:
                return jsonify({
                    'success': False,
                    'error': f'Back document size must be less than {MAX_DOCUMENT_SIZE // (1024*1024)}MB'
                }), 400
                
            back_document_validated = back_document

        # Prepare verification data
        verification_data = {
            'real_name': real_name,
            'id_type': id_type,
            'id_number': id_number
        }

        # Submit verification
        result = verification_service.submit_verification(
            user_id=current_user.id,
            verification_data=verification_data,
            front_document_file=front_document,
            back_document_file=back_document_validated
        )

        return jsonify({
            'success': True,
            'data': result,
            'message': 'Verification submitted successfully'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Submit verification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to submit verification'
        }), 500


@verification_bp.route('/details/<verification_id>', methods=['GET'])
@login_required
def get_verification_details(verification_id):
    """Get detailed verification information."""
    try:
        details = verification_service.get_verification_details(
            user_id=current_user.id,
            verification_id=verification_id
        )
        return jsonify({
            'success': True,
            'data': details
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Get verification details error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve verification details'
        }), 500


@verification_bp.route('/id-types', methods=['GET'])
@login_required
def get_id_types():
    """Get available ID types for verification."""
    try:
        id_types = [
            {
                'value': id_type.value,
                'label': _get_id_type_label(id_type.value)
            }
            for id_type in IDType
        ]
        
        return jsonify({
            'success': True,
            'data': id_types
        })
    except Exception as e:
        current_app.logger.error(f"Get ID types error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve ID types'
        }), 500


def _get_id_type_label(id_type: str) -> str:
    """Get user-friendly label for ID type."""
    labels = {
        IDType.NATIONAL_ID: "National ID Card",
        IDType.PASSPORT: "Passport",
        IDType.DRIVERS_LICENSE: "Driver's License",
        IDType.OTHER: "Other Government ID"
    }
    return labels.get(id_type, id_type.replace('_', ' ').title())


# Admin/Moderator endpoints
@verification_bp.route('/admin/pending', methods=['GET'])
@login_required
def get_pending_verifications():
    """Get pending verifications for admin review (admin only)."""
    # TODO: Add admin role check
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        pending_verifications = verification_service.get_pending_verifications(page, per_page)
        
        return jsonify({
            'success': True,
            'data': pending_verifications,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(pending_verifications)
            }
        })
    except Exception as e:
        current_app.logger.error(f"Get pending verifications error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve pending verifications'
        }), 500


@verification_bp.route('/admin/update-status', methods=['POST'])
@login_required
def update_verification_status():
    """Update verification status (admin only)."""
    # TODO: Add admin role check
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data is required'
            }), 400

        verification_id = data.get('verification_id')
        new_status = data.get('status')
        rejection_reason = data.get('rejection_reason')

        if not all([verification_id, new_status]):
            return jsonify({
                'success': False,
                'error': 'Verification ID and status are required'
            }), 400

        result = verification_service.update_verification_status(
            verification_id=verification_id,
            new_status=new_status,
            moderator_id=current_user.id,
            rejection_reason=rejection_reason
        )

        return jsonify({
            'success': True,
            'data': result,
            'message': f'Verification status updated to {new_status}'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Update verification status error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update verification status'
        }), 500


# Error handlers
@verification_bp.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size: {MAX_DOCUMENT_SIZE // (1024*1024)}MB'
    }), 413


@verification_bp.errorhandler(415)
def unsupported_media_type(e):
    """Handle unsupported file type error."""
    return jsonify({
        'success': False,
        'error': f'Unsupported file type. Allowed: {", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
    }), 415