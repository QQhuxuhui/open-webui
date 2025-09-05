"""Phone-based authentication controllers."""

import logging
from typing import Optional, Dict, Any
from flask import Blueprint, request, jsonify, session
from pydantic import BaseModel, validator
import re
from datetime import datetime

from models.account import Account, AccountStatus
from models.compliance import SMSPurpose, ConsentType, UserConsent
from services.sms import sms_service
from services.auth.phone_auth_service import PhoneAuthService
from services.agreement_service import AgreementService
from services.account_service import account_service
from extensions.ext_database import db
from libs.password import hash_password, valid_password

logger = logging.getLogger(__name__)

bp = Blueprint('phone_auth', __name__, url_prefix='/api/auth/phone')


class PhoneRegistrationRequest(BaseModel):
    """Request model for phone registration."""
    phone_number: str
    verification_code: str
    password: Optional[str] = None
    agreements: Dict[str, Dict[str, Any]]
    user_info: Optional[Dict[str, Any]] = None
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove spaces and special characters
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Basic validation - should start with + and have 10-15 digits
        if not re.match(r'^\+\d{10,15}$', cleaned):
            # Try to add country code for Chinese numbers
            if re.match(r'^\d{11}$', cleaned) and cleaned.startswith('1'):
                cleaned = f'+86{cleaned}'
            elif re.match(r'^86\d{11}$', cleaned):
                cleaned = f'+{cleaned}'
            else:
                raise ValueError('Invalid phone number format. Expected format: +8613800138000')
        
        return cleaned
    
    @validator('verification_code')
    def validate_verification_code(cls, v):
        """Validate verification code format."""
        # Remove spaces
        cleaned = v.strip()
        
        # Should be 4-8 digits
        if not re.match(r'^\d{4,8}$', cleaned):
            raise ValueError('Verification code must be 4-8 digits')
        
        return cleaned
    
    @validator('agreements')
    def validate_agreements(cls, v):
        """Validate agreements structure."""
        if not isinstance(v, dict):
            raise ValueError('Agreements must be a dictionary')
        
        required_agreements = ['privacy_policy', 'terms_of_service']
        for agreement_type in required_agreements:
            if agreement_type not in v:
                raise ValueError(f'Missing required agreement: {agreement_type}')
            
            agreement = v[agreement_type]
            if not isinstance(agreement, dict) or not agreement.get('agreed', False):
                raise ValueError(f'Agreement {agreement_type} must be agreed to')
            
            if not agreement.get('version'):
                raise ValueError(f'Agreement {agreement_type} must include version')
        
        return v


class PhoneLoginRequest(BaseModel):
    """Request model for phone login."""
    phone_number: str
    verification_code: str
    remember_me: Optional[bool] = False
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        # Remove spaces and special characters
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Basic validation - should start with + and have 10-15 digits
        if not re.match(r'^\+\d{10,15}$', cleaned):
            # Try to add country code for Chinese numbers
            if re.match(r'^\d{11}$', cleaned) and cleaned.startswith('1'):
                cleaned = f'+86{cleaned}'
            elif re.match(r'^86\d{11}$', cleaned):
                cleaned = f'+{cleaned}'
            else:
                raise ValueError('Invalid phone number format. Expected format: +8613800138000')
        
        return cleaned
    
    @validator('verification_code')
    def validate_verification_code(cls, v):
        """Validate verification code format."""
        # Remove spaces
        cleaned = v.strip()
        
        # Should be 4-8 digits
        if not re.match(r'^\d{4,8}$', cleaned):
            raise ValueError('Verification code must be 4-8 digits')
        
        return cleaned


def get_client_ip() -> Optional[str]:
    """Get client IP address from request."""
    # Check for forwarded IP (behind proxy)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


@bp.route('/register', methods=['POST'])
def register():
    """
    Register new user with phone number.
    
    Expected JSON payload:
    {
        "phone_number": "+8613800138000",
        "verification_code": "123456",
        "password": "optional_password",
        "agreements": {
            "privacy_policy": {"version": "1.0", "agreed": true},
            "terms_of_service": {"version": "1.0", "agreed": true}
        },
        "user_info": {
            "nickname": "User123",
            "preferred_language": "zh-CN"
        }
    }
    
    Returns:
        JSON response with registration result and user info
    """
    try:
        # Parse and validate request
        try:
            data = PhoneRegistrationRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        # Get client IP
        client_ip = get_client_ip()
        
        # Verify SMS code first
        verification_result = sms_service.verify_code(
            phone_number=data.phone_number,
            verification_code=data.verification_code,
            purpose=SMSPurpose.REGISTRATION
        )
        
        if not verification_result.get('success'):
            return jsonify({
                'success': False,
                'error': 'verification_failed',
                'message': verification_result.get('message', 'SMS verification failed')
            }), 400
        
        # Check if phone number is already registered
        existing_account = db.session.query(Account).filter_by(phone_number=data.phone_number).first()
        if existing_account:
            return jsonify({
                'success': False,
                'error': 'phone_already_registered',
                'message': 'This phone number is already registered'
            }), 409
        
        # Create new user account
        phone_auth_service = PhoneAuthService()
        user_account = phone_auth_service.create_phone_user(
            phone_number=data.phone_number,
            password=data.password,
            user_info=data.user_info,
            client_ip=client_ip
        )
        
        # Record agreement consents
        agreement_service = AgreementService()
        for consent_type, agreement_data in data.agreements.items():
            try:
                consent_enum = ConsentType(consent_type)
                agreement_service.record_consent(
                    account_id=user_account.id,
                    consent_type=consent_enum,
                    agreed=agreement_data['agreed'],
                    version=agreement_data['version'],
                    ip_address=client_ip
                )
            except ValueError:
                logger.warning(f"Invalid consent type: {consent_type}")
        
        # Set up user session
        session['user_id'] = user_account.id
        session['phone_verified'] = True
        session['registration_time'] = datetime.utcnow().isoformat()
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user_account.id,
                'phone_number': user_account.phone_number,
                'phone_verified': user_account.phone_verified,
                'nickname': user_account.nickname,
                'created_at': user_account.created_at.isoformat(),
                'status': user_account.status
            }
        }
        
        logger.info(f"User registered successfully with phone: {data.phone_number[:8]}****")
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Unexpected error in phone registration: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Registration failed due to internal error'
        }), 500


@bp.route('/login', methods=['POST'])
def login():
    """
    Login user with phone number and SMS verification.
    
    Expected JSON payload:
    {
        "phone_number": "+8613800138000",
        "verification_code": "123456",
        "remember_me": false
    }
    
    Returns:
        JSON response with login result and user info
    """
    try:
        # Parse and validate request
        try:
            data = PhoneLoginRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        # Get client IP
        client_ip = get_client_ip()
        
        # Verify SMS code
        verification_result = sms_service.verify_code(
            phone_number=data.phone_number,
            verification_code=data.verification_code,
            purpose=SMSPurpose.LOGIN
        )
        
        if not verification_result.get('success'):
            return jsonify({
                'success': False,
                'error': 'verification_failed',
                'message': verification_result.get('message', 'SMS verification failed')
            }), 400
        
        # Find user account by phone number
        user_account = db.session.query(Account).filter_by(phone_number=data.phone_number).first()
        if not user_account:
            return jsonify({
                'success': False,
                'error': 'account_not_found',
                'message': 'No account found with this phone number'
            }), 404
        
        # Check account status
        if user_account.status != AccountStatus.ACTIVE:
            return jsonify({
                'success': False,
                'error': 'account_inactive',
                'message': f'Account status: {user_account.status}'
            }), 403
        
        # Update login information
        user_account.last_login_at = datetime.utcnow()
        user_account.last_login_ip = client_ip
        user_account.last_active_at = datetime.utcnow()
        
        db.session.commit()
        
        # Set up user session
        session['user_id'] = user_account.id
        session['phone_verified'] = True
        session['login_time'] = datetime.utcnow().isoformat()
        
        if data.remember_me:
            session.permanent = True
            session['remember_me'] = True
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user_account.id,
                'name': user_account.name,
                'phone_number': user_account.phone_number,
                'phone_verified': user_account.phone_verified,
                'nickname': user_account.nickname,
                'avatar': user_account.avatar,
                'interface_language': user_account.interface_language,
                'interface_theme': user_account.interface_theme,
                'timezone': user_account.timezone,
                'status': user_account.status,
                'last_login_at': user_account.last_login_at.isoformat() if user_account.last_login_at else None
            }
        }
        
        logger.info(f"User logged in successfully with phone: {data.phone_number[:8]}****")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in phone login: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Login failed due to internal error'
        }), 500


@bp.route('/agreements', methods=['GET'])
def get_agreements():
    """
    Get all available agreements.
    
    Returns:
        JSON response with all agreements and their current versions
    """
    try:
        agreement_service = AgreementService()
        agreements = agreement_service.get_agreements()
        
        return jsonify({
            'success': True,
            'agreements': agreements
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_agreements: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to retrieve agreements'
        }), 500


@bp.route('/agreements/consent', methods=['POST'])
def record_consent():
    """
    Record user consent for agreements.
    
    Expected JSON payload:
    {
        "account_id": "user_uuid",
        "consents": [
            {
                "consent_type": "privacy_policy",
                "agreed": true,
                "version": "1.0"
            }
        ]
    }
    
    Returns:
        JSON response with consent recording result
    """
    try:
        data = request.json
        account_id = data.get('account_id')
        consents = data.get('consents', [])
        
        if not account_id or not consents:
            return jsonify({
                'success': False,
                'error': 'missing_parameters',
                'message': 'account_id and consents are required'
            }), 400
        
        # Get client info
        client_ip = get_client_ip()
        user_agent = request.headers.get('User-Agent')
        
        agreement_service = AgreementService()
        recorded_count = 0
        failed_consents = []
        
        for consent_data in consents:
            try:
                consent_type = ConsentType(consent_data.get('consent_type'))
                agreed = consent_data.get('agreed', False)
                version = consent_data.get('version')
                
                if not version:
                    failed_consents.append({
                        'consent_type': consent_data.get('consent_type'),
                        'error': 'version_required'
                    })
                    continue
                
                success = agreement_service.record_consent(
                    account_id=account_id,
                    consent_type=consent_type,
                    agreed=agreed,
                    version=version,
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                
                if success:
                    recorded_count += 1
                else:
                    failed_consents.append({
                        'consent_type': consent_data.get('consent_type'),
                        'error': 'recording_failed'
                    })
                    
            except ValueError as e:
                failed_consents.append({
                    'consent_type': consent_data.get('consent_type'),
                    'error': f'invalid_consent_type: {str(e)}'
                })
        
        response_data = {
            'success': recorded_count > 0,
            'recorded_count': recorded_count,
            'total_count': len(consents),
            'message': f'Recorded {recorded_count} out of {len(consents)} consents'
        }
        
        if failed_consents:
            response_data['failed_consents'] = failed_consents
        
        status_code = 200 if recorded_count > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Unexpected error in record_consent: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to record consents'
        }), 500


@bp.route('/check-phone', methods=['POST'])
def check_phone():
    """
    Check if phone number is already registered.
    
    Expected JSON payload:
    {
        "phone_number": "+8613800138000"
    }
    
    Returns:
        JSON response with availability status
    """
    try:
        phone_number = request.json.get('phone_number')
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'missing_parameter',
                'message': 'phone_number is required'
            }), 400
        
        # Validate and clean phone number
        try:
            data = PhoneRegistrationRequest(
                phone_number=phone_number,
                verification_code='000000',  # Dummy code for validation
                agreements={'privacy_policy': {'version': '1.0', 'agreed': True}, 'terms_of_service': {'version': '1.0', 'agreed': True}}
            )
            phone_number = data.phone_number
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        # Check if phone number exists
        existing_account = db.session.query(Account).filter_by(phone_number=phone_number).first()
        
        return jsonify({
            'success': True,
            'available': existing_account is None,
            'registered': existing_account is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in check_phone: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Phone check failed due to internal error'
        }), 500