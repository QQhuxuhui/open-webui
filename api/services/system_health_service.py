"""System health monitoring and performance tracking service."""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import logging

from models.engine import db
from utils.cache import cache_manager

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_free_gb: float
    response_time_ms: float
    active_connections: int
    error_rate_percent: float


@dataclass
class HealthCheckResult:
    """Health check result for a component."""
    component: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SystemHealthService:
    """Service for system health monitoring and performance tracking."""

    def __init__(self):
        self.cache = cache_manager
        self._start_time = time.time()

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        
        # Try cache first
        cache_key = "system_status"
        cached_status = self.cache.get(cache_key)
        if cached_status:
            return cached_status

        try:
            # Collect system metrics
            metrics = self._collect_system_metrics()
            
            # Run health checks
            health_checks = self._run_health_checks()
            
            # Calculate overall system health
            overall_status = self._calculate_overall_status(health_checks)
            
            # Get performance statistics
            performance_stats = self._get_performance_statistics()
            
            status = {
                'overall_status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - self._start_time,
                'metrics': asdict(metrics),
                'health_checks': [asdict(check) for check in health_checks],
                'performance_stats': performance_stats,
                'version_info': self._get_version_info()
            }

            # Cache for 30 seconds
            self.cache.set(cache_key, status, timeout=30)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        
        # Database response time
        response_time_ms = self._measure_database_response_time()
        
        # Get connection count (estimated)
        active_connections = self._get_active_connections()
        
        # Error rate (simplified)
        error_rate_percent = self._get_error_rate()

        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_gb=memory_available_gb,
            disk_percent=disk_percent,
            disk_free_gb=disk_free_gb,
            response_time_ms=response_time_ms,
            active_connections=active_connections,
            error_rate_percent=error_rate_percent
        )

    def _run_health_checks(self) -> List[HealthCheckResult]:
        """Run comprehensive health checks."""
        
        health_checks = []
        
        # Database health check
        health_checks.append(self._check_database_health())
        
        # Cache health check
        health_checks.append(self._check_cache_health())
        
        # File system health check
        health_checks.append(self._check_filesystem_health())
        
        # SMS service health check
        health_checks.append(self._check_sms_service_health())
        
        return health_checks

    def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        
        start_time = time.time()
        try:
            # Simple query to test connectivity
            result = db.session.execute(db.text("SELECT 1")).fetchone()
            latency_ms = (time.time() - start_time) * 1000
            
            if result and latency_ms < 100:
                status = "healthy"
            elif latency_ms < 500:
                status = "degraded"
            else:
                status = "unhealthy"
                
            return HealthCheckResult(
                component="database",
                status=status,
                latency_ms=latency_ms,
                details={"query_result": bool(result)}
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="database",
                status="unhealthy",
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def _check_cache_health(self) -> HealthCheckResult:
        """Check cache connectivity and performance."""
        
        start_time = time.time()
        try:
            # Test cache set/get
            test_key = f"health_check_{int(time.time())}"
            test_value = "test"
            
            self.cache.set(test_key, test_value, timeout=60)
            retrieved_value = self.cache.get(test_key)
            self.cache.delete(test_key)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if retrieved_value == test_value and latency_ms < 50:
                status = "healthy"
            elif retrieved_value == test_value and latency_ms < 200:
                status = "degraded"
            else:
                status = "unhealthy"
                
            return HealthCheckResult(
                component="cache",
                status=status,
                latency_ms=latency_ms,
                details={"test_successful": retrieved_value == test_value}
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="cache",
                status="unhealthy",
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def _check_filesystem_health(self) -> HealthCheckResult:
        """Check file system health and space."""
        
        start_time = time.time()
        try:
            disk = psutil.disk_usage('/')
            latency_ms = (time.time() - start_time) * 1000
            
            free_space_gb = disk.free / (1024**3)
            usage_percent = disk.percent
            
            if free_space_gb > 5 and usage_percent < 80:
                status = "healthy"
            elif free_space_gb > 1 and usage_percent < 90:
                status = "degraded"
            else:
                status = "unhealthy"
                
            return HealthCheckResult(
                component="filesystem",
                status=status,
                latency_ms=latency_ms,
                details={
                    "free_space_gb": free_space_gb,
                    "usage_percent": usage_percent
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="filesystem",
                status="unhealthy",
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def _check_sms_service_health(self) -> HealthCheckResult:
        """Check SMS service health."""
        
        start_time = time.time()
        try:
            # Simple availability check for SMS service
            from services.sms.sms_service import SMSService
            sms_service = SMSService()
            
            # Check if SMS service is configured and available
            is_available = hasattr(sms_service, 'client') and sms_service.client is not None
            latency_ms = (time.time() - start_time) * 1000
            
            status = "healthy" if is_available else "degraded"
                
            return HealthCheckResult(
                component="sms_service",
                status=status,
                latency_ms=latency_ms,
                details={"is_configured": is_available}
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="sms_service",
                status="degraded",
                latency_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )

    def _calculate_overall_status(self, health_checks: List[HealthCheckResult]) -> str:
        """Calculate overall system status from health checks."""
        
        if not health_checks:
            return "unknown"
            
        unhealthy_count = sum(1 for check in health_checks if check.status == "unhealthy")
        degraded_count = sum(1 for check in health_checks if check.status == "degraded")
        
        if unhealthy_count > 0:
            return "unhealthy"
        elif degraded_count > 0:
            return "degraded"
        else:
            return "healthy"

    def _measure_database_response_time(self) -> float:
        """Measure database response time."""
        
        start_time = time.time()
        try:
            db.session.execute(db.text("SELECT 1")).fetchone()
            return (time.time() - start_time) * 1000
        except Exception:
            return -1  # Error indicator

    def _get_active_connections(self) -> int:
        """Get approximate number of active connections."""
        try:
            # This is a simplified implementation
            # In production, you might query the database for actual connection count
            return len(psutil.net_connections(kind='inet'))
        except Exception:
            return 0

    def _get_error_rate(self) -> float:
        """Get current error rate percentage."""
        # This is a placeholder implementation
        # In production, you would track actual error rates from logs/metrics
        return 0.0

    def _get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        
        return {
            "requests_per_second": self._get_requests_per_second(),
            "average_response_time_ms": self._get_average_response_time(),
            "cache_hit_rate_percent": self._get_cache_hit_rate(),
            "database_query_time_ms": self._get_database_query_time(),
            "active_users": self._get_active_users_count()
        }

    def _get_requests_per_second(self) -> float:
        """Get current requests per second."""
        # Placeholder implementation
        return 0.0

    def _get_average_response_time(self) -> float:
        """Get average response time."""
        # Placeholder implementation  
        return 0.0

    def _get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        # Placeholder implementation
        return 0.0

    def _get_database_query_time(self) -> float:
        """Get average database query time."""
        return self._measure_database_response_time()

    def _get_active_users_count(self) -> int:
        """Get count of active users."""
        # Placeholder implementation
        return 0

    def _get_version_info(self) -> Dict[str, Any]:
        """Get application version information."""
        
        return {
            "application_version": "1.0.0",
            "python_version": "3.12",
            "database_version": "PostgreSQL",
            "build_date": "2025-01-13",
            "environment": "development"
        }

    def get_historical_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical system metrics."""
        
        # This would typically query a time-series database
        # For now, return sample data structure
        return [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "cpu_percent": 25.0 + (i % 10),
                "memory_percent": 45.0 + (i % 15),
                "response_time_ms": 150.0 + (i % 50),
                "error_rate": 0.1
            }
            for i in range(hours)
        ]

    def log_performance_metrics(self, metrics: SystemMetrics):
        """Log performance metrics for monitoring."""
        
        logger.info(
            f"System Metrics - CPU: {metrics.cpu_percent}%, "
            f"Memory: {metrics.memory_percent}%, "
            f"Response Time: {metrics.response_time_ms}ms, "
            f"Error Rate: {metrics.error_rate_percent}%"
        )


# Create service instance
system_health_service = SystemHealthService()