"""SMS system monitoring and health check controllers."""

import logging
from flask import Blueprint, jsonify
from datetime import datetime

from services.sms import sms_service
from configs.sms import sms_config

logger = logging.getLogger(__name__)

bp = Blueprint('system_sms', __name__, url_prefix='/api/system/sms')


@bp.route('/health', methods=['GET'])
async def get_sms_health():
    """
    Get SMS service health status.
    
    Returns:
        JSON response with health information
    """
    try:
        # Get health status from SMS service
        health_status = await sms_service.get_health_status()
        
        # Add configuration status
        config_errors = sms_config.validate()
        health_status['config_errors'] = config_errors
        health_status['config_valid'] = len(config_errors) == 0
        
        # Determine overall status
        if health_status['status'] == 'healthy' and health_status['config_valid']:
            overall_status = 'healthy'
            http_status = 200
        elif health_status['status'] == 'healthy' and not health_status['config_valid']:
            overall_status = 'degraded'
            http_status = 200
        else:
            overall_status = 'down'
            http_status = 503
        
        health_status['overall_status'] = overall_status
        health_status['timestamp'] = datetime.utcnow().isoformat()
        
        return jsonify(health_status), http_status
        
    except Exception as e:
        logger.error(f"SMS health check failed: {e}", exc_info=True)
        return jsonify({
            'overall_status': 'down',
            'status': 'down',
            'provider': 'unknown',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'config_valid': False
        }), 503


@bp.route('/config', methods=['GET'])
def get_sms_config():
    """
    Get SMS service configuration (excluding sensitive data).
    
    Returns:
        JSON response with configuration information
    """
    try:
        # Get sanitized configuration
        config_dict = sms_config.to_dict()
        
        # Add validation status
        config_errors = sms_config.validate()
        config_dict['validation_errors'] = config_errors
        config_dict['is_valid'] = len(config_errors) == 0
        
        return jsonify({
            'success': True,
            'config': config_dict,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get SMS config: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/statistics', methods=['GET'])
def get_sms_statistics():
    """
    Get SMS service usage statistics.
    
    Returns:
        JSON response with statistics
    """
    try:
        # Get basic statistics from database
        from models.base import get_db
        from models.compliance import SmsVerification
        from datetime import timedelta
        from sqlalchemy import and_, func
        
        with get_db() as db:
            now = datetime.utcnow()
            
            # Statistics for different time periods
            stats = {}
            
            time_periods = [
                ('last_hour', timedelta(hours=1)),
                ('last_24h', timedelta(days=1)),
                ('last_7d', timedelta(days=7)),
                ('last_30d', timedelta(days=30))
            ]
            
            for period_name, time_delta in time_periods:
                since = now - time_delta
                
                # Total sent
                total_sent = db.query(SmsVerification).filter(
                    SmsVerification.created_at >= since
                ).count()
                
                # Total verified
                total_verified = db.query(SmsVerification).filter(
                    and_(
                        SmsVerification.created_at >= since,
                        SmsVerification.verified_at.is_not(None)
                    )
                ).count()
                
                # By purpose
                by_purpose = db.query(
                    SmsVerification.purpose,
                    func.count(SmsVerification.id).label('count')
                ).filter(
                    SmsVerification.created_at >= since
                ).group_by(SmsVerification.purpose).all()
                
                stats[period_name] = {
                    'total_sent': total_sent,
                    'total_verified': total_verified,
                    'verification_rate': (total_verified / total_sent * 100) if total_sent > 0 else 0,
                    'by_purpose': {purpose: count for purpose, count in by_purpose}
                }
            
            # Cleanup stats
            expired_count = sms_service.cleanup_expired_codes()
            
            return jsonify({
                'success': True,
                'statistics': stats,
                'cleanup': {
                    'expired_codes_cleaned': expired_count
                },
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Failed to get SMS statistics: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@bp.route('/cleanup', methods=['POST'])
def cleanup_expired_codes():
    """
    Manually trigger cleanup of expired verification codes.
    
    Returns:
        JSON response with cleanup results
    """
    try:
        # Cleanup expired codes
        expired_count = sms_service.cleanup_expired_codes()
        
        logger.info(f"Manual SMS cleanup completed: {expired_count} codes removed")
        
        return jsonify({
            'success': True,
            'expired_codes_removed': expired_count,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"SMS cleanup failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500