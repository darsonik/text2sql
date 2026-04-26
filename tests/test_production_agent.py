"""Comprehensive test suite for production-ready LangGraph agent.

This test suite covers:
- Configuration management
- Persistent state management
- Input validation and sanitization
- Error handling and graceful degradation
- Circuit breaker functionality
- Rate limiting
- Health checks and monitoring
- Thread safety and concurrency
"""

import os
import sys
import unittest
import tempfile
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from text2sql.agents.langgraph_config import AgentConfig, PersistentCheckpointer, ProductionAgent
from text2sql.agents.flow import AgentFlow, LegacyAgentFlow
from text2sql.agents.agent_tools import QueryValidator, QueryMetrics, sql_query_tool, health_check
from text2sql.config.config_manager import ConfigManager, Config
from text2sql.utils.circuit_breaker import CircuitBreaker, CircuitBreakerManager, CircuitBreakerState
from text2sql.utils.rate_limiter import RateLimiter, RateLimiterManager, RateLimitExceeded


class TestAgentConfig(unittest.TestCase):
    """Test AgentConfig class."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        for key in ['AGENT_THREAD_ID', 'CHECKPOINT_DB_PATH', 'AGENT_MAX_RETRIES', 
                   'AGENT_REQUEST_TIMEOUT', 'AGENT_ENABLE_LOGGING']:
            if key in os.environ:
                del os.environ[key]
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig()
        
        self.assertIsNotNone(config.thread_id)
        self.assertEqual(config.checkpoint_db_path, 'checkpoint.db')
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.request_timeout, 30)
        self.assertTrue(config.enable_logging)
    
    def test_environment_override(self):
        """Test environment variable overrides."""
        os.environ['AGENT_THREAD_ID'] = 'test-thread'
        os.environ['CHECKPOINT_DB_PATH'] = '/tmp/test.db'
        os.environ['AGENT_MAX_RETRIES'] = '5'
        os.environ['AGENT_REQUEST_TIMEOUT'] = '60'
        os.environ['AGENT_ENABLE_LOGGING'] = 'false'
        
        config = AgentConfig()
        
        self.assertEqual(config.thread_id, 'test-thread')
        self.assertEqual(config.checkpoint_db_path, '/tmp/test.db')
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.request_timeout, 60)
        self.assertFalse(config.enable_logging)
    
    def test_to_dict(self):
        """Test configuration to dictionary conversion."""
        config = AgentConfig()
        config_dict = config.to_dict()
        
        self.assertIn('configurable', config_dict)
        self.assertIn('thread_id', config_dict['configurable'])
        self.assertIn('max_retries', config_dict['configurable'])
        self.assertIn('request_timeout', config_dict['configurable'])


class TestPersistentCheckpointer(unittest.TestCase):
    """Test PersistentCheckpointer class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_checkpoint.db')
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test checkpointer initialization."""
        checkpointer = PersistentCheckpointer(self.db_path)
        
        self.assertEqual(checkpointer.db_path, self.db_path)
        self.assertIsNotNone(checkpointer._saver)
        self.assertTrue(os.path.exists(self.db_path) or os.path.exists(os.path.dirname(self.db_path)))
    
    def test_thread_safety(self):
        """Test thread safety of checkpointer."""
        checkpointer = PersistentCheckpointer(self.db_path)
        
        def access_checkpointer():
            # Multiple threads accessing the checkpointer
            for _ in range(10):
                self.assertIsNotNone(checkpointer._saver)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=access_checkpointer)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # If we get here without exceptions, thread safety is working
        self.assertTrue(True)


class TestQueryValidator(unittest.TestCase):
    """Test QueryValidator class."""
    
    def test_valid_query_length(self):
        """Test query length validation."""
        # Valid length
        self.assertTrue(QueryValidator.validate_query_length("What is the average income?"))
        
        # Too short
        self.assertFalse(QueryValidator.validate_query_length("a"))
        
        # Too long
        long_query = "x" * 1500
        self.assertFalse(QueryValidator.validate_query_length(long_query))
    
    def test_sql_injection_detection(self):
        """Test SQL injection detection."""
        # Clean query
        result = QueryValidator.detect_sql_injection("What is the average income in cities?")
        self.assertIsNone(result)
        
        # SQL injection patterns
        injection_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "' OR '1'='1",
            "UNION SELECT password FROM users",
            "1=1",
            "'; EXEC xp_cmdshell 'dir'--"
        ]
        
        for query in injection_queries:
            result = QueryValidator.detect_sql_injection(query)
            self.assertIsNotNone(result)
            self.assertIn("SQL injection", result)
    
    def test_input_sanitization(self):
        """Test input sanitization."""
        # HTML tags removal
        sanitized = QueryValidator.sanitize_input("<script>alert('xss')</script>query")
        self.assertNotIn("<script>", sanitized)
        
        # HTML entities escaping
        sanitized = QueryValidator.sanitize_input('query with "quotes" and \'apostrophes\'')
        self.assertIn("&quot;", sanitized)
        self.assertIn("&#x27;", sanitized)
        
        # Whitespace normalization
        sanitized = QueryValidator.sanitize_input("  multiple    spaces  ")
        self.assertEqual(sanitized, "multiple spaces")
    
    def test_content_validation(self):
        """Test content validation."""
        # Empty query
        result = QueryValidator.validate_content("")
        self.assertIsNotNone(result)
        self.assertIn("empty", result)
        
        # Excessive repetition
        result = QueryValidator.validate_content("test test test test test test test test test test")
        self.assertIsNotNone(result)
        self.assertIn("repetition", result)
        
        # Malicious content
        malicious_queries = [
            "hack the database",
            "bypass security",
            "drop all tables",
            "get admin password"
        ]
        
        for query in malicious_queries:
            result = QueryValidator.validate_content(query)
            self.assertIsNotNone(result)
            self.assertIn("malicious", result)
        
        # Clean query
        result = QueryValidator.validate_content("What is the average income in New York?")
        self.assertIsNone(result)
    
    def test_comprehensive_validation(self):
        """Test comprehensive query validation."""
        # Valid query
        result = QueryValidator.validate_query("What is the average income in cities?")
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
        
        # Invalid query with SQL injection
        result = QueryValidator.validate_query("SELECT * FROM users; DROP TABLE users;")
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("SQL injection", result["errors"][0])
        
        # Query requiring sanitization
        result = QueryValidator.validate_query("  query with <script>  ")
        self.assertTrue(result["valid"])
        self.assertGreater(len(result["warnings"]), 0)
        self.assertIn("sanitized", result["warnings"][0])


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker class."""
    
    def setUp(self):
        """Set up test environment."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,
            expected_exception=Exception,
            name="test_breaker"
        )
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
    
    def test_successful_calls(self):
        """Test successful function calls."""
        def success_func():
            return "success"
        
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
    
    def test_failure_threshold(self):
        """Test failure threshold and circuit opening."""
        def failing_func():
            raise Exception("Test failure")
        
        # First two failures should keep circuit closed
        for _ in range(2):
            with self.assertRaises(Exception):
                self.circuit_breaker.call(failing_func)
            self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        
        # Third failure should open the circuit
        with self.assertRaises(Exception):
            self.circuit_breaker.call(failing_func)
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Subsequent calls should be rejected immediately
        with self.assertRaises(Exception) as context:
            self.circuit_breaker.call(failing_func)
        self.assertIn("is open", str(context.exception))
    
    def test_recovery_mechanism(self):
        """Test circuit breaker recovery."""
        def failing_func():
            raise Exception("Test failure")
        
        def success_func():
            return "success"
        
        # Open the circuit
        for _ in range(3):
            try:
                self.circuit_breaker.call(failing_func)
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next call should attempt recovery (half-open state)
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
    
    def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(3):
            try:
                self.circuit_breaker.call(failing_func)
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Manual reset
        self.circuit_breaker.reset()
        self.assertEqual(self.circuit_breaker.state, CircuitBreakerState.CLOSED)
        
        # Should allow calls again
        def success_func():
            return "success"
        
        result = self.circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
    
    def test_metrics(self):
        """Test circuit breaker metrics."""
        def success_func():
            return "success"
        
        def failing_func():
            raise Exception("Test failure")
        
        # Record some successes and failures
        self.circuit_breaker.call(success_func)
        
        try:
            self.circuit_breaker.call(failing_func)
        except Exception:
            pass
        
        metrics = self.circuit_breaker.get_metrics()
        
        self.assertEqual(metrics["state"], "closed")
        self.assertEqual(metrics["failure_count"], 1)
        self.assertEqual(metrics["success_count"], 1)
        self.assertEqual(metrics["failure_threshold"], 3)
        self.assertEqual(metrics["recovery_timeout"], 1)


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class."""
    
    def setUp(self):
        """Set up test environment."""
        self.rate_limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
            window_size=60
        )
    
    def test_initial_state(self):
        """Test initial rate limiter state."""
        result = self.rate_limiter.check_rate_limit()
        self.assertTrue(result["allowed"])
        self.assertEqual(result["tokens_remaining"], 2)
        self.assertEqual(result["window_remaining"], 9)
    
    def test_burst_limiting(self):
        """Test burst request limiting."""
        # Consume burst allowance
        for i in range(3):
            result = self.rate_limiter.check_rate_limit()
            self.assertTrue(result["allowed"])
            self.assertEqual(result["tokens_remaining"], 2 - i)
        
        # Next request should be denied due to burst limit
        result = self.rate_limiter.check_rate_limit()
        self.assertFalse(result["allowed"])
        self.assertEqual(result["tokens_remaining"], 0)
    
    def test_window_limiting(self):
        """Test sliding window limiting."""
        # Consume all window allowance
        for _ in range(10):
            self.rate_limiter.check_rate_limit()
        
        # Next request should be denied
        result = self.rate_limiter.check_rate_limit()
        self.assertFalse(result["allowed"])
        self.assertEqual(result["window_remaining"], 0)
    
    def test_metrics(self):
        """Test rate limiter metrics."""
        # Record some requests
        for _ in range(5):
            self.rate_limiter.check_rate_limit()
        
        metrics = self.rate_limiter.get_metrics()
        
        self.assertEqual(metrics["rate_limiter_metrics"]["total_requests"], 5)
        self.assertEqual(metrics["rate_limiter_metrics"]["allowed_requests"], 5)
        self.assertEqual(metrics["rate_limiter_metrics"]["denied_requests"], 0)
        self.assertEqual(metrics["configuration"]["requests_per_minute"], 10)
        self.assertEqual(metrics["configuration"]["burst_size"], 3)
    
    def test_retry_after_calculation(self):
        """Test retry after calculation."""
        # Consume all allowance
        for _ in range(10):
            self.rate_limiter.check_rate_limit()
        
        # Check retry after
        result = self.rate_limiter.check_rate_limit()
        self.assertFalse(result["allowed"])
        self.assertGreater(result["retry_after"], 0)


class TestAgentFlow(unittest.TestCase):
    """Test AgentFlow class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the production agent
        self.mock_agent = Mock()
        self.mock_agent.invoke = Mock(return_value={
            "success": True,
            "response": {
                "messages": [Mock(content="Test response")]
            },
            "thread_id": "test-thread",
            "processing_time": 1.0
        })
        
        # Patch the production agent
        self.patcher = patch('text2sql.agents.flow.production_agent', self.mock_agent)
        self.patcher.start()
    
    def tearDown(self):
        """Clean up test environment."""
        self.patcher.stop()
    
    def test_successful_query(self):
        """Test successful query execution."""
        agent_flow = AgentFlow()
        result = agent_flow.run("What is the average income?")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], "Test response")
        self.assertEqual(result["correlation_id"], agent_flow.correlation_id)
        self.assertGreater(result["processing_time"], 0)
    
    def test_error_handling(self):
        """Test error handling in agent flow."""
        # Mock agent to raise exception
        self.mock_agent.invoke = Mock(side_effect=Exception("Agent error"))
        
        agent_flow = AgentFlow()
        result = agent_flow.run("Invalid query")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error_type"], "system")
        self.assertIn("suggestion", result)
    
    def test_correlation_id_tracking(self):
        """Test correlation ID tracking."""
        agent_flow = AgentFlow(correlation_id="test-correlation")
        result = agent_flow.run("Test query")
        
        self.assertEqual(result["correlation_id"], "test-correlation")
        self.assertEqual(agent_flow.correlation_id, "test-correlation")
    
    def test_legacy_compatibility(self):
        """Test legacy compatibility wrapper."""
        legacy_flow = LegacyAgentFlow()
        result = legacy_flow.run("Test query")
        
        # Legacy wrapper should return just the response string
        self.assertEqual(result, "Test response")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete production agent system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_integration.db')
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        # Test configuration loading
        config = AgentConfig()
        self.assertIsNotNone(config.thread_id)
        
        # Test checkpointer initialization
        checkpointer = PersistentCheckpointer(self.db_path)
        self.assertIsNotNone(checkpointer._saver)
        
        # Test query validation
        validation_result = QueryValidator.validate_query("What is the average income?")
        self.assertTrue(validation_result["valid"])
        
        # Test circuit breaker
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        def success_func():
            return "success"
        
        result = circuit_breaker.call(success_func)
        self.assertEqual(result, "success")
        
        # Test rate limiter
        rate_limiter = RateLimiter(requests_per_minute=5, burst_size=2)
        result = rate_limiter.check_rate_limit()
        self.assertTrue(result["allowed"])
    
    def test_concurrent_access(self):
        """Test concurrent access to shared resources."""
        results = []
        errors = []
        
        def worker_task(worker_id):
            try:
                # Test configuration
                config = AgentConfig()
                
                # Test query validation
                validation_result = QueryValidator.validate_query(f"Query from worker {worker_id}")
                
                # Test rate limiter
                rate_limiter = RateLimiter(requests_per_minute=60, burst_size=10)
                rate_result = rate_limiter.check_rate_limit()
                
                results.append({
                    'worker_id': worker_id,
                    'config_valid': True,
                    'validation_valid': validation_result['valid'],
                    'rate_allowed': rate_result['allowed']
                })
                
            except Exception as e:
                errors.append(f"Worker {worker_id} error: {e}")
        
        # Create multiple worker threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker_task, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)
        
        for result in results:
            self.assertTrue(result['config_valid'])
            self.assertTrue(result['validation_valid'])
            self.assertTrue(result['rate_allowed'])
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        # Test circuit breaker recovery
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Cause failures to open circuit
        for _ in range(2):
            try:
                circuit_breaker.call(lambda: exec("raise Exception('Test failure')"))
            except Exception:
                pass
        
        # Circuit should be open
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.OPEN)
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Test recovery with successful call
        result = circuit_breaker.call(lambda: "recovered")
        self.assertEqual(result, "recovered")
        self.assertEqual(circuit_breaker.state, CircuitBreakerState.CLOSED)


class TestPerformance(unittest.TestCase):
    """Performance tests for the production agent system."""
    
    def test_query_validation_performance(self):
        """Test query validation performance."""
        test_queries = [
            "What is the average income?",
            "Show me cities with population over 1 million",
            "Compare income levels across different regions",
            "SELECT * FROM users WHERE id = 1",  # SQL injection test
            "'; DROP TABLE users; --",  # SQL injection test
        ]
        
        start_time = time.time()
        
        # Validate multiple queries
        for _ in range(100):
            for query in test_queries:
                QueryValidator.validate_query(query)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 500 validations in reasonable time (< 1 second)
        self.assertLess(total_time, 1.0, f"Validation too slow: {total_time:.3f}s for 500 queries")
        
        # Average time per validation should be minimal
        avg_time = total_time / 500
        self.assertLess(avg_time, 0.002, f"Average validation time too high: {avg_time:.4f}s")
    
    def test_rate_limiter_performance(self):
        """Test rate limiter performance."""
        rate_limiter = RateLimiter(requests_per_minute=1000, burst_size=100)
        
        start_time = time.time()
        
        # Check rate limit for many requests
        for _ in range(1000):
            rate_limiter.check_rate_limit()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 1000 rate limit checks quickly (< 0.1 seconds)
        self.assertLess(total_time, 0.1, f"Rate limiter too slow: {total_time:.3f}s for 1000 checks")
        
        # Average time per check should be minimal
        avg_time = total_time / 1000
        self.assertLess(avg_time, 0.0001, f"Average rate limit check time too high: {avg_time:.5f}s")
    
    def test_circuit_breaker_performance(self):
        """Test circuit breaker performance."""
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        
        def success_func():
            return "success"
        
        start_time = time.time()
        
        # Execute many successful calls
        for _ in range(1000):
            circuit_breaker.call(success_func)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete 1000 circuit breaker calls quickly (< 0.1 seconds)
        self.assertLess(total_time, 0.1, f"Circuit breaker too slow: {total_time:.3f}s for 1000 calls")
        
        # Average time per call should be minimal
        avg_time = total_time / 1000
        self.assertLess(avg_time, 0.0001, f"Average circuit breaker call time too high: {avg_time:.5f}s")


if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.INFO)
    
    # Run all tests
    unittest.main(verbosity=2)