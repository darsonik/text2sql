"""Performance benchmarks for the production-ready LangGraph agent.

This script measures:
- Query processing throughput
- Memory usage patterns
- Response time distributions
- Concurrency performance
- Resource utilization under load
"""

import os
import sys
import time
import threading
import psutil
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from text2sql.agents.langgraph_config import AgentConfig, PersistentCheckpointer, ProductionAgent
from text2sql.agents.flow import AgentFlow
from text2sql.agents.agent_tools import QueryValidator, sql_query_tool
from text2sql.utils.circuit_breaker import CircuitBreaker
from text2sql.utils.rate_limiter import RateLimiter


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_rps: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: List[str]


class PerformanceBenchmark:
    """Performance benchmark suite for the production agent."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.test_queries = [
            "What is the average income in cities?",
            "Show me cities with population over 1 million",
            "Compare income levels across different regions",
            "What is the median income in urban areas?",
            "List cities with highest income growth",
            "Show income distribution by city size",
            "What is the average income in coastal cities?",
            "Compare rural vs urban income levels",
            "Show income trends over time",
            "List top 10 cities by average income"
        ]
        
        self.memory_monitor = None
        self.cpu_monitor = None
        self.monitoring_active = False
    
    def start_monitoring(self):
        """Start system resource monitoring."""
        self.monitoring_active = True
        self.memory_samples = []
        self.cpu_samples = []
        
        def monitor_resources():
            while self.monitoring_active:
                try:
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    cpu_percent = process.cpu_percent(interval=0.1)
                    
                    self.memory_samples.append(memory_mb)
                    self.cpu_samples.append(cpu_percent)
                    
                    time.sleep(0.1)
                except Exception:
                    break
        
        self.monitor_thread = threading.Thread(target=monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system resource monitoring."""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
    
    def get_resource_stats(self) -> Dict[str, float]:
        """Get resource usage statistics."""
        if not self.memory_samples or not self.cpu_samples:
            return {"memory_mb": 0, "cpu_percent": 0}
        
        return {
            "memory_mb": statistics.mean(self.memory_samples),
            "cpu_percent": statistics.mean(self.cpu_samples)
        }
    
    def benchmark_query_validation(self, num_requests: int = 1000) -> BenchmarkResult:
        """Benchmark query validation performance."""
        print(f"Running query validation benchmark with {num_requests} requests...")
        
        self.start_monitoring()
        response_times = []
        errors = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            query = self.test_queries[i % len(self.test_queries)]
            
            request_start = time.time()
            try:
                result = QueryValidator.validate_query(query)
                if result["valid"]:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
            
            request_end = time.time()
            response_times.append(request_end - request_start)
        
        total_time = time.time() - start_time
        self.stop_monitoring()
        
        resource_stats = self.get_resource_stats()
        
        return BenchmarkResult(
            name="Query Validation",
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18],
            p99_response_time=statistics.quantiles(response_times, n=100)[98],
            throughput_rps=num_requests / total_time,
            memory_usage_mb=resource_stats["memory_mb"],
            cpu_usage_percent=resource_stats["cpu_percent"],
            errors=errors
        )
    
    def benchmark_rate_limiter(self, num_requests: int = 1000) -> BenchmarkResult:
        """Benchmark rate limiter performance."""
        print(f"Running rate limiter benchmark with {num_requests} requests...")
        
        rate_limiter = RateLimiter(requests_per_minute=1000, burst_size=100)
        
        self.start_monitoring()
        response_times = []
        errors = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            request_start = time.time()
            try:
                result = rate_limiter.check_rate_limit()
                if result["allowed"]:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
            
            request_end = time.time()
            response_times.append(request_end - request_start)
        
        total_time = time.time() - start_time
        self.stop_monitoring()
        
        resource_stats = self.get_resource_stats()
        
        return BenchmarkResult(
            name="Rate Limiter",
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18],
            p99_response_time=statistics.quantiles(response_times, n=100)[98],
            throughput_rps=num_requests / total_time,
            memory_usage_mb=resource_stats["memory_mb"],
            cpu_usage_percent=resource_stats["cpu_percent"],
            errors=errors
        )
    
    def benchmark_circuit_breaker(self, num_requests: int = 1000) -> BenchmarkResult:
        """Benchmark circuit breaker performance."""
        print(f"Running circuit breaker benchmark with {num_requests} requests...")
        
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        
        def success_func():
            return "success"
        
        self.start_monitoring()
        response_times = []
        errors = []
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            request_start = time.time()
            try:
                result = circuit_breaker.call(success_func)
                if result == "success":
                    successful += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
            
            request_end = time.time()
            response_times.append(request_end - request_start)
        
        total_time = time.time() - start_time
        self.stop_monitoring()
        
        resource_stats = self.get_resource_stats()
        
        return BenchmarkResult(
            name="Circuit Breaker",
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18],
            p99_response_time=statistics.quantiles(response_times, n=100)[98],
            throughput_rps=num_requests / total_time,
            memory_usage_mb=resource_stats["memory_mb"],
            cpu_usage_percent=resource_stats["cpu_percent"],
            errors=errors
        )
    
    def benchmark_concurrent_load(self, num_workers: int = 10, requests_per_worker: int = 100) -> BenchmarkResult:
        """Benchmark concurrent load performance."""
        print(f"Running concurrent load benchmark with {num_workers} workers...")
        
        rate_limiter = RateLimiter(requests_per_minute=10000, burst_size=1000)
        
        self.start_monitoring()
        response_times = []
        errors = []
        successful = 0
        failed = 0
        
        def worker_task(worker_id: int):
            """Worker task for concurrent testing."""
            worker_times = []
            worker_successful = 0
            worker_failed = 0
            worker_errors = []
            
            for i in range(requests_per_worker):
                query = self.test_queries[i % len(self.test_queries)]
                
                request_start = time.time()
                try:
                    # Test query validation
                    validation_result = QueryValidator.validate_query(query)
                    
                    # Test rate limiter
                    rate_result = rate_limiter.check_rate_limit()
                    
                    if validation_result["valid"] and rate_result["allowed"]:
                        worker_successful += 1
                    else:
                        worker_failed += 1
                        
                except Exception as e:
                    worker_failed += 1
                    worker_errors.append(str(e))
                
                request_end = time.time()
                worker_times.append(request_end - request_start)
            
            return {
                'times': worker_times,
                'successful': worker_successful,
                'failed': worker_failed,
                'errors': worker_errors
            }
        
        start_time = time.time()
        
        # Execute workers concurrently
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]
            
            for future in as_completed(futures):
                result = future.result()
                response_times.extend(result['times'])
                successful += result['successful']
                failed += result['failed']
                errors.extend(result['errors'])
        
        total_time = time.time() - start_time
        self.stop_monitoring()
        
        resource_stats = self.get_resource_stats()
        
        return BenchmarkResult(
            name="Concurrent Load",
            total_requests=num_workers * requests_per_worker,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=statistics.mean(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=statistics.median(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18],
            p99_response_time=statistics.quantiles(response_times, n=100)[98],
            throughput_rps=(num_workers * requests_per_worker) / total_time,
            memory_usage_mb=resource_stats["memory_mb"],
            cpu_usage_percent=resource_stats["cpu_percent"],
            errors=errors
        )
    
    def benchmark_memory_usage(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """Benchmark memory usage patterns over time."""
        print(f"Running memory usage benchmark for {duration_seconds} seconds...")
        
        rate_limiter = RateLimiter(requests_per_minute=1000, burst_size=100)
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        
        def success_func():
            return "success"
        
        memory_samples = []
        cpu_samples = []
        request_count = 0
        
        start_time = time.time()
        self.start_monitoring()
        
        while time.time() - start_time < duration_seconds:
            # Perform various operations
            try:
                QueryValidator.validate_query("What is the average income?")
                rate_limiter.check_rate_limit()
                circuit_breaker.call(success_func)
                request_count += 1
            except Exception:
                pass
            
            time.sleep(0.01)  # Small delay to simulate real usage
        
        self.stop_monitoring()
        
        return {
            "name": "Memory Usage",
            "duration_seconds": duration_seconds,
            "total_requests": request_count,
            "memory_samples": len(self.memory_samples),
            "avg_memory_mb": statistics.mean(self.memory_samples) if self.memory_samples else 0,
            "max_memory_mb": max(self.memory_samples) if self.memory_samples else 0,
            "memory_trend": self._calculate_memory_trend(),
            "avg_cpu_percent": statistics.mean(self.cpu_samples) if self.cpu_samples else 0,
            "max_cpu_percent": max(self.cpu_samples) if self.cpu_samples else 0
        }
    
    def _calculate_memory_trend(self) -> str:
        """Calculate memory usage trend."""
        if len(self.memory_samples) < 10:
            return "insufficient_data"
        
        # Split into first and second half
        mid_point = len(self.memory_samples) // 2
        first_half = self.memory_samples[:mid_point]
        second_half = self.memory_samples[mid_point:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.1:
            return "increasing"
        elif second_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all performance benchmarks."""
        print("Starting comprehensive performance benchmark suite...")
        print("=" * 60)
        
        results = {
            "query_validation": self.benchmark_query_validation(),
            "rate_limiter": self.benchmark_rate_limiter(),
            "circuit_breaker": self.benchmark_circuit_breaker(),
            "concurrent_load": self.benchmark_concurrent_load(),
            "memory_usage": self.benchmark_memory_usage()
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """Print benchmark results in a formatted way."""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        
        for name, result in results.items():
            if isinstance(result, BenchmarkResult):
                print(f"\n{name.upper()} BENCHMARK:")
                print(f"  Total Requests: {result.total_requests:,}")
                print(f"  Success Rate: {(result.successful_requests/result.total_requests)*100:.1f}%")
                print(f"  Average Response Time: {result.avg_response_time*1000:.2f}ms")
                print(f"  P95 Response Time: {result.p95_response_time*1000:.2f}ms")
                print(f"  P99 Response Time: {result.p99_response_time*1000:.2f}ms")
                print(f"  Throughput: {result.throughput_rps:.1f} RPS")
                print(f"  Memory Usage: {result.memory_usage_mb:.1f} MB")
                print(f"  CPU Usage: {result.cpu_usage_percent:.1f}%")
                if result.errors:
                    print(f"  Errors: {len(result.errors)}")
            else:
                print(f"\n{name.upper()} BENCHMARK:")
                for key, value in result.items():
                    if isinstance(value, float):
                        print(f"  {key.replace('_', ' ').title()}: {value:.2f}")
                    else:
                        print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "=" * 60)
        print("BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Calculate overall metrics
        total_requests = sum(r.total_requests for r in results.values() if isinstance(r, BenchmarkResult))
        total_successful = sum(r.successful_requests for r in results.values() if isinstance(r, BenchmarkResult))
        avg_throughput = statistics.mean([r.throughput_rps for r in results.values() if isinstance(r, BenchmarkResult)])
        avg_memory = statistics.mean([r.memory_usage_mb for r in results.values() if isinstance(r, BenchmarkResult)])
        
        print(f"Total Requests Across All Benchmarks: {total_requests:,}")
        print(f"Overall Success Rate: {(total_successful/total_requests)*100:.1f}%")
        print(f"Average Throughput: {avg_throughput:.1f} RPS")
        print(f"Average Memory Usage: {avg_memory:.1f} MB")
        
        print("\nPerformance Recommendations:")
        print("- Monitor memory usage in production")
        print("- Set appropriate rate limits based on load")
        print("- Tune circuit breaker thresholds for your use case")
        print("- Consider horizontal scaling for high-throughput scenarios")


def main():
    """Main function to run performance benchmarks."""
    print("Production Agent Performance Benchmark Suite")
    print("=" * 60)
    
    benchmark = PerformanceBenchmark()
    
    try:
        # Run all benchmarks
        results = benchmark.run_all_benchmarks()
        
        # Print results
        benchmark.print_results(results)
        
        # Save results to file
        import json
        with open('benchmark_results.json', 'w') as f:
            # Convert BenchmarkResult to dict for JSON serialization
            serializable_results = {}
            for name, result in results.items():
                if isinstance(result, BenchmarkResult):
                    serializable_results[name] = {
                        "name": result.name,
                        "total_requests": result.total_requests,
                        "successful_requests": result.successful_requests,
                        "failed_requests": result.failed_requests,
                        "avg_response_time": result.avg_response_time,
                        "min_response_time": result.min_response_time,
                        "max_response_time": result.max_response_time,
                        "p50_response_time": result.p50_response_time,
                        "p95_response_time": result.p95_response_time,
                        "p99_response_time": result.p99_response_time,
                        "throughput_rps": result.throughput_rps,
                        "memory_usage_mb": result.memory_usage_mb,
                        "cpu_usage_percent": result.cpu_usage_percent,
                        "errors": result.errors
                    }
                else:
                    serializable_results[name] = result
            
            json.dump(serializable_results, f, indent=2)
        
        print(f"\nResults saved to benchmark_results.json")
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\nError running benchmarks: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()