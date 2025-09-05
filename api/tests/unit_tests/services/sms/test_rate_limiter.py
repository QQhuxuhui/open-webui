"""Unit tests for SMS rate limiter."""

import time
import pytest
from unittest.mock import Mock, patch

from configs.sms import SMSConfig
from services.sms.rate_limiter import InMemoryRateLimiter, RateLimit


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = SMSConfig(
            phone_rate_per_minute=2,
            phone_rate_per_hour=5,
            phone_rate_per_day=10,
            ip_rate_per_minute=5,
            ip_rate_per_hour=20
        )
        self.rate_limiter = InMemoryRateLimiter(self.config)
    
    def test_phone_rate_limit_within_limits(self):
        """Test phone rate limiting when within limits."""
        phone = '+8613800138000'
        
        # First request should be allowed
        allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
        assert allowed is True
        assert error is None
        
        # Second request should still be allowed (limit is 2 per minute)
        allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
        assert allowed is True
        assert error is None
    
    def test_phone_rate_limit_exceeded_per_minute(self):
        """Test phone rate limiting when minute limit is exceeded."""
        phone = '+8613800138001'
        
        # Make requests up to the limit
        for i in range(2):  # Limit is 2 per minute
            allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
            assert allowed is True
        
        # Next request should be blocked
        allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
        assert allowed is False
        assert 'per minute' in error
    
    def test_phone_rate_limit_window_sliding(self):
        """Test that rate limit window slides correctly."""
        phone = '+8613800138002'
        
        with patch('time.time') as mock_time:
            # Start at time 0
            mock_time.return_value = 0
            
            # Make maximum requests
            for i in range(2):
                allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
                assert allowed is True
            
            # Should be blocked now
            allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
            assert allowed is False
            
            # Move time forward by 61 seconds (past the 60-second window)
            mock_time.return_value = 61
            
            # Should be allowed again
            allowed, error = self.rate_limiter.check_phone_rate_limit(phone)
            assert allowed is True
    
    def test_ip_rate_limit_within_limits(self):
        """Test IP rate limiting when within limits."""
        ip = '192.168.1.100'
        
        # Should be able to make up to 5 requests per minute
        for i in range(5):
            allowed, error = self.rate_limiter.check_ip_rate_limit(ip)
            assert allowed is True
            assert error is None
    
    def test_ip_rate_limit_exceeded(self):
        """Test IP rate limiting when limit is exceeded."""
        ip = '192.168.1.101'
        
        # Make requests up to the limit
        for i in range(5):  # Limit is 5 per minute
            allowed, error = self.rate_limiter.check_ip_rate_limit(ip)
            assert allowed is True
        
        # Next request should be blocked
        allowed, error = self.rate_limiter.check_ip_rate_limit(ip)
        assert allowed is False
        assert 'per minute' in error
    
    def test_combined_rate_limits(self):
        """Test combined phone and IP rate limiting."""
        phone = '+8613800138003'
        ip = '192.168.1.102'
        
        # Both should be allowed initially
        allowed, error = self.rate_limiter.check_rate_limits(phone, ip)
        assert allowed is True
        assert error is None
        
        # Make requests to exhaust phone limit
        for i in range(1):  # One more to reach limit of 2
            allowed, error = self.rate_limiter.check_rate_limits(phone, ip)
            assert allowed is True
        
        # Phone limit should be reached
        allowed, error = self.rate_limiter.check_rate_limits(phone, ip)
        assert allowed is False
        assert 'Phone number' in error
    
    def test_rate_limit_status(self):
        """Test getting rate limit status information."""
        phone = '+8613800138004'
        ip = '192.168.1.103'
        
        # Make some requests
        self.rate_limiter.check_phone_rate_limit(phone)
        self.rate_limiter.check_ip_rate_limit(ip)
        
        # Get status
        status = self.rate_limiter.get_rate_limit_status(phone, ip)
        
        assert 'phone_number' in status
        assert 'phone_limits' in status
        assert 'ip_address' in status
        assert 'ip_limits' in status
        
        # Check phone limits structure
        phone_limits = status['phone_limits']
        assert len(phone_limits) == 3  # minute, hour, day
        
        minute_limit = phone_limits[0]
        assert minute_limit['period'] == 'minute'
        assert minute_limit['limit'] == 2
        assert minute_limit['used'] == 1
        assert minute_limit['remaining'] == 1
        
        # Check IP limits structure
        ip_limits = status['ip_limits']
        assert len(ip_limits) == 2  # minute, hour
        
        ip_minute_limit = ip_limits[0]
        assert ip_minute_limit['period'] == 'minute'
        assert ip_minute_limit['limit'] == 5
        assert ip_minute_limit['used'] == 1
        assert ip_minute_limit['remaining'] == 4
    
    def test_reset_rate_limits(self):
        """Test resetting rate limits."""
        phone = '+8613800138005'
        ip = '192.168.1.104'
        
        # Exhaust limits
        for i in range(2):
            self.rate_limiter.check_phone_rate_limit(phone)
        for i in range(5):
            self.rate_limiter.check_ip_rate_limit(ip)
        
        # Should be blocked
        allowed, _ = self.rate_limiter.check_phone_rate_limit(phone)
        assert allowed is False
        
        allowed, _ = self.rate_limiter.check_ip_rate_limit(ip)
        assert allowed is False
        
        # Reset limits
        self.rate_limiter.reset_rate_limits(phone, ip)
        
        # Should be allowed again
        allowed, _ = self.rate_limiter.check_phone_rate_limit(phone)
        assert allowed is True
        
        allowed, _ = self.rate_limiter.check_ip_rate_limit(ip)
        assert allowed is True
    
    def test_clear_all_rate_limits(self):
        """Test clearing all rate limits."""
        phone1 = '+8613800138006'
        phone2 = '+8613800138007'
        ip1 = '192.168.1.105'
        ip2 = '192.168.1.106'
        
        # Make some requests to populate rate limiters
        self.rate_limiter.check_phone_rate_limit(phone1)
        self.rate_limiter.check_phone_rate_limit(phone2)
        self.rate_limiter.check_ip_rate_limit(ip1)
        self.rate_limiter.check_ip_rate_limit(ip2)
        
        # Verify internal state has data
        assert len(self.rate_limiter._phone_requests) >= 2
        assert len(self.rate_limiter._ip_requests) >= 2
        
        # Clear all
        self.rate_limiter.clear_all_rate_limits()
        
        # Verify internal state is cleared
        assert len(self.rate_limiter._phone_requests) == 0
        assert len(self.rate_limiter._ip_requests) == 0
    
    def test_cleanup_old_entries(self):
        """Test cleanup of old rate limit entries."""
        phone = '+8613800138008'
        
        with patch('time.time') as mock_time:
            # Make requests at different times
            mock_time.return_value = 0
            self.rate_limiter.check_phone_rate_limit(phone)
            
            mock_time.return_value = 3600  # 1 hour later
            self.rate_limiter.check_phone_rate_limit(phone)
            
            # Force cleanup by checking an entry after max age
            mock_time.return_value = 86401  # > 24 hours later
            requests_dict = self.rate_limiter._phone_requests
            self.rate_limiter._cleanup_old_entries(requests_dict, 86401)
            
            # Old entries should be cleaned up
            if phone in requests_dict:
                # If entry still exists, it should be empty or only contain recent requests
                assert len(requests_dict[phone]) <= 1
    
    def test_different_phone_numbers_independent(self):
        """Test that different phone numbers have independent rate limits."""
        phone1 = '+8613800138009'
        phone2 = '+8613800138010'
        
        # Exhaust limit for phone1
        for i in range(2):
            allowed, _ = self.rate_limiter.check_phone_rate_limit(phone1)
            assert allowed is True
        
        # phone1 should be blocked
        allowed, _ = self.rate_limiter.check_phone_rate_limit(phone1)
        assert allowed is False
        
        # phone2 should still be allowed
        allowed, _ = self.rate_limiter.check_phone_rate_limit(phone2)
        assert allowed is True
    
    def test_different_ip_addresses_independent(self):
        """Test that different IP addresses have independent rate limits."""
        ip1 = '192.168.1.107'
        ip2 = '192.168.1.108'
        
        # Exhaust limit for ip1
        for i in range(5):
            allowed, _ = self.rate_limiter.check_ip_rate_limit(ip1)
            assert allowed is True
        
        # ip1 should be blocked
        allowed, _ = self.rate_limiter.check_ip_rate_limit(ip1)
        assert allowed is False
        
        # ip2 should still be allowed
        allowed, _ = self.rate_limiter.check_ip_rate_limit(ip2)
        assert allowed is True
    
    def test_rate_limit_configuration(self):
        """Test rate limiter with different configurations."""
        custom_config = SMSConfig(
            phone_rate_per_minute=1,
            phone_rate_per_hour=3,
            phone_rate_per_day=5,
            ip_rate_per_minute=2,
            ip_rate_per_hour=6
        )
        
        custom_limiter = InMemoryRateLimiter(custom_config)
        phone = '+8613800138011'
        
        # Should allow 1 request per minute
        allowed, _ = custom_limiter.check_phone_rate_limit(phone)
        assert allowed is True
        
        # Second request should be blocked
        allowed, error = custom_limiter.check_phone_rate_limit(phone)
        assert allowed is False
        assert '1/1 per minute' in error