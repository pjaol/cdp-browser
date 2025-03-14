"""
Cloudflare Bypass Benchmark Framework

This module provides tools for benchmarking and regression testing of
Cloudflare bypass capabilities. It tracks success rates, performance metrics,
and detects regressions over time.
"""

import pytest
import asyncio
import json
import time
import psutil
import logging
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Store results from a single benchmark run"""
    timestamp: str
    test_name: str
    success: bool
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> dict:
        return asdict(self)

class CloudflareBenchmark:
    """Benchmark runner for Cloudflare bypass testing"""

    def __init__(self, results_dir: str = "benchmark_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_results: List[BenchmarkResult] = []
        self.process = psutil.Process()

    def _get_resource_usage(self) -> tuple:
        """Get current CPU and memory usage"""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        return memory_mb, cpu_percent

    async def run_benchmark(self, test_func, test_name: str, **kwargs) -> BenchmarkResult:
        """Run a single benchmark test and collect metrics"""
        start_time = time.time()
        error = None
        success = False
        
        try:
            await test_func(self, **kwargs)
            success = True
        except Exception as e:
            error = str(e)
            logger.error(f"Benchmark {test_name} failed: {e}")
        
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        memory_mb, cpu_percent = self._get_resource_usage()
        
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            test_name=test_name,
            success=success,
            duration_ms=duration,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            error=error,
            metadata=kwargs
        )
        
        self.current_results.append(result)
        return result

    def save_results(self) -> None:
        """Save benchmark results to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"benchmark_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump([r.to_dict() for r in self.current_results], f, indent=2)
        
        logger.info(f"Saved benchmark results to {results_file}")

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze benchmark results and generate statistics"""
        stats = {
            "total_tests": len(self.current_results),
            "successful_tests": sum(1 for r in self.current_results if r.success),
            "failed_tests": sum(1 for r in self.current_results if not r.success),
            "success_rate": 0.0,
            "average_duration_ms": 0.0,
            "average_memory_mb": 0.0,
            "average_cpu_percent": 0.0,
            "tests": {}
        }
        
        if stats["total_tests"] > 0:
            stats["success_rate"] = (stats["successful_tests"] / stats["total_tests"]) * 100
        
        # Group results by test name
        test_results: Dict[str, List[BenchmarkResult]] = {}
        for result in self.current_results:
            if result.test_name not in test_results:
                test_results[result.test_name] = []
            test_results[result.test_name].append(result)
        
        # Calculate per-test statistics
        for test_name, results in test_results.items():
            successful = sum(1 for r in results if r.success)
            total = len(results)
            success_rate = (successful / total) * 100 if total > 0 else 0
            
            durations = [r.duration_ms for r in results]
            memory_usage = [r.memory_mb for r in results]
            cpu_usage = [r.cpu_percent for r in results]
            
            stats["tests"][test_name] = {
                "total_runs": total,
                "successful_runs": successful,
                "success_rate": success_rate,
                "average_duration_ms": statistics.mean(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "stddev_duration_ms": statistics.stdev(durations) if len(durations) > 1 else 0,
                "average_memory_mb": statistics.mean(memory_usage),
                "average_cpu_percent": statistics.mean(cpu_usage)
            }
        
        # Calculate overall averages
        if self.current_results:
            stats["average_duration_ms"] = statistics.mean(r.duration_ms for r in self.current_results)
            stats["average_memory_mb"] = statistics.mean(r.memory_mb for r in self.current_results)
            stats["average_cpu_percent"] = statistics.mean(r.cpu_percent for r in self.current_results)
        
        return stats

    def check_regression(self, previous_results_file: Optional[str] = None) -> Dict[str, Any]:
        """Check for performance regressions against previous results"""
        if not previous_results_file:
            # Find most recent results file
            result_files = list(self.results_dir.glob("benchmark_results_*.json"))
            if not result_files:
                return {"regression_detected": False, "message": "No previous results found"}
            previous_results_file = str(sorted(result_files)[-1])
        
        try:
            with open(previous_results_file) as f:
                previous_results = json.load(f)
        except FileNotFoundError:
            return {"regression_detected": False, "message": f"Previous results file not found: {previous_results_file}"}
        
        current_stats = self.analyze_results()
        regressions = {
            "regression_detected": False,
            "details": []
        }
        
        # Define regression thresholds
        THRESHOLDS = {
            "success_rate_decrease": 5.0,  # 5% decrease in success rate
            "duration_increase": 20.0,  # 20% increase in duration
            "memory_increase": 15.0  # 15% increase in memory usage
        }
        
        # Convert previous results to a format matching current stats
        previous_stats = {
            "tests": {}
        }
        
        for result in previous_results:
            test_name = result["test_name"]
            if test_name not in previous_stats["tests"]:
                previous_stats["tests"][test_name] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "success_rate": 0,
                    "average_duration_ms": 0,
                    "average_memory_mb": 0,
                    "average_cpu_percent": 0
                }
            
            stats = previous_stats["tests"][test_name]
            stats["total_runs"] += 1
            if result["success"]:
                stats["successful_runs"] += 1
            stats["success_rate"] = (stats["successful_runs"] / stats["total_runs"]) * 100
            stats["average_duration_ms"] += result["duration_ms"]
            stats["average_memory_mb"] += result["memory_mb"]
            stats["average_cpu_percent"] += result["cpu_percent"]
        
        # Calculate averages for previous stats
        for test_stats in previous_stats["tests"].values():
            test_stats["average_duration_ms"] /= test_stats["total_runs"]
            test_stats["average_memory_mb"] /= test_stats["total_runs"]
            test_stats["average_cpu_percent"] /= test_stats["total_runs"]
        
        for test_name, current_test_stats in current_stats["tests"].items():
            if test_name in previous_stats["tests"]:
                previous_test_stats = previous_stats["tests"][test_name]
                regression_details = []
                
                # Check success rate regression
                success_rate_diff = current_test_stats["success_rate"] - previous_test_stats["success_rate"]
                if success_rate_diff < -THRESHOLDS["success_rate_decrease"]:
                    regression_details.append(
                        f"Success rate decreased by {abs(success_rate_diff):.1f}%"
                    )
                
                # Check duration regression
                duration_increase = (
                    (current_test_stats["average_duration_ms"] - previous_test_stats["average_duration_ms"])
                    / previous_test_stats["average_duration_ms"] * 100
                )
                if duration_increase > THRESHOLDS["duration_increase"]:
                    regression_details.append(
                        f"Duration increased by {duration_increase:.1f}%"
                    )
                
                # Check memory regression
                memory_increase = (
                    (current_test_stats["average_memory_mb"] - previous_test_stats["average_memory_mb"])
                    / previous_test_stats["average_memory_mb"] * 100
                )
                if memory_increase > THRESHOLDS["memory_increase"]:
                    regression_details.append(
                        f"Memory usage increased by {memory_increase:.1f}%"
                    )
                
                if regression_details:
                    regressions["regression_detected"] = True
                    regressions["details"].append({
                        "test_name": test_name,
                        "regressions": regression_details
                    })
        
        return regressions

# Example benchmark test cases
@pytest.mark.asyncio
async def test_js_challenge_benchmark(benchmark: CloudflareBenchmark):
    """Benchmark JavaScript challenge solving"""
    profile = StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
    
    async with StealthBrowser(profile=profile) as browser:
        page = await browser.create_page()
        try:
            # Test against a known JS challenge site
            await page.navigate("https://nowsecure.nl", wait_until="networkidle")
            
            # Wait for network idle with a shorter timeout
            await page.wait_for_network_idle(timeout=3.0)
            
            # Get page content for verification
            content = await page.get_content()
            
            # Verify we've bypassed the challenge
            assert "nowsecure.nl" in content.lower(), "Failed to bypass JavaScript challenge"
            
            # Additional verification
            cookies = await page.get_cookies()
            assert any(c.get('name', '').startswith('cf_') for c in cookies), "No Cloudflare cookies found"
            
        except Exception as e:
            logger.error(f"JS Challenge test failed: {str(e)}")
            raise
        finally:
            await page.close()

@pytest.mark.asyncio
async def test_turnstile_benchmark(benchmark: CloudflareBenchmark):
    """Benchmark Turnstile challenge solving"""
    profile = StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
    
    async with StealthBrowser(profile=profile) as browser:
        page = await browser.create_page()
        try:
            # Test against a known Turnstile challenge site
            await page.navigate("https://tls.peet.ws/api/all", wait_until="networkidle")
            
            # Wait for network idle with a shorter timeout
            await page.wait_for_network_idle(timeout=3.0)
            
            # Get page content for verification
            content = await page.get_content()
            
            # Verify we've loaded the page
            assert "tls" in content.lower(), "Failed to load TLS test page"
            assert "fingerprint" in content.lower(), "Failed to find fingerprint data"
            
            # Check for successful challenge completion
            success = await page.evaluate("""
                () => {
                    const content = document.body.textContent;
                    return content.includes('success') || content.includes('fingerprint');
                }
            """)
            assert success, "Failed to complete challenge"
            
            logger.info("Turnstile test passed")
            return True
            
        except Exception as e:
            logger.error(f"Turnstile test failed: {str(e)}")
            return False
        finally:
            await page.close()

@pytest.fixture
def benchmark():
    """Fixture to provide benchmark instance"""
    return CloudflareBenchmark()

@pytest.mark.asyncio
async def test_run_benchmarks(benchmark):
    """Run all benchmarks and generate report"""
    # Run JavaScript challenge benchmark
    await benchmark.run_benchmark(
        test_js_challenge_benchmark,
        "javascript_challenge"
    )
    
    # Run Turnstile challenge benchmark
    await benchmark.run_benchmark(
        test_turnstile_benchmark,
        "turnstile_challenge"
    )
    
    # Save results
    benchmark.save_results()
    
    # Analyze results
    stats = benchmark.analyze_results()
    logger.info("Benchmark Results:")
    logger.info(json.dumps(stats, indent=2))
    
    # Check for regressions
    regressions = benchmark.check_regression()
    if regressions["regression_detected"]:
        logger.warning("Performance regressions detected:")
        logger.warning(json.dumps(regressions["details"], indent=2))
    
    # Assert minimum success criteria
    assert stats["success_rate"] >= 90.0, "Overall success rate below 90%"
    assert stats["average_duration_ms"] < 5000, "Average duration exceeds 5 seconds" 