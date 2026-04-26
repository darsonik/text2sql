"""Circuit breaker implementation for external dependencies.

This module provides enterprise-grade circuit breaker functionality with:
- State management (closed, open, half-open)
- Failure threshold detection
- Recovery time tracking
- Thread safety
- Metrics collection
"""

import time
import threading
import logging
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.state_changes = 0
        self.total_calls = 0
        self.start_time = datetime.now()
    
    def record_success(self):
        """Record a successful call."""
        self.success_count += 1
        self.total_calls += 1
        self.last_success_time = datetime.now()
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.total_calls += 1
        self.last_failure_time = datetime.now()
    
    def record_state_change(self):
        """Record a state change."""
        self.state_changes += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        failure_rate = self.failure_count / max(self.total_calls, 1)
        
        return {
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "failure_rate": failure_rate,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "state_changes": self.state_changes,
            "uptime_seconds": uptime
        }


class CircuitBreaker:
    """Thread-safe circuit breaker for protecting external dependencies."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "CircuitBreaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open state
            expected_exception: Exception type to catch
            name: Name for logging and identification
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self._state = CircuitBreakerState.CLOSED
        self._last_failure_time = None
        self._lock = threading.RLock()
        self._metrics = CircuitBreakerMetrics()
        
        logger.info(f"Initialized circuit breaker '{name}' with threshold {failure_threshold} and timeout {recovery_timeout}s")
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current state."""
        with self._lock:
            return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"[{self.name}] Circuit entering half-open state for recovery test")
                    self._transition_to(CircuitBreakerState.HALF_OPEN)
                else:
                    logger.warning(f"[{self.name}] Circuit is open, rejecting call")
                    raise Exception(f"Circuit breaker '{self.name}' is open")
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Record success
                self._metrics.record_success()
                
                # If we were in half-open state, close the circuit
                if self._state == CircuitBreakerState.HALF_OPEN:
                    logger.info(f"[{self.name}] Recovery test successful, closing circuit")
                    self._transition_to(CircuitBreakerState.CLOSED)
                
                return result
                
            except self.expected_exception as e:
                # Record failure
                self._metrics.record_failure()
                self._last_failure_time = datetime.now()
                
                logger.error(f"[{self.name}] Function call failed: {e}")
                
                # Check if we should open the circuit
                if self._metrics.failure_count >= self.failure_threshold:
                    logger.warning(f"[{self.name}] Failure threshold reached, opening circuit")
                    self._transition_to(CircuitBreakerState.OPEN)
                
                # Re-raise the exception
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
        
        time_since_failure = (datetime.now() - self._last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout
    
    def _transition_to(self, new_state: CircuitBreakerState):
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._metrics.record_state_change()
        
        logger.info(f"[{self.name}] State transition: {old_state.value} -> {new_state.value}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        with self._lock:
            metrics = self._metrics.get_metrics()
            metrics.update({
                "state": self._state.value,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
            })
            return metrics
    
    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            logger.info(f"[{self.name}] Manual reset requested")
            self._transition_to(CircuitBreakerState.CLOSED)
            self._metrics = CircuitBreakerMetrics()
            self._last_failure_time = None
    
    def force_open(self):
        """Force the circuit breaker to open state."""
        with self._lock:
            logger.warning(f"[{self.name}] Force opening circuit")
            self._transition_to(CircuitBreakerState.OPEN)
            self._last_failure_time = datetime.now()


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            recovery_timeout: Recovery timeout in seconds
            expected_exception: Exception type to catch
            
        Returns:
            Circuit breaker instance
        """
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    expected_exception=expected_exception,
                    name=name
                )
            
            return self._circuit_breakers[name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        with self._lock:
            return {
                name: cb.get_metrics()
                for name, cb in self._circuit_breakers.items()
            }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for name, cb in self._circuit_breakers.items():
                cb.reset()
    
    def force_open_all(self):
        """Force open all circuit breakers."""
        with self._lock:
            for name, cb in self._circuit_breakers.items():
                cb.force_open()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def with_circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator for adding circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures before opening
        recovery_timeout: Recovery timeout in seconds
        expected_exception: Exception type to catch
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cb = circuit_breaker_manager.get_circuit_breaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception
            )
            return cb.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Export main components
__all__ = ['CircuitBreaker', 'CircuitBreakerState', 'CircuitBreakerManager', 'CircuitBreakerMetrics', 'with_circuit_breaker', 'circuit_breaker_manager']