"""Performance monitoring and optimization service."""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
import threading
from collections import defaultdict, deque

from utils.cache import cache_manager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    timestamp: datetime
    user_id: Optional[str] = None
    error_message: Optional[str] = None


class PerformanceMonitor:
    """Thread-safe performance monitoring service."""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.metrics_lock = threading.RLock()
        
        # Aggregated statistics
        self.endpoint_stats = defaultdict(lambda: {
            'total_requests': 0,
            'total_response_time': 0.0,
            'error_count': 0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0,
            'recent_errors': deque(maxlen=100)
        })
        
        # Cache for expensive calculations
        self.cache = cache_manager
        
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric."""
        with self.metrics_lock:
            self.metrics.append(metric)
            
            # Update endpoint statistics
            key = f"{metric.method}:{metric.endpoint}"
            stats = self.endpoint_stats[key]
            
            stats['total_requests'] += 1
            stats['total_response_time'] += metric.response_time_ms
            
            if metric.status_code >= 400:
                stats['error_count'] += 1
                stats['recent_errors'].append({
                    'timestamp': metric.timestamp,
                    'status_code': metric.status_code,
                    'error_message': metric.error_message,
                    'response_time_ms': metric.response_time_ms
                })
            
            # Update min/max response times
            stats['min_response_time'] = min(stats['min_response_time'], metric.response_time_ms)
            stats['max_response_time'] = max(stats['max_response_time'], metric.response_time_ms)
            
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance metrics summary for the specified time period."""
        
        cache_key = f"metrics_summary:{hours}"
        cached_summary = self.cache.get(cache_key)
        if cached_summary:
            return cached_summary
            
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.metrics_lock:
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
            
        if not recent_metrics:
            return {
                'total_requests': 0,
                'average_response_time_ms': 0,
                'error_rate_percent': 0,
                'requests_per_minute': 0,
                'top_endpoints': [],
                'slow_endpoints': [],
                'error_endpoints': []
            }
            
        total_requests = len(recent_metrics)
        total_response_time = sum(m.response_time_ms for m in recent_metrics)
        error_count = sum(1 for m in recent_metrics if m.status_code >= 400)
        
        # Calculate averages and rates
        avg_response_time = total_response_time / total_requests if total_requests > 0 else 0
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        requests_per_minute = total_requests / (hours * 60) if hours > 0 else 0
        
        # Endpoint analysis
        endpoint_metrics = defaultdict(lambda: {
            'count': 0, 
            'total_time': 0, 
            'errors': 0,
            'max_time': 0
        })
        
        for metric in recent_metrics:
            key = f"{metric.method}:{metric.endpoint}"
            endpoint_metrics[key]['count'] += 1
            endpoint_metrics[key]['total_time'] += metric.response_time_ms
            endpoint_metrics[key]['max_time'] = max(
                endpoint_metrics[key]['max_time'], 
                metric.response_time_ms
            )
            if metric.status_code >= 400:
                endpoint_metrics[key]['errors'] += 1
                
        # Top endpoints by request count
        top_endpoints = sorted(
            [(endpoint, data['count']) for endpoint, data in endpoint_metrics.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Slowest endpoints by average response time
        slow_endpoints = []
        for endpoint, data in endpoint_metrics.items():
            if data['count'] > 0:
                avg_time = data['total_time'] / data['count']
                slow_endpoints.append((endpoint, avg_time))
        slow_endpoints = sorted(slow_endpoints, key=lambda x: x[1], reverse=True)[:10]
        
        # Endpoints with highest error rates
        error_endpoints = []
        for endpoint, data in endpoint_metrics.items():
            if data['count'] > 0:
                error_rate_ep = (data['errors'] / data['count']) * 100
                if error_rate_ep > 0:
                    error_endpoints.append((endpoint, error_rate_ep))
        error_endpoints = sorted(error_endpoints, key=lambda x: x[1], reverse=True)[:10]
        
        summary = {
            'period_hours': hours,
            'total_requests': total_requests,
            'average_response_time_ms': round(avg_response_time, 2),
            'error_rate_percent': round(error_rate, 2),
            'requests_per_minute': round(requests_per_minute, 2),
            'top_endpoints': [{'endpoint': ep, 'count': count} for ep, count in top_endpoints],
            'slow_endpoints': [{'endpoint': ep, 'avg_time_ms': round(time, 2)} 
                             for ep, time in slow_endpoints],
            'error_endpoints': [{'endpoint': ep, 'error_rate_percent': round(rate, 2)} 
                              for ep, rate in error_endpoints],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Cache for 1 minute
        self.cache.set(cache_key, summary, timeout=60)
        
        return summary
        
    def get_endpoint_details(self, endpoint: str, method: str = None) -> Dict[str, Any]:
        """Get detailed performance metrics for a specific endpoint."""
        
        with self.metrics_lock:
            if method:
                endpoint_metrics = [m for m in self.metrics 
                                  if m.endpoint == endpoint and m.method == method]
            else:
                endpoint_metrics = [m for m in self.metrics if m.endpoint == endpoint]
                
        if not endpoint_metrics:
            return {'error': 'No metrics found for endpoint'}
            
        # Calculate statistics
        response_times = [m.response_time_ms for m in endpoint_metrics]
        error_count = sum(1 for m in endpoint_metrics if m.status_code >= 400)
        
        return {
            'endpoint': endpoint,
            'method': method,
            'total_requests': len(endpoint_metrics),
            'error_count': error_count,
            'error_rate_percent': (error_count / len(endpoint_metrics)) * 100,
            'avg_response_time_ms': sum(response_times) / len(response_times),
            'min_response_time_ms': min(response_times),
            'max_response_time_ms': max(response_times),
            'recent_requests': [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'response_time_ms': m.response_time_ms,
                    'status_code': m.status_code,
                    'user_id': m.user_id
                }
                for m in sorted(endpoint_metrics, key=lambda x: x.timestamp, reverse=True)[:50]
            ]
        }
        
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on thresholds."""
        
        alerts = []
        summary = self.get_metrics_summary(hours=1)
        
        # Alert thresholds
        HIGH_ERROR_RATE = 5.0  # 5%
        SLOW_RESPONSE_TIME = 1000.0  # 1000ms
        HIGH_TRAFFIC = 1000  # requests per minute
        
        # Check overall error rate
        if summary['error_rate_percent'] > HIGH_ERROR_RATE:
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'warning',
                'message': f"High error rate: {summary['error_rate_percent']:.1f}%",
                'value': summary['error_rate_percent'],
                'threshold': HIGH_ERROR_RATE
            })
            
        # Check overall response time
        if summary['average_response_time_ms'] > SLOW_RESPONSE_TIME:
            alerts.append({
                'type': 'slow_response_time',
                'severity': 'warning',
                'message': f"Slow average response time: {summary['average_response_time_ms']:.1f}ms",
                'value': summary['average_response_time_ms'],
                'threshold': SLOW_RESPONSE_TIME
            })
            
        # Check traffic volume
        if summary['requests_per_minute'] > HIGH_TRAFFIC:
            alerts.append({
                'type': 'high_traffic',
                'severity': 'info',
                'message': f"High traffic volume: {summary['requests_per_minute']:.1f} req/min",
                'value': summary['requests_per_minute'],
                'threshold': HIGH_TRAFFIC
            })
            
        # Check individual endpoints
        for endpoint_data in summary['error_endpoints']:
            if endpoint_data['error_rate_percent'] > HIGH_ERROR_RATE:
                alerts.append({
                    'type': 'endpoint_high_errors',
                    'severity': 'warning',
                    'message': f"Endpoint {endpoint_data['endpoint']} has high error rate: {endpoint_data['error_rate_percent']:.1f}%",
                    'endpoint': endpoint_data['endpoint'],
                    'value': endpoint_data['error_rate_percent'],
                    'threshold': HIGH_ERROR_RATE
                })
                
        return alerts
        
    def clear_old_metrics(self, hours: int = 24):
        """Clear metrics older than specified hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self.metrics_lock:
            # Filter out old metrics
            self.metrics = deque(
                [m for m in self.metrics if m.timestamp >= cutoff_time],
                maxlen=self.max_metrics
            )
            
        logger.info(f"Cleared metrics older than {hours} hours")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def performance_tracking(endpoint_name: str = None):
    """Decorator to track endpoint performance."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or getattr(func, '__name__', 'unknown')
            method = 'unknown'
            status_code = 200
            error_message = None
            user_id = None
            
            try:
                # Try to get request context
                from flask import request, g
                if request:
                    method = request.method
                    endpoint = endpoint or request.endpoint or 'unknown'
                    user_id = getattr(g, 'current_user_id', None)
                    
            except RuntimeError:
                # No request context
                pass
                
            try:
                result = func(*args, **kwargs)
                
                # Try to extract status code from response
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                    
                return result
                
            except Exception as e:
                status_code = 500
                error_message = str(e)
                raise
                
            finally:
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                # Record the metric
                metric = PerformanceMetric(
                    endpoint=endpoint,
                    method=method,
                    response_time_ms=response_time_ms,
                    status_code=status_code,
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    error_message=error_message
                )
                
                performance_monitor.record_metric(metric)
                
        return wrapper
    return decorator


@contextmanager
def performance_context(operation_name: str):
    """Context manager to track performance of code blocks."""
    start_time = time.time()
    error_message = None
    
    try:
        yield
    except Exception as e:
        error_message = str(e)
        raise
    finally:
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        metric = PerformanceMetric(
            endpoint=operation_name,
            method='operation',
            response_time_ms=response_time_ms,
            status_code=500 if error_message else 200,
            timestamp=datetime.utcnow(),
            error_message=error_message
        )
        
        performance_monitor.record_metric(metric)


class PerformanceOptimizer:
    """Service for performance optimization recommendations."""
    
    @staticmethod
    def analyze_performance(hours: int = 24) -> Dict[str, Any]:
        """Analyze performance and provide optimization recommendations."""
        
        summary = performance_monitor.get_metrics_summary(hours)
        alerts = performance_monitor.get_performance_alerts()
        
        recommendations = []
        
        # Analyze slow endpoints
        if summary['slow_endpoints']:
            slow_endpoint = summary['slow_endpoints'][0]
            if slow_endpoint['avg_time_ms'] > 500:
                recommendations.append({
                    'type': 'endpoint_optimization',
                    'priority': 'high',
                    'description': f"Optimize {slow_endpoint['endpoint']} - average response time {slow_endpoint['avg_time_ms']:.1f}ms",
                    'suggestions': [
                        'Add caching for expensive operations',
                        'Optimize database queries',
                        'Consider pagination for large datasets',
                        'Add database indexes if needed'
                    ]
                })
                
        # Analyze error patterns
        if summary['error_rate_percent'] > 2:
            recommendations.append({
                'type': 'error_reduction',
                'priority': 'high',
                'description': f"Reduce error rate from {summary['error_rate_percent']:.1f}%",
                'suggestions': [
                    'Improve input validation',
                    'Add better error handling',
                    'Review recent deployments',
                    'Check external service dependencies'
                ]
            })
            
        # Analyze traffic patterns
        if summary['requests_per_minute'] > 500:
            recommendations.append({
                'type': 'scalability',
                'priority': 'medium',
                'description': f"High traffic volume: {summary['requests_per_minute']:.1f} req/min",
                'suggestions': [
                    'Consider implementing rate limiting',
                    'Add horizontal scaling',
                    'Optimize database connection pooling',
                    'Implement CDN for static content'
                ]
            })
            
        return {
            'analysis_period_hours': hours,
            'performance_summary': summary,
            'alerts': alerts,
            'recommendations': recommendations,
            'analyzed_at': datetime.utcnow().isoformat()
        }