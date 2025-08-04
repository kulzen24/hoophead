#!/usr/bin/env python3
"""
Comprehensive Test Runner for HoopHead Multi-Sport API Platform.
Orchestrates all test suites and provides detailed reporting with coverage analysis.
"""
import asyncio
import argparse
import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import json

# Add backend source to path
from test_utils import setup_test_environment
setup_test_environment()

# Import test suites
try:
    from test_comprehensive_suite import run_comprehensive_test_suite
    from test_end_to_end_workflows import run_end_to_end_tests  
    from test_performance_benchmarks import run_performance_tests
except ImportError as e:
    print(f"Warning: Could not import test suites: {e}")


class ComprehensiveTestRunner:
    """
    Master test runner for HoopHead platform.
    
    Capabilities:
    1. Run all test categories (unit, integration, e2e, performance)
    2. Generate coverage reports
    3. Provide detailed test analytics
    4. Support CI/CD pipeline integration
    5. Benchmark performance over time
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize comprehensive test runner."""
        self.config = config or {}
        self.test_results = {}
        self.start_time = time.time()
        
        # Default configuration
        self.default_config = {
            'run_unit_tests': True,
            'run_integration_tests': True,
            'run_e2e_tests': True,
            'run_performance_tests': True,
            'use_real_api': False,
            'generate_coverage': True,
            'coverage_threshold': 80,
            'save_results': True,
            'results_file': 'test_results.json',
            'verbose': True
        }
        
        # Merge with provided config
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        print("🚀 HoopHead Comprehensive Test Runner Initialized")
        print(f"   Configuration: {', '.join([k for k, v in self.config.items() if v])}")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all configured test suites."""
        print("\n" + "="*100)
        print("🏀 HOOPHEAD COMPREHENSIVE TEST SUITE - FULL EXECUTION")
        print("="*100)
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        overall_start = time.time()
        
        # 1. Run Unit & Integration Tests
        if self.config['run_unit_tests'] or self.config['run_integration_tests']:
            print("\n📋 Running Comprehensive Test Suite (Unit + Integration)...")
            try:
                comprehensive_results = await run_comprehensive_test_suite(
                    include_real_api=self.config['use_real_api'],
                    verbose=self.config['verbose']
                )
                self.test_results['comprehensive'] = {
                    'status': 'completed',
                    'results': comprehensive_results,
                    'duration_seconds': time.time() - overall_start
                }
                print("   ✅ Comprehensive tests completed")
            except Exception as e:
                print(f"   ❌ Comprehensive tests failed: {e}")
                self.test_results['comprehensive'] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - overall_start
                }
        
        # 2. Run End-to-End Tests
        if self.config['run_e2e_tests']:
            print("\n🎯 Running End-to-End Workflow Tests...")
            e2e_start = time.time()
            try:
                e2e_results = await run_end_to_end_tests(
                    use_real_api=self.config['use_real_api']
                )
                self.test_results['end_to_end'] = {
                    'status': 'completed',
                    'results': e2e_results,
                    'duration_seconds': time.time() - e2e_start
                }
                print("   ✅ End-to-end tests completed")
            except Exception as e:
                print(f"   ❌ End-to-end tests failed: {e}")
                self.test_results['end_to_end'] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - e2e_start
                }
        
        # 3. Run Performance Tests
        if self.config['run_performance_tests']:
            print("\n⚡ Running Performance & Load Tests...")
            perf_start = time.time()
            try:
                perf_results = await run_performance_tests(
                    use_real_api=self.config['use_real_api']
                )
                self.test_results['performance'] = {
                    'status': 'completed',
                    'results': perf_results,
                    'duration_seconds': time.time() - perf_start
                }
                print("   ✅ Performance tests completed")
            except Exception as e:
                print(f"   ❌ Performance tests failed: {e}")
                self.test_results['performance'] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - perf_start
                }
        
        # 4. Generate Coverage Report
        if self.config['generate_coverage']:
            print("\n📊 Generating Code Coverage Report...")
            coverage_start = time.time()
            try:
                coverage_results = await self._generate_coverage_report()
                self.test_results['coverage'] = {
                    'status': 'completed',
                    'results': coverage_results,
                    'duration_seconds': time.time() - coverage_start
                }
                print("   ✅ Coverage report generated")
            except Exception as e:
                print(f"   ❌ Coverage generation failed: {e}")
                self.test_results['coverage'] = {
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - coverage_start
                }
        
        overall_duration = time.time() - overall_start
        
        # 5. Generate Final Report
        await self._generate_final_report(overall_duration)
        
        # 6. Save Results
        if self.config['save_results']:
            await self._save_test_results()
        
        return self.test_results
    
    async def _generate_coverage_report(self) -> Dict[str, Any]:
        """Generate code coverage report using pytest-cov."""
        print("   🔍 Running coverage analysis...")
        
        try:
            # Get the project root and source directories
            test_dir = Path(__file__).parent
            backend_dir = test_dir.parent / 'backend'
            src_dir = backend_dir / 'src'
            
            # Run pytest with coverage on existing test files
            coverage_cmd = [
                'python', '-m', 'pytest',
                '--cov=' + str(src_dir),
                '--cov-report=term-missing',
                '--cov-report=json:coverage.json',
                '--cov-report=html:htmlcov',
                str(test_dir),
                '-v'
            ]
            
            # Change to backend directory for proper path resolution
            original_cwd = os.getcwd()
            os.chdir(backend_dir)
            
            print(f"   Running: {' '.join(coverage_cmd)}")
            
            result = subprocess.run(
                coverage_cmd,
                capture_output=True,
                text=True,
                env={**os.environ, 'PYTHONPATH': str(src_dir)}
            )
            
            # Restore original directory
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                print("   ✅ Coverage analysis completed successfully")
                
                # Try to read coverage.json if it exists
                coverage_file = backend_dir / 'coverage.json'
                if coverage_file.exists():
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                    print(f"   📊 Overall Coverage: {total_coverage:.1f}%")
                    
                    return {
                        'total_coverage': total_coverage,
                        'coverage_data': coverage_data,
                        'threshold_met': total_coverage >= self.config['coverage_threshold'],
                        'html_report': 'htmlcov/index.html'
                    }
                else:
                    return {
                        'total_coverage': 0,
                        'coverage_data': None,
                        'threshold_met': False,
                        'note': 'Coverage file not found'
                    }
            else:
                print(f"   ⚠️ Coverage command failed: {result.stderr}")
                return {
                    'total_coverage': 0,
                    'error': result.stderr,
                    'threshold_met': False
                }
        
        except Exception as e:
            print(f"   ❌ Coverage generation error: {e}")
            return {
                'total_coverage': 0,
                'error': str(e),
                'threshold_met': False
            }
    
    async def _generate_final_report(self, overall_duration: float):
        """Generate comprehensive final report."""
        print("\n" + "="*100)
        print("📊 COMPREHENSIVE TEST EXECUTION SUMMARY")
        print("="*100)
        
        # Execution summary
        print(f"\n⏱️ Execution Summary:")
        print(f"   Total Duration: {overall_duration:.2f} seconds")
        print(f"   Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}")
        print(f"   Finished: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test suite results
        print(f"\n🧪 Test Suite Results:")
        total_suites = len(self.test_results)
        successful_suites = sum(1 for result in self.test_results.values() if result['status'] == 'completed')
        
        for suite_name, result in self.test_results.items():
            status = "✅ PASSED" if result['status'] == 'completed' else "❌ FAILED"
            duration = result['duration_seconds']
            print(f"   {suite_name.title():20} | {status} | {duration:6.2f}s")
        
        print(f"\n📈 Overall Status: {successful_suites}/{total_suites} test suites passed")
        
        # Coverage summary
        if 'coverage' in self.test_results:
            coverage_result = self.test_results['coverage']
            if coverage_result['status'] == 'completed':
                coverage_data = coverage_result['results']
                total_coverage = coverage_data.get('total_coverage', 0)
                threshold = self.config['coverage_threshold']
                threshold_met = coverage_data.get('threshold_met', False)
                
                print(f"\n📊 Code Coverage:")
                print(f"   Total Coverage: {total_coverage:.1f}%")
                print(f"   Threshold: {threshold}%")
                print(f"   Status: {'✅ PASSED' if threshold_met else '❌ BELOW THRESHOLD'}")
                
                if coverage_data.get('html_report'):
                    print(f"   HTML Report: {coverage_data['html_report']}")
        
        # Performance insights
        if 'performance' in self.test_results and self.test_results['performance']['status'] == 'completed':
            print(f"\n⚡ Performance Insights:")
            perf_data = self.test_results['performance']['results']
            if 'performance_metrics' in perf_data:
                for metric in perf_data['performance_metrics']:
                    print(f"   {metric.test_name}: {metric.avg_latency_ms:.2f}ms avg")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if successful_suites == total_suites:
            print("   🎉 Excellent! All test suites passed successfully.")
            print("   🚀 Your platform is ready for production deployment.")
        else:
            print("   🔧 Some test suites need attention:")
            for suite_name, result in self.test_results.items():
                if result['status'] == 'failed':
                    print(f"      • {suite_name.title()}: {result.get('error', 'Unknown error')}")
        
        # Coverage recommendations
        if 'coverage' in self.test_results:
            coverage_result = self.test_results['coverage']
            if coverage_result['status'] == 'completed':
                if not coverage_result['results'].get('threshold_met', False):
                    print(f"   📊 Increase test coverage to meet {self.config['coverage_threshold']}% threshold")
                else:
                    print(f"   ✅ Code coverage meets quality standards")
        
        # CI/CD Integration
        print(f"\n🔄 CI/CD Integration:")
        exit_code = 0 if successful_suites == total_suites else 1
        print(f"   Exit Code: {exit_code}")
        print(f"   Results File: {self.config['results_file']}")
        
        if 'coverage' in self.test_results and self.test_results['coverage']['status'] == 'completed':
            coverage_data = self.test_results['coverage']['results']
            if coverage_data.get('html_report'):
                print(f"   Coverage Report: {coverage_data['html_report']}")
    
    async def _save_test_results(self):
        """Save test results to JSON file."""
        try:
            results_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': time.time() - self.start_time,
                'config': self.config,
                'results': self.test_results
            }
            
            with open(self.config['results_file'], 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            print(f"\n💾 Test results saved to: {self.config['results_file']}")
        
        except Exception as e:
            print(f"\n❌ Failed to save test results: {e}")
    
    def get_exit_code(self) -> int:
        """Get appropriate exit code for CI/CD integration."""
        if not self.test_results:
            return 1  # No tests run
        
        # Check if all test suites passed
        failed_suites = [name for name, result in self.test_results.items() 
                        if result['status'] != 'completed']
        
        if failed_suites:
            return 1  # Some tests failed
        
        # Check coverage threshold if enabled
        if self.config['generate_coverage'] and 'coverage' in self.test_results:
            coverage_result = self.test_results['coverage']
            if (coverage_result['status'] == 'completed' and 
                not coverage_result['results'].get('threshold_met', False)):
                return 1  # Coverage below threshold
        
        return 0  # All tests passed


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="HoopHead Comprehensive Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests with mock API
  python run_comprehensive_tests.py
  
  # Run with real API calls (requires BALLDONTLIE_API_KEY)
  python run_comprehensive_tests.py --real-api
  
  # Run only unit and integration tests
  python run_comprehensive_tests.py --no-e2e --no-performance
  
  # Run with custom coverage threshold
  python run_comprehensive_tests.py --coverage-threshold 90
  
  # Run quietly for CI/CD
  python run_comprehensive_tests.py --quiet --no-save
        """
    )
    
    # Test selection
    parser.add_argument("--no-unit", action="store_true", help="Skip unit tests")
    parser.add_argument("--no-integration", action="store_true", help="Skip integration tests") 
    parser.add_argument("--no-e2e", action="store_true", help="Skip end-to-end tests")
    parser.add_argument("--no-performance", action="store_true", help="Skip performance tests")
    
    # API configuration
    parser.add_argument("--real-api", action="store_true", 
                       help="Use real API calls (requires BALLDONTLIE_API_KEY)")
    
    # Coverage configuration
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage generation")
    parser.add_argument("--coverage-threshold", type=int, default=80,
                       help="Coverage threshold percentage (default: 80)")
    
    # Output configuration
    parser.add_argument("--quiet", action="store_true", help="Minimize output")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    parser.add_argument("--results-file", default="test_results.json",
                       help="Results file path (default: test_results.json)")
    
    return parser.parse_args()


async def main():
    """Main entry point for comprehensive test runner."""
    args = parse_arguments()
    
    # Build configuration from arguments
    config = {
        'run_unit_tests': not args.no_unit,
        'run_integration_tests': not args.no_integration,
        'run_e2e_tests': not args.no_e2e,
        'run_performance_tests': not args.no_performance,
        'use_real_api': args.real_api,
        'generate_coverage': not args.no_coverage,
        'coverage_threshold': args.coverage_threshold,
        'save_results': not args.no_save,
        'results_file': args.results_file,
        'verbose': not args.quiet
    }
    
    # Run comprehensive tests
    runner = ComprehensiveTestRunner(config)
    await runner.run_all_tests()
    
    # Exit with appropriate code for CI/CD
    exit_code = runner.get_exit_code()
    sys.exit(exit_code)


if __name__ == "__main__":
    """Run the comprehensive test runner."""
    asyncio.run(main()) 