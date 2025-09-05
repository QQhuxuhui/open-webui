"""Rate limiting for SMS services."""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from threading import Lock
from collections import defaultdict, deque

from configs.sms import SMSConfig, sms_config

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration."""
    limit: int
    window_seconds: int
    period_name: str


class InMemoryRateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self, config: Optional[SMSConfig] = None):
        """Initialize rate limiter."""
        self.config = config or sms_config
        self._lock = Lock()
        self._phone_requests: Dict[str, deque] = defaultdict(deque)
        self._ip_requests: Dict[str, deque] = defaultdict(deque)
        
        # Define rate limits
        self.phone_limits = [
            RateLimit(self.config.phone_rate_per_minute, 60, "minute"),
            RateLimit(self.config.phone_rate_per_hour, 3600, "hour"),
            RateLimit(self.config.phone_rate_per_day, 86400, "day")
        ]
        
        self.ip_limits = [
            RateLimit(self.config.ip_rate_per_minute, 60, "minute"),
            RateLimit(self.config.ip_rate_per_hour, 3600, "hour")
        ]
    
    def check_phone_rate_limit(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Check if phone number is within rate limits.
        
        Args:
            phone_number: Phone number to check
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self._lock:
            current_time = time.time()
            requests = self._phone_requests[phone_number]
            
            # Check each rate limit
            for rate_limit in self.phone_limits:
                # Remove old requests outside the window
                cutoff_time = current_time - rate_limit.window_seconds
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
                
                # Check if limit would be exceeded
                if len(requests) >= rate_limit.limit:
                    return False, f"Phone number rate limit exceeded: {len(requests)}/{rate_limit.limit} per {rate_limit.period_name}"
            
            # Record this request
            requests.append(current_time)
            
            # Cleanup old entries to prevent memory leaks
            self._cleanup_old_entries(self._phone_requests, current_time)
            
            return True, None
    
    def check_ip_rate_limit(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if IP address is within rate limits.
        
        Args:
            ip_address: IP address to check
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self._lock:
            current_time = time.time()
            requests = self._ip_requests[ip_address]
            
            # Check each rate limit
            for rate_limit in self.ip_limits:
                # Remove old requests outside the window
                cutoff_time = current_time - rate_limit.window_seconds
                while requests and requests[0] < cutoff_time:
                    requests.popleft()
                
                # Check if limit would be exceeded
                if len(requests) >= rate_limit.limit:
                    return False, f"IP address rate limit exceeded: {len(requests)}/{rate_limit.limit} per {rate_limit.period_name}"
            
            # Record this request
            requests.append(current_time)
            
            # Cleanup old entries to prevent memory leaks
            self._cleanup_old_entries(self._ip_requests, current_time)
            
            return True, None
    
    def check_rate_limits(
        self,
        phone_number: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check both phone and IP rate limits.
        
        Args:
            phone_number: Phone number to check
            ip_address: IP address to check (optional)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # Check phone rate limit
        phone_allowed, phone_error = self.check_phone_rate_limit(phone_number)
        if not phone_allowed:
            return False, phone_error
        
        # Check IP rate limit if provided
        if ip_address:
            ip_allowed, ip_error = self.check_ip_rate_limit(ip_address)
            if not ip_allowed:
                return False, ip_error
        
        return True, None
    
    def get_rate_limit_status(
        self,
        phone_number: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Get current rate limit status for phone number and IP.
        
        Args:
            phone_number: Phone number to check
            ip_address: IP address to check (optional)
            
        Returns:
            Dictionary with rate limit status
        """
        with self._lock:
            current_time = time.time()
            
            # Get phone number status
            phone_requests = self._phone_requests[phone_number]
            phone_status = []
            
            for rate_limit in self.phone_limits:
                cutoff_time = current_time - rate_limit.window_seconds
                # Count requests in this window
                recent_requests = sum(1 for req_time in phone_requests if req_time >= cutoff_time)
                
                phone_status.append({
                    'period': rate_limit.period_name,
                    'limit': rate_limit.limit,
                    'used': recent_requests,
                    'remaining': max(0, rate_limit.limit - recent_requests),
                    'window_seconds': rate_limit.window_seconds
                })
            
            result = {
                'phone_number': phone_number,
                'phone_limits': phone_status
            }
            
            # Get IP address status if provided
            if ip_address:
                ip_requests = self._ip_requests[ip_address]
                ip_status = []
                
                for rate_limit in self.ip_limits:
                    cutoff_time = current_time - rate_limit.window_seconds
                    # Count requests in this window
                    recent_requests = sum(1 for req_time in ip_requests if req_time >= cutoff_time)
                    
                    ip_status.append({
                        'period': rate_limit.period_name,
                        'limit': rate_limit.limit,
                        'used': recent_requests,
                        'remaining': max(0, rate_limit.limit - recent_requests),
                        'window_seconds': rate_limit.window_seconds
                    })
                
                result['ip_address'] = ip_address
                result['ip_limits'] = ip_status
            
            return result
    
    def reset_rate_limits(
        self,
        phone_number: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Reset rate limits for specific phone number or IP address.
        
        Args:
            phone_number: Phone number to reset (optional)
            ip_address: IP address to reset (optional)
        """
        with self._lock:
            if phone_number:
                self._phone_requests[phone_number].clear()
                logger.info(f"Reset rate limits for phone number: {phone_number}")
            
            if ip_address:
                self._ip_requests[ip_address].clear()
                logger.info(f"Reset rate limits for IP address: {ip_address}")
    
    def clear_all_rate_limits(self) -> None:
        """Clear all rate limit data."""
        with self._lock:
            self._phone_requests.clear()
            self._ip_requests.clear()
            logger.info("Cleared all rate limit data")
    
    def _cleanup_old_entries(
        self,
        requests_dict: Dict[str, deque],
        current_time: float,
        max_age_seconds: int = 86400  # 24 hours
    ) -> None:
        """
        Cleanup old entries to prevent memory leaks.
        
        Args:
            requests_dict: Dictionary of request queues
            current_time: Current timestamp
            max_age_seconds: Maximum age to keep entries
        """
        cutoff_time = current_time - max_age_seconds
        
        # Remove entries that are completely old
        keys_to_remove = []
        for key, requests in requests_dict.items():
            # Remove old requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # If no requests left, mark for removal
            if not requests:
                keys_to_remove.append(key)
        
        # Remove empty entries
        for key in keys_to_remove:
            del requests_dict[key]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()