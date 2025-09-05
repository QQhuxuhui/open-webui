"""Profile management controller with comprehensive security audit."""

import os
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import io

from services.profile_service import ProfileService
from services.sms.sms_service import SMSService
from models.account import Account
from models.compliance import SmsVerification, SMSPurpose
from utils.validation import validate_phone_number, validate_email
from utils.security import get_client_ip, get_user_agent
from decorators.rate_limit import rate_limit

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')
profile_service = ProfileService()
sms_service = SMSService()

# Configuration
ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_AVATAR_SIZE = 10 * 1024 * 1024  # 10MB
AVATAR_SIZES = [(200, 200), (100, 100), (50, 50)]  # Original, medium, small


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


@profile_bp.route('/', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile information."""
    try:
        profile_data = profile_service.get_user_profile(current_user.id)
        return jsonify({
            'success': True,
            'data': profile_data
        })
    except Exception as e:
        current_app.logger.error(f"Get profile error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve profile data'
        }), 500


@profile_bp.route('/', methods=['PUT'])
@login_required
@rate_limit("profile_update", per_minute=5)
def update_profile():
    """Update user profile information."""
    try:
        data = request.get_json()
        
        # Validate input data
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate fields
        if 'nickname' in data:
            nickname = data['nickname'].strip()
            if not nickname or len(nickname) < 2 or len(nickname) > 50:
                return jsonify({
                    'success': False,
                    'error': 'Nickname must be between 2 and 50 characters'
                }), 400

        if 'email' in data and data['email']:
            if not validate_email(data['email']):
                return jsonify({
                    'success': False,
                    'error': 'Invalid email format'
                }), 400

        if 'real_name' in data and data['real_name']:
            real_name = data['real_name'].strip()
            if len(real_name) > 100:
                return jsonify({
                    'success': False,
                    'error': 'Real name must be less than 100 characters'
                }), 400

        # Update profile
        updated_profile = profile_service.update_user_profile(
            user_id=current_user.id,
            updates=data,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return jsonify({
            'success': True,
            'data': updated_profile,
            'message': 'Profile updated successfully'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Update profile error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update profile'
        }), 500


@profile_bp.route('/avatar', methods=['POST'])
@login_required
@rate_limit("avatar_upload", per_minute=3)
def upload_avatar():
    """Upload and process user avatar."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Allowed file types: {", ".join(ALLOWED_AVATAR_EXTENSIONS)}'
            }), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > MAX_AVATAR_SIZE:
            return jsonify({
                'success': False,
                'error': f'File size must be less than {MAX_AVATAR_SIZE // (1024*1024)}MB'
            }), 400

        # Process and save avatar
        avatar_url = profile_service.process_and_save_avatar(
            user_id=current_user.id,
            file=file,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return jsonify({
            'success': True,
            'avatar_url': avatar_url,
            'message': 'Avatar updated successfully'
        })

    except Exception as e:
        current_app.logger.error(f"Avatar upload error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload avatar'
        }), 500


@profile_bp.route('/phone/change', methods=['POST'])
@login_required
@rate_limit("phone_change", per_minute=2)
def change_phone_number():
    """Change user's phone number with verification."""
    try:
        data = request.get_json()
        
        if not data or 'new_phone' not in data:
            return jsonify({
                'success': False,
                'error': 'New phone number is required'
            }), 400

        new_phone = data['new_phone'].strip()
        
        # Validate phone number format
        if not validate_phone_number(new_phone):
            return jsonify({
                'success': False,
                'error': 'Invalid phone number format'
            }), 400

        # Check if phone is already in use
        existing_user = Account.query.filter_by(phone_number=new_phone).first()
        if existing_user and existing_user.id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Phone number is already in use'
            }), 400

        # Verify both old and new phone numbers have been verified
        current_phone = current_user.phone_number
        
        if current_phone:
            # Check old phone verification
            old_verification = SmsVerification.query.filter_by(
                phone_number=current_phone,
                purpose=SMSPurpose.PHONE_CHANGE,
                verified_at__isnot=None
            ).order_by(SmsVerification.created_at.desc()).first()
            
            if not old_verification or old_verification.verified_at < datetime.utcnow() - timedelta(minutes=30):
                return jsonify({
                    'success': False,
                    'error': 'Current phone verification required or expired'
                }), 400

        # Check new phone verification
        new_verification = SmsVerification.query.filter_by(
            phone_number=new_phone,
            purpose=SMSPurpose.PHONE_CHANGE,
            verified_at__isnot=None
        ).order_by(SmsVerification.created_at.desc()).first()
        
        if not new_verification or new_verification.verified_at < datetime.utcnow() - timedelta(minutes=30):
            return jsonify({
                'success': False,
                'error': 'New phone verification required or expired'
            }), 400

        # Update phone number
        updated_profile = profile_service.change_phone_number(
            user_id=current_user.id,
            new_phone=new_phone,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return jsonify({
            'success': True,
            'data': updated_profile,
            'message': 'Phone number updated successfully'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Phone change error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to change phone number'
        }), 500


@profile_bp.route('/history', methods=['GET'])
@login_required
def get_change_history():
    """Get user's profile change history for security audit."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        change_type = request.args.get('type')
        
        changes = profile_service.get_change_history(
            user_id=current_user.id,
            change_type=change_type,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'data': changes
        })

    except Exception as e:
        current_app.logger.error(f"Get change history error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve change history'
        }), 500


@profile_bp.route('/security/verify-identity', methods=['POST'])
@login_required
@rate_limit("identity_verify", per_minute=3)
def verify_identity():
    """Verify user identity for sensitive operations."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Verification data required'
            }), 400

        verification_method = data.get('method', 'sms')
        
        if verification_method == 'sms':
            phone = data.get('phone') or current_user.phone_number
            code = data.get('code')
            
            if not phone or not code:
                return jsonify({
                    'success': False,
                    'error': 'Phone number and verification code required'
                }), 400

            # Verify SMS code
            is_valid = sms_service.verify_code(phone, code, SMSPurpose.PHONE_CHANGE)
            
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired verification code'
                }), 400

            # Generate verification token
            token = profile_service.generate_identity_token(current_user.id)
            
            return jsonify({
                'success': True,
                'verification_token': token,
                'expires_in': 1800,  # 30 minutes
                'message': 'Identity verified successfully'
            })

        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported verification method'
            }), 400

    except Exception as e:
        current_app.logger.error(f"Identity verification error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to verify identity'
        }), 500


@profile_bp.route('/statistics', methods=['GET'])
@login_required
def get_profile_statistics():
    """Get user's profile completion and activity statistics."""
    try:
        stats = profile_service.get_profile_statistics(current_user.id)
        
        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        current_app.logger.error(f"Get profile statistics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve profile statistics'
        }), 500


# Error handlers
@profile_bp.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum size: {MAX_AVATAR_SIZE // (1024*1024)}MB'
    }), 413


@profile_bp.errorhandler(415)
def unsupported_media_type(e):
    """Handle unsupported file type error."""
    return jsonify({
        'success': False,
        'error': f'Unsupported file type. Allowed: {", ".join(ALLOWED_AVATAR_EXTENSIONS)}'
    }), 415