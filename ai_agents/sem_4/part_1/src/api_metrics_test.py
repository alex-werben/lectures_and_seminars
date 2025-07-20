import requests
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import argparse


class APIMetricsCollector:
    def __init__(self, base_url: str = "http://localhost:8800"):
        self.base_url = base_url
        self.generate_url = f"{base_url}/generate"
        self.health_url = f"{base_url}/health"
        
        # Metrics storage
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.total_requests = 0
        self.error_details = []
        self.token_metrics = []
        
        # Test scenarios
        self.test_prompts = [
            "The weather today is",
            "If you go into space in just a sweater and shorts, then you can",
            "Once upon a time",
            "The future of artificial intelligence",
            "Python programming is",
            "The capital of France is",
            "Machine learning algorithms",
            "In a galaxy far, far away",
            "The secret to happiness",
            "Technology has changed"
        ]
    
    def check_health(self) -> bool:
        """Check if the API is healthy"""
        try:
            response = requests.get(self.health_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def single_request_test(self, prompt: str, max_tokens: int = 256) -> Dict[str, Any]:
        """Perform a single API request and collect metrics"""
        start_time = time.time()
        
        try:
            data = {
                "text": prompt,
                "max_new_tokens": max_tokens,
                "temperature": 0.1,
                "num_return_sequences": 1
            }
            
            response = requests.post(self.generate_url, json=data, timeout=30)
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "input_tokens": result.get("input_token_count", 0),
                    "output_tokens": result.get("output_token_count", 0),
                    "total_tokens": result.get("total_token_count", 0),
                    "generated_text_length": len(result.get("generated_text", "")),
                    "prompt": prompt,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "prompt": prompt
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "response_time": end_time - start_time,
                "status_code": None,
                "error": str(e),
                "prompt": prompt
            }
    
    def run_sequential_tests(self, num_requests: int = 10) -> None:
        """Run sequential API tests"""
        print(f"\n🔄 Running {num_requests} sequential requests...")
        
        for i in range(num_requests):
            prompt = self.test_prompts[i % len(self.test_prompts)]
            result = self.single_request_test(prompt)
            self._record_result(result)
            
            print(f"Request {i+1}/{num_requests}: {'✅' if result['success'] else '❌'} "
                  f"({result['response_time']:.2f}s)")
    
    def run_concurrent_tests(self, num_requests: int = 10, max_workers: int = 3) -> None:
        """Run concurrent API tests"""
        print(f"\n🚀 Running {num_requests} concurrent requests with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all requests
            futures = []
            for i in range(num_requests):
                prompt = self.test_prompts[i % len(self.test_prompts)]
                future = executor.submit(self.single_request_test, prompt)
                futures.append(future)
            
            # Collect results
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                self._record_result(result)
                print(f"Request {i+1}/{num_requests}: {'✅' if result['success'] else '❌'} "
                      f"({result['response_time']:.2f}s)")
    
    def stress_test(self, duration_seconds: int = 30, max_workers: int = 5) -> None:
        """Run stress test for specified duration"""
        print(f"\n💪 Running stress test for {duration_seconds} seconds with {max_workers} workers...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_count = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            while time.time() < end_time:
                prompt = self.test_prompts[request_count % len(self.test_prompts)]
                future = executor.submit(self.single_request_test, prompt, 10)  # Shorter responses for stress test
                futures.append(future)
                request_count += 1
                time.sleep(0.1)  # Small delay to prevent overwhelming
            
            # Collect all results
            for future in as_completed(futures):
                result = future.result()
                self._record_result(result)
    
    def _record_result(self, result: Dict[str, Any]) -> None:
        """Record test result in metrics"""
        self.total_requests += 1
        self.response_times.append(result['response_time'])
        
        if result['success']:
            self.success_count += 1
            if 'input_tokens' in result:
                self.token_metrics.append({
                    'input_tokens': result['input_tokens'],
                    'output_tokens': result['output_tokens'],
                    'total_tokens': result['total_tokens'],
                    'response_time': result['response_time'],
                    'tokens_per_second': result['total_tokens'] / result['response_time'] if result['response_time'] > 0 else 0
                })
        else:
            self.error_count += 1
            self.error_details.append({
                'error': result['error'],
                'status_code': result.get('status_code'),
                'prompt': result['prompt'],
                'response_time': result['response_time']
            })
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive API metrics"""
        if not self.response_times:
            return {"error": "No data collected"}
        
        # Basic metrics
        success_rate = (self.success_count / self.total_requests) * 100 if self.total_requests > 0 else 0
        error_rate = (self.error_count / self.total_requests) * 100 if self.total_requests > 0 else 0
        
        # Response time metrics
        avg_response_time = statistics.mean(self.response_times)
        median_response_time = statistics.median(self.response_times)
        min_response_time = min(self.response_times)
        max_response_time = max(self.response_times)
        p95_response_time = sorted(self.response_times)[int(0.95 * len(self.response_times))]
        p99_response_time = sorted(self.response_times)[int(0.99 * len(self.response_times))]
        
        # Token metrics
        token_stats = {}
        if self.token_metrics:
            avg_input_tokens = statistics.mean([t['input_tokens'] for t in self.token_metrics])
            avg_output_tokens = statistics.mean([t['output_tokens'] for t in self.token_metrics])
            avg_total_tokens = statistics.mean([t['total_tokens'] for t in self.token_metrics])
            avg_tokens_per_second = statistics.mean([t['tokens_per_second'] for t in self.token_metrics])
            
            token_stats = {
                "avg_input_tokens": round(avg_input_tokens, 2),
                "avg_output_tokens": round(avg_output_tokens, 2),
                "avg_total_tokens": round(avg_total_tokens, 2),
                "avg_tokens_per_second": round(avg_tokens_per_second, 2),
                "max_tokens_per_second": round(max([t['tokens_per_second'] for t in self.token_metrics]), 2),
                "min_tokens_per_second": round(min([t['tokens_per_second'] for t in self.token_metrics]), 2)
            }
        
        # Throughput
        total_time = sum(self.response_times)
        requests_per_second = self.total_requests / total_time if total_time > 0 else 0
        
        return {
            "test_summary": {
                "total_requests": self.total_requests,
                "successful_requests": self.success_count,
                "failed_requests": self.error_count,
                "success_rate_percent": round(success_rate, 2),
                "error_rate_percent": round(error_rate, 2)
            },
            "response_time_metrics": {
                "average_ms": round(avg_response_time * 1000, 2),
                "median_ms": round(median_response_time * 1000, 2),
                "min_ms": round(min_response_time * 1000, 2),
                "max_ms": round(max_response_time * 1000, 2),
                "p95_ms": round(p95_response_time * 1000, 2),
                "p99_ms": round(p99_response_time * 1000, 2)
            },
            "throughput_metrics": {
                "requests_per_second": round(requests_per_second, 2),
                "avg_response_time_seconds": round(avg_response_time, 2)
            },
            "token_metrics": token_stats,
            "error_analysis": {
                "total_errors": len(self.error_details),
                "error_breakdown": self._analyze_errors()
            }
        }
    
    def _analyze_errors(self) -> Dict[str, int]:
        """Analyze error patterns"""
        error_types = {}
        for error in self.error_details:
            error_type = str(error.get('status_code', 'Unknown'))
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return error_types
    
    def print_metrics(self) -> None:
        """Print formatted metrics report"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*60)
        print("📊 API PERFORMANCE METRICS REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test Summary
        print(f"\n📈 Test Summary:")
        summary = metrics["test_summary"]
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Successful: {summary['successful_requests']} ({summary['success_rate_percent']}%)")
        print(f"  Failed: {summary['failed_requests']} ({summary['error_rate_percent']}%)")
        
        # Response Times
        print(f"\n⏱️  Response Time Metrics:")
        rt = metrics["response_time_metrics"]
        print(f"  Average: {rt['average_ms']} ms")
        print(f"  Median: {rt['median_ms']} ms")
        print(f"  Min: {rt['min_ms']} ms")
        print(f"  Max: {rt['max_ms']} ms")
        print(f"  95th percentile: {rt['p95_ms']} ms")
        print(f"  99th percentile: {rt['p99_ms']} ms")
        
        # Throughput
        print(f"\n🚀 Throughput Metrics:")
        tp = metrics["throughput_metrics"]
        print(f"  Requests per second: {tp['requests_per_second']}")
        print(f"  Average response time: {tp['avg_response_time_seconds']} seconds")
        
        # Token Metrics
        if metrics["token_metrics"]:
            print(f"\n🔤 Token Metrics:")
            tm = metrics["token_metrics"]
            print(f"  Average input tokens: {tm['avg_input_tokens']}")
            print(f"  Average output tokens: {tm['avg_output_tokens']}")
            print(f"  Average total tokens: {tm['avg_total_tokens']}")
            print(f"  Average tokens/second: {tm['avg_tokens_per_second']}")
            print(f"  Max tokens/second: {tm['max_tokens_per_second']}")
        
        # Errors
        if metrics["error_analysis"]["total_errors"] > 0:
            print(f"\n❌ Error Analysis:")
            print(f"  Total errors: {metrics['error_analysis']['total_errors']}")
            for error_type, count in metrics["error_analysis"]["error_breakdown"].items():
                print(f"  {error_type}: {count}")
    
    def save_metrics_to_file(self, filename: str = None) -> None:
        """Save metrics to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_metrics_{timestamp}.json"
        
        metrics = self.calculate_metrics()
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n💾 Metrics saved to: {filename}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="🧪 API Metrics Testing Tool for FastAPI Text Generation Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python api_metrics_test.py                                    # Run with default settings
  python api_metrics_test.py --seq-requests 10 --conc-requests 20   # Custom request counts
  python api_metrics_test.py --stress-duration 30 --stress-workers 5 # Custom stress test
  python api_metrics_test.py --url http://192.168.1.100:8000    # Custom API URL
  python api_metrics_test.py --output my_results.json           # Custom output file
  python api_metrics_test.py --skip-sequential --skip-stress    # Run only concurrent tests
        """
    )
    
    # API Configuration
    parser.add_argument('--url', '--base-url', 
                       default='http://localhost:8800',
                       help='Base URL of the API (default: http://localhost:8800)')
    
    # Sequential Tests
    parser.add_argument('--seq-requests', '--sequential-requests',
                       type=int, default=5,
                       help='Number of sequential requests (default: 5)')
    
    parser.add_argument('--skip-sequential',
                       action='store_true',
                       help='Skip sequential tests')
    
    # Concurrent Tests
    parser.add_argument('--conc-requests', '--concurrent-requests',
                       type=int, default=10,
                       help='Number of concurrent requests (default: 10)')
    
    parser.add_argument('--conc-workers', '--concurrent-workers',
                       type=int, default=3,
                       help='Number of concurrent workers (default: 3)')
    
    parser.add_argument('--skip-concurrent',
                       action='store_true',
                       help='Skip concurrent tests')
    
    # Stress Tests
    parser.add_argument('--stress-duration',
                       type=int, default=15,
                       help='Stress test duration in seconds (default: 15)')
    
    parser.add_argument('--stress-workers',
                       type=int, default=3,
                       help='Number of stress test workers (default: 3)')
    
    parser.add_argument('--skip-stress',
                       action='store_true',
                       help='Skip stress tests')
    
    # Output Options
    parser.add_argument('--output', '--output-file',
                       help='Output file for metrics (default: auto-generated timestamp)')
    
    parser.add_argument('--no-save',
                       action='store_true',
                       help='Do not save metrics to file')
    
    return parser.parse_args()

def main():
    """Main function to run API tests"""
    args = parse_arguments()
    
    print("🧪 API Metrics Testing Tool")
    print("=" * 40)
    print(f"Target URL: {args.url}")
    print(f"Sequential requests: {args.seq_requests if not args.skip_sequential else 'SKIPPED'}")
    print(f"Concurrent requests: {args.conc_requests} (workers: {args.conc_workers}) {'' if not args.skip_concurrent else '- SKIPPED'}")
    print(f"Stress test: {args.stress_duration}s (workers: {args.stress_workers}) {'' if not args.skip_stress else '- SKIPPED'}")
    print()
    
    # Initialize collector
    collector = APIMetricsCollector(base_url=args.url)
    
    # Check if API is healthy
    if not collector.check_health():
        print("❌ API is not healthy! Make sure your FastAPI server is running.")
        return
    
    print("✅ API health check passed!")
    
    # Run different types of tests based on arguments
    try:
        # Sequential tests
        if not args.skip_sequential:
            collector.run_sequential_tests(num_requests=args.seq_requests)
        
        # Concurrent tests
        if not args.skip_concurrent:
            collector.run_concurrent_tests(
                num_requests=args.conc_requests, 
                max_workers=args.conc_workers
            )
        
        # Stress test
        if not args.skip_stress:
            collector.stress_test(
                duration_seconds=args.stress_duration, 
                max_workers=args.stress_workers
            )
        
        # Print results
        collector.print_metrics()
        
        # Save to file
        if not args.no_save:
            collector.save_metrics_to_file(args.output)
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        if collector.total_requests > 0:
            collector.print_metrics()
            if not args.no_save:
                collector.save_metrics_to_file(args.output)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    main()