"""Rate limiting implementation for API protection.

This module provides enterprise-grade rate limiting with:
- Token bucket algorithm
- Sliding window tracking
- Per-user and per-IP limiting
- Thread safety
- Metrics collection
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Configure logging
logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens consumed, False if not enough tokens
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_tokens(self) -> float:
        """Get current number of tokens."""
        with self._lock:
            self._refill()
            return self.tokens


class SlidingWindow:
    """Sliding window implementation for rate limiting."""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window.
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = threading.Lock()
    
    def is_allowed(self) -> bool:
        """
        Check if request is allowed.
        
        Returns:
            True if request allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < now - self.window_size:
                self.requests.popleft()
            
            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            else:
                return False
    
    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window."""
        with self._lock:
            now = time.time()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < now - self.window_size:
                self.requests.popleft()
            
            return max(0, self.max_requests - len(self.requests))
    
    def get_retry_after(self) -> int:
        """Get seconds until next request allowed."""
        with self._lock:
            if not self.requests:
                return 0
            
            now = time.time()
            oldest_request = self.requests[0]
            return max(0, int(self.window_size - (now - oldest_request)) + 1)


class RateLimiterMetrics:
    """Metrics for rate limiter monitoring."""
    
    def __init__(self):
        self.total_requests = 0
        self.allowed_requests = 0
        self.denied_requests = 0
        self.start_time = datetime.now()
        self.per_minute_denials = deque(maxlen=60)  # Track denials per minute
    
    def record_request(self, allowed: bool):
        """Record a request attempt."""
        self.total_requests += 1
        now = datetime.now()
        
        if allowed:
            self.allowed_requests += 1
        else:
            self.denied_requests += 1
            self.per_minute_denials.append(now)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        now = datetime.now()
        uptime = (now - self.start_time).total_seconds()
        
        # Calculate denials in last minute
        recent_denials = sum(
            1 for d in self.per_minute_denials
            if (now - d).total_seconds() <= 60
        )
        
        return {
            "total_requests": self.total_requests,
            "allowed_requests": self.allowed_requests,
            "denied_requests": self.denied_requests,
            "denial_rate": self.denied_requests / max(self.total_requests, 1),
            "denials_per_minute": recent_denials,
            "uptime_seconds": uptime,
            "requests_per_second": self.total_requests / max(uptime, 1)
        }


class RateLimiter:
    """Rate limiter with token bucket and sliding window support."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        window_size: int = 60,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Requests per minute limit
            burst_size: Burst size for token bucket
            window_size: Sliding window size in seconds
            key_prefix: Prefix for rate limit keys
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = window_size
        self.key_prefix = key_prefix
        
        # Token bucket for burst handling
        self.token_bucket = TokenBucket(
            capacity=burst_size,
            refill_rate=requests_per_minute / 60.0
        )
        
        # Sliding window for sustained rate limiting
        self.sliding_window = SlidingWindow(
            window_size=window_size,
            max_requests=requests_per_minute
        )
        
        self.metrics = RateLimiterMetrics()
        self._lock = threading.Lock()
    
    def is_allowed(self, tokens: int = 1) -> bool:
        """
        Check if request is allowed.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if request allowed, False otherwise
        """
        with self._lock:
            # Check both token bucket and sliding window
            token_allowed = self.token_bucket.consume(tokens)
            window_allowed = self.sliding_window.is_allowed()
            
            allowed = token_allowed and window_allowed
            self.metrics.record_request(allowed)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded: tokens={tokens}, token_allowed={token_allowed}, window_allowed={window_allowed}")
            
            return allowed
    
    def check_rate_limit(self, tokens: int = 1) -> Dict[str, Any]:
        """
        Check rate limit and return detailed information.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            Dictionary with rate limit information
        """
        with self._lock:
            allowed = self.is_allowed(tokens)
            
            return {
                "allowed": allowed,
                "tokens_remaining": self.token_bucket.get_tokens(),
                "window_remaining": self.sliding_window.get_remaining_requests(),
                "retry_after": self.sliding_window.get_retry_after() if not allowed else 0,
                "limits": {
                    "requests_per_minute": self.requests_per_minute,
                    "burst_size": self.burst_size,
                    "window_size": self.window_size
                }
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics."""
        return {
            "rate_limiter_metrics": self.metrics.get_metrics(),
            "configuration": {
                "requests_per_minute": self.requests_per_minute,
                "burst_size": self.burst_size,
                "window_size": self.window_size
            }
        }


class RateLimiterManager:
    """Manager for multiple rate limiters."""
    
    def __init__(self):
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
    
    def get_rate_limiter(
        self,
        key: str,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        window_size: int = 60
    ) -> RateLimiter:
        """
        Get or create a rate limiter.
        
        Args:
            key: Rate limiter key
            requests_per_minute: Requests per minute limit
            burst_size: Burst size
            window_size: Window size in seconds
            
        Returns:
            Rate limiter instance
        """
        with self._lock:
            if key not in self._rate_limiters:
                self._rate_limiters[key] = RateLimiter(
                    requests_per_minute=requests_per_minute,
                    burst_size=burst_size,
                    window_size=window_size,
                    key_prefix=key
                )
            
            return self._rate_limiters[key]
    
    def check_rate_limit(self, key: str, tokens: int = 1) -> Dict[str, Any]:
        """
        Check rate limit for a specific key.
        
        Args:
            key: Rate limiter key
            tokens: Number of tokens to consume
            
        Returns:
            Rate limit information
        """
        rate_limiter = self.get_rate_limiter(key)
        return rate_limiter.check_rate_limit(tokens)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all rate limiters."""
        with self._lock:
            return {
                key: limiter.get_metrics()
                for key, limiter in self._rate_limiters.items()
            }
    
    def reset_all(self):
        """Reset all rate limiters."""
        with self._lock:
            self._rate_limiters.clear()


# Global rate limiter manager
rate_limiter_manager = RateLimiterManager()


def rate_limit(
    key: str = "default",
    requests_per_minute: int = 60,
    burst_size: int = 10,
    tokens: int = 1
):
    """
    Decorator for adding rate limiting to functions.
    
    Args:
        key: Rate limiter key
        requests_per_minute: Requests per minute limit
        burst_size: Burst size
        tokens: Number of tokens to consume
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            rate_limiter = rate_limiter_manager.get_rate_limiter(
                key=key,
                requests_per_minute=requests_per_minute,
                burst_size=burst_size
            )
            
            if not rate_limiter.is_allowed(tokens):
                retry_after = rate_limiter.sliding_window.get_retry_after()
                raise RateLimitExceeded(
                    f"Rate limit exceeded for {key}. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Export main components
__all__ = ['RateLimiter', 'RateLimiterManager', 'RateLimitExceeded', 'TokenBucket', 'SlidingWindow', 'rate_limit', 'rate_limiter_manager']