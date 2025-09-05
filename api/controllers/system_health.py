"""System health and monitoring controller."""

from flask import Blueprint, jsonify, current_app
from flask_login import login_required

from services.system_health_service import system_health_service
from decorators.rate_limit import rate_limit

health_bp = Blueprint('health', __name__, url_prefix='/api/health')


@health_bp.route('/status', methods=['GET'])
@rate_limit("health_check", per_minute=60)
def get_system_status():
    """Get comprehensive system status and health metrics."""
    try:
        status = system_health_service.get_system_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        current_app.logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve system status'
        }), 500


@health_bp.route('/metrics', methods=['GET'])
@login_required
@rate_limit("metrics_check", per_minute=30)
def get_system_metrics():
    """Get detailed system performance metrics (authenticated users only)."""
    try:
        status = system_health_service.get_system_status()
        
        # Return detailed metrics for authenticated users
        return jsonify({
            'success': True,
            'data': {
                'metrics': status.get('metrics', {}),
                'performance_stats': status.get('performance_stats', {}),
                'health_checks': status.get('health_checks', []),
                'uptime_seconds': status.get('uptime_seconds', 0)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Metrics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve system metrics'
        }), 500


@health_bp.route('/metrics/historical', methods=['GET'])
@login_required
@rate_limit("historical_metrics", per_minute=10)
def get_historical_metrics():
    """Get historical system metrics."""
    try:
        from flask import request
        hours = request.args.get('hours', 24, type=int)
        hours = min(max(hours, 1), 168)  # Limit to 1-168 hours (1 week)
        
        metrics = system_health_service.get_historical_metrics(hours)
        
        return jsonify({
            'success': True,
            'data': {
                'metrics': metrics,
                'period_hours': hours
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Historical metrics error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve historical metrics'
        }), 500


@health_bp.route('/ping', methods=['GET'])
def ping():
    """Simple health ping endpoint."""
    return jsonify({
        'success': True,
        'message': 'pong',
        'timestamp': system_health_service._start_time
    })