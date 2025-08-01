"""
Performance and Load Test Suite for HoopHead Multi-Sport API Platform.
Benchmarks API client, caching, authentication, and overall system performance.
"""
import asyncio
import pytest
import sys
import os
import time
import statistics
import psutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import aiohttp

# Add backend source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

# Import system components
from adapters.external.ball_dont_lie_client import BallDontLieClient, Sport
from adapters.external.auth_manager import AuthenticationManager, APITier
from adapters.cache import multi_cache, cache_warmer
from domain.services.player_service import PlayerService
from domain.services.team_service import TeamService


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test scenario."""
    test_name: str
    total_duration_ms: float
    min_latency_ms: float
    max_latency_ms: float
    avg_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_requests_per_second: float
    success_rate: float
    cache_hit_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: List[str]


@dataclass
class LoadTestResult:
    """Result of a load test scenario."""
    scenario_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    duration_seconds: float
    throughput_rps: float
    latency_metrics: PerformanceMetrics
    resource_usage: Dict[str, Any]


class PerformanceTestSuite:
    """
    Comprehensive performance test suite for HoopHead platform.
    
    Test Categories:
    1. Cache Performance - Redis and file cache latency
    2. API Client Performance - Request/response timing
    3. Authentication Performance - Key validation and rate limiting
    4. Domain Services Performance - Model conversion and business logic
    5. Load Testing - Concurrent request handling
    6. Memory and CPU Profiling - Resource usage analysis
    """
    
    def __init__(self, use_real_api: bool = False):
        """Initialize performance test suite."""
        self.use_real_api = use_real_api
        self.auth_manager = None
        self.test_api_key_id = None
        self.performance_results = []
        
        print(f"⚡ Performance Test Suite initialized (Real API: {'✅' if use_real_api else '❌'})")
    
    async def setup_performance_environment(self):
        """Set up performance testing environment."""
        print("\n🔧 Setting up performance test environment...")
        
        # Initialize authentication
        self.auth_manager = AuthenticationManager()
        
        if not self.use_real_api:
            # Add test API key
            self.test_api_key_id = self.auth_manager.add_api_key(
                "perf_test_goat_key_123", APITier.GOAT, "Performance Test Key"
            )
        else:
            api_key = os.getenv('BALLDONTLIE_API_KEY')
            if api_key:
                self.test_api_key_id = self.auth_manager.add_api_key(api_key, APITier.GOAT, "Real API Performance Test")
        
        print(f"   ✅ Authentication setup complete")
    
    async def test_cache_performance(self) -> PerformanceMetrics:
        """Test cache system performance."""
        test_name = "Cache Performance Benchmark"
        print(f"\n💾 Running {test_name}...")
        
        latencies = []
        cache_hits = 0
        total_operations = 100
        errors = []
        
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        overall_start = time.time()
        
        try:
            # Test cache write and read performance
            test_data = {"teams": [{"id": i, "name": f"Team {i}"} for i in range(50)]}
            
            for i in range(total_operations):
                # Write operation
                write_start = time.time()
                redis_success, file_success = await multi_cache.set(
                    Sport.NBA, f"performance_test_{i}", test_data, 
                    params={"iteration": i}, tier=APITier.GOAT
                )
                write_end = time.time()
                write_latency = (write_end - write_start) * 1000
                
                # Read operation
                read_start = time.time()
                cached_data, hit_info = await multi_cache.get(
                    Sport.NBA, f"performance_test_{i}", 
                    params={"iteration": i}, tier=APITier.GOAT
                )
                read_end = time.time()
                read_latency = (read_end - read_start) * 1000
                
                # Track metrics
                latencies.append(read_latency)
                if hit_info.hit:
                    cache_hits += 1
                
                # Log performance every 25 iterations
                if (i + 1) % 25 == 0:
                    print(f"      Progress: {i+1}/{total_operations} operations ({read_latency:.2f}ms)")
        
        except Exception as e:
            errors.append(f"Cache performance test error: {str(e)}")
        
        overall_end = time.time()
        total_duration_ms = (overall_end - overall_start) * 1000
        
        end_memory = self._get_memory_usage()
        end_cpu = self._get_cpu_usage()
        
        # Calculate metrics
        if latencies:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=min(latencies),
                max_latency_ms=max(latencies),
                avg_latency_ms=statistics.mean(latencies),
                median_latency_ms=statistics.median(latencies),
                p95_latency_ms=self._percentile(latencies, 95),
                p99_latency_ms=self._percentile(latencies, 99),
                throughput_requests_per_second=total_operations / (total_duration_ms / 1000),
                success_rate=(total_operations - len(errors)) / total_operations * 100,
                cache_hit_rate=cache_hits / total_operations * 100,
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=end_cpu - start_cpu,
                errors=errors
            )
        else:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=0, max_latency_ms=0, avg_latency_ms=0,
                median_latency_ms=0, p95_latency_ms=0, p99_latency_ms=0,
                throughput_requests_per_second=0, success_rate=0,
                cache_hit_rate=0, memory_usage_mb=0, cpu_usage_percent=0,
                errors=errors
            )
        
        print(f"   📊 Results: {metrics.avg_latency_ms:.2f}ms avg, {metrics.cache_hit_rate:.1f}% hit rate")
        return metrics
    
    async def test_api_client_performance(self) -> PerformanceMetrics:
        """Test API client performance."""
        test_name = "API Client Performance Benchmark"
        print(f"\n🌐 Running {test_name}...")
        
        latencies = []
        successful_requests = 0
        total_requests = 20  # Reduced for performance testing
        errors = []
        cache_hits = 0
        
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        overall_start = time.time()
        
        try:
            async with BallDontLieClient(key_id=self.test_api_key_id) as client:
                
                # Test different endpoints for performance
                test_scenarios = [
                    (Sport.NBA, "teams", {}),
                    (Sport.NFL, "teams", {}),
                    (Sport.MLB, "teams", {}),
                    (Sport.NHL, "teams", {}),
                ]
                
                for i in range(total_requests):
                    scenario = test_scenarios[i % len(test_scenarios)]
                    sport, endpoint_type, params = scenario
                    
                    request_start = time.time()
                    
                    try:
                        if endpoint_type == "teams":
                            response = await client.get_teams(sport)
                        
                        request_end = time.time()
                        latency = (request_end - request_start) * 1000
                        latencies.append(latency)
                        
                        if response.success:
                            successful_requests += 1
                            if hasattr(response, 'meta') and response.meta.get('cached'):
                                cache_hits += 1
                        
                        # Log progress
                        if (i + 1) % 5 == 0:
                            print(f"      Progress: {i+1}/{total_requests} requests ({latency:.0f}ms)")
                    
                    except Exception as e:
                        errors.append(f"Request {i+1} error: {str(e)}")
                        latencies.append(0)  # Add zero latency for failed requests
                    
                    # Small delay to avoid overwhelming the API
                    if self.use_real_api:
                        await asyncio.sleep(0.1)
        
        except Exception as e:
            errors.append(f"API client performance test error: {str(e)}")
        
        overall_end = time.time()
        total_duration_ms = (overall_end - overall_start) * 1000
        
        end_memory = self._get_memory_usage()
        end_cpu = self._get_cpu_usage()
        
        # Calculate metrics
        valid_latencies = [l for l in latencies if l > 0]
        if valid_latencies:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=min(valid_latencies),
                max_latency_ms=max(valid_latencies),
                avg_latency_ms=statistics.mean(valid_latencies),
                median_latency_ms=statistics.median(valid_latencies),
                p95_latency_ms=self._percentile(valid_latencies, 95),
                p99_latency_ms=self._percentile(valid_latencies, 99),
                throughput_requests_per_second=successful_requests / (total_duration_ms / 1000),
                success_rate=successful_requests / total_requests * 100,
                cache_hit_rate=cache_hits / successful_requests * 100 if successful_requests > 0 else 0,
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=end_cpu - start_cpu,
                errors=errors
            )
        else:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=0, max_latency_ms=0, avg_latency_ms=0,
                median_latency_ms=0, p95_latency_ms=0, p99_latency_ms=0,
                throughput_requests_per_second=0, success_rate=0,
                cache_hit_rate=0, memory_usage_mb=0, cpu_usage_percent=0,
                errors=errors
            )
        
        print(f"   📊 Results: {metrics.avg_latency_ms:.0f}ms avg, {metrics.success_rate:.1f}% success rate")
        return metrics
    
    async def test_authentication_performance(self) -> PerformanceMetrics:
        """Test authentication system performance."""
        test_name = "Authentication Performance Benchmark"
        print(f"\n🔐 Running {test_name}...")
        
        latencies = []
        successful_operations = 0
        total_operations = 1000
        errors = []
        
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        
        overall_start = time.time()
        
        try:
            # Test various authentication operations
            for i in range(total_operations):
                operation_start = time.time()
                
                try:
                    if i % 3 == 0:
                        # Test API key validation
                        is_valid, _, tier = self.auth_manager.validate_api_key(f"test_key_{i}")
                    elif i % 3 == 1:
                        # Test rate limit checking
                        allowed, info = await self.auth_manager.check_rate_limit(self.test_api_key_id)
                    else:
                        # Test usage statistics
                        stats = self.auth_manager.get_usage_stats(self.test_api_key_id)
                    
                    successful_operations += 1
                
                except Exception as e:
                    errors.append(f"Auth operation {i+1} error: {str(e)}")
                
                operation_end = time.time()
                latency = (operation_end - operation_start) * 1000
                latencies.append(latency)
                
                # Log progress
                if (i + 1) % 200 == 0:
                    print(f"      Progress: {i+1}/{total_operations} auth operations ({latency:.3f}ms)")
        
        except Exception as e:
            errors.append(f"Authentication performance test error: {str(e)}")
        
        overall_end = time.time()
        total_duration_ms = (overall_end - overall_start) * 1000
        
        end_memory = self._get_memory_usage()
        end_cpu = self._get_cpu_usage()
        
        # Calculate metrics
        if latencies:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=min(latencies),
                max_latency_ms=max(latencies),
                avg_latency_ms=statistics.mean(latencies),
                median_latency_ms=statistics.median(latencies),
                p95_latency_ms=self._percentile(latencies, 95),
                p99_latency_ms=self._percentile(latencies, 99),
                throughput_requests_per_second=successful_operations / (total_duration_ms / 1000),
                success_rate=successful_operations / total_operations * 100,
                cache_hit_rate=0,  # Not applicable for auth
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=end_cpu - start_cpu,
                errors=errors
            )
        else:
            metrics = PerformanceMetrics(
                test_name=test_name,
                total_duration_ms=total_duration_ms,
                min_latency_ms=0, max_latency_ms=0, avg_latency_ms=0,
                median_latency_ms=0, p95_latency_ms=0, p99_latency_ms=0,
                throughput_requests_per_second=0, success_rate=0,
                cache_hit_rate=0, memory_usage_mb=0, cpu_usage_percent=0,
                errors=errors
            )
        
        print(f"   📊 Results: {metrics.avg_latency_ms:.3f}ms avg, {metrics.throughput_requests_per_second:.0f} ops/sec")
        return metrics
    
    async def test_concurrent_load(self, concurrent_users: int = 5) -> LoadTestResult:
        """Test concurrent load handling."""
        scenario_name = f"Concurrent Load Test ({concurrent_users} users)"
        print(f"\n🚀 Running {scenario_name}...")
        
        async def simulate_user_session():
            """Simulate a single user session."""
            session_requests = 0
            session_successes = 0
            session_latencies = []
            
            try:
                async with BallDontLieClient(key_id=self.test_api_key_id) as client:
                    # Each user makes 5 requests
                    for i in range(5):
                        request_start = time.time()
                        
                        try:
                            sport = [Sport.NBA, Sport.NFL, Sport.MLB, Sport.NHL][i % 4]
                            response = await client.get_teams(sport)
                            
                            request_end = time.time()
                            latency = (request_end - request_start) * 1000
                            session_latencies.append(latency)
                            session_requests += 1
                            
                            if response.success:
                                session_successes += 1
                        
                        except Exception:
                            session_requests += 1
                            session_latencies.append(0)
                        
                        # Small delay between requests
                        await asyncio.sleep(0.1)
            
            except Exception:
                pass
            
            return {
                'requests': session_requests,
                'successes': session_successes,
                'latencies': session_latencies
            }
        
        start_memory = self._get_memory_usage()
        start_cpu = self._get_cpu_usage()
        load_test_start = time.time()
        
        # Run concurrent user sessions
        tasks = [simulate_user_session() for _ in range(concurrent_users)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        load_test_end = time.time()
        duration_seconds = load_test_end - load_test_start
        
        end_memory = self._get_memory_usage()
        end_cpu = self._get_cpu_usage()
        
        # Aggregate results
        total_requests = 0
        successful_requests = 0
        all_latencies = []
        
        for result in session_results:
            if isinstance(result, dict):
                total_requests += result['requests']
                successful_requests += result['successes']
                all_latencies.extend([l for l in result['latencies'] if l > 0])
        
        failed_requests = total_requests - successful_requests
        throughput_rps = successful_requests / duration_seconds if duration_seconds > 0 else 0
        
        # Create latency metrics
        if all_latencies:
            latency_metrics = PerformanceMetrics(
                test_name=f"Load Test Latencies ({concurrent_users} users)",
                total_duration_ms=duration_seconds * 1000,
                min_latency_ms=min(all_latencies),
                max_latency_ms=max(all_latencies),
                avg_latency_ms=statistics.mean(all_latencies),
                median_latency_ms=statistics.median(all_latencies),
                p95_latency_ms=self._percentile(all_latencies, 95),
                p99_latency_ms=self._percentile(all_latencies, 99),
                throughput_requests_per_second=throughput_rps,
                success_rate=successful_requests / total_requests * 100 if total_requests > 0 else 0,
                cache_hit_rate=0,  # Not tracked in load test
                memory_usage_mb=end_memory - start_memory,
                cpu_usage_percent=end_cpu - start_cpu,
                errors=[]
            )
        else:
            latency_metrics = PerformanceMetrics(
                test_name=f"Load Test Latencies ({concurrent_users} users)",
                total_duration_ms=duration_seconds * 1000,
                min_latency_ms=0, max_latency_ms=0, avg_latency_ms=0,
                median_latency_ms=0, p95_latency_ms=0, p99_latency_ms=0,
                throughput_requests_per_second=0, success_rate=0,
                cache_hit_rate=0, memory_usage_mb=0, cpu_usage_percent=0,
                errors=[]
            )
        
        result = LoadTestResult(
            scenario_name=scenario_name,
            concurrent_users=concurrent_users,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            duration_seconds=duration_seconds,
            throughput_rps=throughput_rps,
            latency_metrics=latency_metrics,
            resource_usage={
                'memory_increase_mb': end_memory - start_memory,
                'cpu_usage_change': end_cpu - start_cpu
            }
        )
        
        print(f"   📊 Results: {throughput_rps:.1f} RPS, {latency_metrics.avg_latency_ms:.0f}ms avg latency")
        return result
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a list of values."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    async def run_all_performance_tests(self) -> Dict[str, Any]:
        """Run all performance tests."""
        print("\n" + "="*80)
        print("⚡ HoopHead Performance Test Suite - Benchmarking & Load Testing")
        print("="*80)
        
        await self.setup_performance_environment()
        
        # Run performance tests
        cache_perf = await self.test_cache_performance()
        api_perf = await self.test_api_client_performance()
        auth_perf = await self.test_authentication_performance()
        
        # Run load tests with different concurrent user counts
        load_results = []
        for concurrent_users in [1, 3, 5]:
            load_result = await self.test_concurrent_load(concurrent_users)
            load_results.append(load_result)
        
        self.performance_results = [cache_perf, api_perf, auth_perf]
        
        # Generate comprehensive report
        await self._generate_performance_report(load_results)
        
        return {
            'performance_metrics': self.performance_results,
            'load_test_results': load_results
        }
    
    async def _generate_performance_report(self, load_results: List[LoadTestResult]):
        """Generate comprehensive performance report."""
        print("\n" + "="*80)
        print("📊 PERFORMANCE TEST RESULTS SUMMARY")
        print("="*80)
        
        # Performance metrics summary
        print(f"\n⚡ Performance Metrics:")
        for metrics in self.performance_results:
            print(f"   {metrics.test_name:30} | Avg: {metrics.avg_latency_ms:6.2f}ms | P95: {metrics.p95_latency_ms:6.2f}ms | {metrics.throughput_requests_per_second:6.0f} ops/sec")
        
        # Load test summary
        print(f"\n🚀 Load Test Results:")
        for result in load_results:
            print(f"   {result.concurrent_users:2d} users | {result.throughput_rps:6.1f} RPS | {result.latency_metrics.avg_latency_ms:6.0f}ms avg | {result.successful_requests:3d}/{result.total_requests:3d} success")
        
        # Resource usage
        print(f"\n💾 Resource Usage:")
        for metrics in self.performance_results:
            print(f"   {metrics.test_name:30} | Memory: {metrics.memory_usage_mb:+5.1f}MB | CPU: {metrics.cpu_usage_percent:+5.1f}%")
        
        # Performance insights
        fastest_test = min(self.performance_results, key=lambda m: m.avg_latency_ms)
        highest_throughput = max(self.performance_results, key=lambda m: m.throughput_requests_per_second)
        
        print(f"\n🏆 Performance Highlights:")
        print(f"   Fastest Operation: {fastest_test.test_name} ({fastest_test.avg_latency_ms:.2f}ms)")
        print(f"   Highest Throughput: {highest_throughput.test_name} ({highest_throughput.throughput_requests_per_second:.0f} ops/sec)")
        
        # Load test insights
        if load_results:
            best_load = max(load_results, key=lambda r: r.throughput_rps)
            print(f"   Best Load Performance: {best_load.concurrent_users} users at {best_load.throughput_rps:.1f} RPS")
        
        # Overall assessment
        avg_latency = statistics.mean([m.avg_latency_ms for m in self.performance_results])
        total_throughput = sum([m.throughput_requests_per_second for m in self.performance_results])
        
        print(f"\n📈 Overall Assessment:")
        print(f"   Average Latency: {avg_latency:.2f}ms")
        print(f"   Combined Throughput: {total_throughput:.0f} ops/sec")
        
        if avg_latency < 50:
            print("   🎉 Excellent performance! Your platform is highly optimized.")
        elif avg_latency < 200:
            print("   ✅ Good performance! Your platform meets production standards.")
        else:
            print("   ⚠️  Performance needs attention. Consider optimization.")


async def run_performance_tests(use_real_api: bool = False):
    """
    Run the complete performance test suite.
    
    Args:
        use_real_api: Whether to use real API calls for testing
    """
    suite = PerformanceTestSuite(use_real_api=use_real_api)
    results = await suite.run_all_performance_tests()
    return results


if __name__ == "__main__":
    """Run performance tests when executed directly."""
    import argparse
    
    parser = argparse.ArgumentParser(description="HoopHead Performance Test Suite")
    parser.add_argument("--real-api", action="store_true", 
                       help="Use real API calls for performance testing (requires BALLDONTLIE_API_KEY)")
    
    args = parser.parse_args()
    
    asyncio.run(run_performance_tests(use_real_api=args.real_api)) 