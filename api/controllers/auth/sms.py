"""SMS verification controllers."""

import logging
from typing import Optional
from flask import Blueprint, request, jsonify
from pydantic import BaseModel, validator
import re

from models.compliance import SMSPurpose
from services.sms import sms_service
from services.sms.rate_limiter import rate_limiter
from services.sms.sms_service import RateLimitExceededError, VerificationCodeError, SMSServiceError

logger = logging.getLogger(__name__)

bp = Blueprint('sms', __name__, url_prefix='/api/auth')


class SendSMSRequest(BaseModel):
    """Request model for sending SMS verification codes."""
    phone_number: str
    purpose: SMSPurpose
    
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


class VerifySMSRequest(BaseModel):
    """Request model for verifying SMS codes."""
    phone_number: str
    verification_code: str
    purpose: SMSPurpose
    
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


@bp.route('/send-sms', methods=['POST'])
async def send_sms():
    """
    Send SMS verification code.
    
    Expected JSON payload:
    {
        "phone_number": "+8613800138000",
        "purpose": "registration"
    }
    
    Returns:
        JSON response with result
    """
    try:
        # Parse and validate request
        try:
            data = SendSMSRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        # Get client IP for rate limiting
        client_ip = get_client_ip()
        
        # Check rate limits
        rate_allowed, rate_error = rate_limiter.check_rate_limits(
            phone_number=data.phone_number,
            ip_address=client_ip
        )
        
        if not rate_allowed:
            logger.warning(
                f"SMS rate limit exceeded: phone={data.phone_number}, "
                f"ip={client_ip}, error={rate_error}"
            )
            return jsonify({
                'success': False,
                'error': 'rate_limit_exceeded',
                'message': rate_error
            }), 429
        
        # Send SMS verification code
        result = await sms_service.send_verification_code(
            phone_number=data.phone_number,
            purpose=data.purpose,
            ip_address=client_ip
        )
        
        return jsonify(result), 200
        
    except RateLimitExceededError as e:
        logger.warning(f"SMS rate limit exceeded: {e}")
        return jsonify({
            'success': False,
            'error': 'rate_limit_exceeded',
            'message': str(e)
        }), 429
        
    except SMSServiceError as e:
        logger.error(f"SMS service error: {e}")
        return jsonify({
            'success': False,
            'error': 'sms_service_error',
            'message': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in send_sms: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'An internal error occurred'
        }), 500


@bp.route('/verify-sms', methods=['POST'])
def verify_sms():
    """
    Verify SMS verification code.
    
    Expected JSON payload:
    {
        "phone_number": "+8613800138000",
        "verification_code": "123456",
        "purpose": "registration"
    }
    
    Returns:
        JSON response with verification result
    """
    try:
        # Parse and validate request
        try:
            data = VerifySMSRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        # Verify SMS code
        result = sms_service.verify_code(
            phone_number=data.phone_number,
            verification_code=data.verification_code,
            purpose=data.purpose
        )
        
        return jsonify(result), 200
        
    except VerificationCodeError as e:
        logger.warning(f"SMS verification failed: {e}")
        return jsonify({
            'success': False,
            'error': 'verification_failed',
            'message': str(e)
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error in verify_sms: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'An internal error occurred'
        }), 500


@bp.route('/sms-status', methods=['GET'])
def get_sms_status():
    """
    Get SMS verification status for phone number and purpose.
    
    Query parameters:
    - phone_number: Phone number to check
    - purpose: Purpose of verification
    
    Returns:
        JSON response with status information
    """
    try:
        # Get query parameters
        phone_number = request.args.get('phone_number')
        purpose = request.args.get('purpose')
        
        if not phone_number or not purpose:
            return jsonify({
                'success': False,
                'error': 'missing_parameters',
                'message': 'phone_number and purpose are required'
            }), 400
        
        # Validate purpose
        try:
            purpose_enum = SMSPurpose(purpose)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'invalid_purpose',
                'message': f'Invalid purpose. Valid values: {list(SMSPurpose)}'
            }), 400
        
        # Get status
        status = sms_service.get_verification_status(phone_number, purpose_enum)
        
        if status:
            return jsonify({
                'success': True,
                'status': status
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'No verification found for this phone number and purpose'
            }), 404
        
    except Exception as e:
        logger.error(f"Unexpected error in get_sms_status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'An internal error occurred'
        }), 500


@bp.route('/rate-limit-status', methods=['GET'])
def get_rate_limit_status():
    """
    Get current rate limit status.
    
    Query parameters:
    - phone_number: Phone number to check
    - ip_address: IP address to check (optional)
    
    Returns:
        JSON response with rate limit status
    """
    try:
        # Get query parameters
        phone_number = request.args.get('phone_number')
        ip_address = request.args.get('ip_address') or get_client_ip()
        
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'missing_parameters',
                'message': 'phone_number is required'
            }), 400
        
        # Get rate limit status
        status = rate_limiter.get_rate_limit_status(phone_number, ip_address)
        
        return jsonify({
            'success': True,
            'rate_limits': status
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_rate_limit_status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'An internal error occurred'
        }), 500