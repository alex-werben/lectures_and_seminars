import requests
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
import numpy as np


class LLMInferenceMetrics:
    def __init__(self, base_url: str = "http://localhost:8000", endpoint_path: str = "/generate", api_format: str = "fastapi"):
        self.base_url = base_url
        self.endpoint_path = endpoint_path
        self.api_format = api_format  # "fastapi", "triton", or "tensorrt" 
        self.generate_url = f"{base_url}{endpoint_path}"
        
        # Metrics storage
        self.inference_results = []
        self.successful_inferences = []
        self.failed_inferences = []
        
        # LLM-specific metrics
        self.ttft_times = []  # Time to First Token
        self.tps_rates = []   # Tokens per Second
        self.itl_times = []   # Inter-Token Latency
        self.total_inference_times = []
        
        # Test scenarios with different complexities
        self.test_prompts = {
            "short": [
                "Hello",
                "What is AI?",
                "The weather is",
                "Python is",
                "Today I feel"
            ],
            "medium": [
                "Explain machine learning in simple terms",
                "Write a short story about a robot",
                "What are the benefits of renewable energy?",
                "Describe the process of photosynthesis",
                "How does the internet work?"
            ],
            "long": [
                "Write a detailed explanation of how neural networks learn and adapt, including the mathematical concepts behind backpropagation",
                "Create a comprehensive guide for someone starting a small business, covering legal, financial, and marketing aspects",
                "Explain the history and impact of artificial intelligence on modern society, including both benefits and potential risks",
                "Describe the complete process of software development from initial concept to deployment and maintenance",
                "Analyze the environmental impact of different energy sources and propose solutions for sustainable energy future"
            ]
        }
    
    
    def single_inference_test(self, prompt: str, max_tokens: int = 50, temperature: float = 0.1) -> Dict[str, Any]:
        """Perform a single inference and collect detailed LLM metrics"""
        
        # Prepare request based on API format
        if self.api_format == "triton":
            data = {
                "text_input": prompt,
                "stream": False,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        elif self.api_format == "tensorrt":
            data = {
                "inputs": [
                    {
                        "name": "text_input",
                        "shape": [1, 1],
                        "datatype": "BYTES",
                        "data": [prompt]
                    },
                    {
                        "name": "max_tokens",
                        "shape": [1, 1],
                        "datatype": "INT32",
                        "data": [max_tokens]
                    }
                ]
            }
        else:  # fastapi format
            data = {
                "text": prompt,
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "num_return_sequences": 1
            }
        
        # Start timing
        request_start = time.time()
        
        try:
            # Make the request
            response = requests.post(self.generate_url, json=data, timeout=60)
            request_end = time.time()
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract metrics based on API format
                if self.api_format == "triton":
                    # Handle Triton response format - field is 'text_output'
                    generated_text = result.get("text_output", "")
                    
                    # Estimate tokens if not provided (rough approximation: 1 token ≈ 0.75 words)
                    if generated_text:
                        # Remove the original prompt from the output to get only new tokens
                        if generated_text.startswith(prompt.strip()):
                            new_text = generated_text[len(prompt.strip()):].strip()
                        else:
                            new_text = generated_text

                        # Ensure we have reasonable token counts
                        input_tokens = result.get("input_tokens", max(int(len(prompt.split()) * 1.3), 1) if prompt else 1)
                        output_tokens = result.get("output_tokens", max(int(len(new_text.split()) * 1.3), 1) if new_text else 1)
                        total_tokens = input_tokens + output_tokens
                        
                    else:
                        # If no text generated, still count input tokens
                        input_tokens = result.get("input_tokens", max(int(len(prompt.split()) * 1.3), 1) if prompt else 1)
                        output_tokens = 0
                        total_tokens = input_tokens
                elif self.api_format == "tensorrt":
                    # Handle TensorRT-LLM response format - text is in outputs array
                    generated_text = ""
                    outputs = result.get("outputs", [])
                    
                    # Find text_output in outputs array
                    for output in outputs:
                        if output.get("name") == "text_output":
                            data = output.get("data", [])
                            if data:
                                generated_text = data[0]
                            break
                    
                    # Estimate tokens if not provided (rough approximation: 1 token ≈ 0.75 words)
                    if generated_text:
                        # Remove the original prompt from the output to get only new tokens
                        if generated_text.startswith(prompt.strip()):
                            new_text = generated_text[len(prompt.strip()):].strip()
                        else:
                            new_text = generated_text
                        
                        # Ensure we have reasonable token counts
                        input_tokens = max(int(len(prompt.split()) * 1.3), 1) if prompt else 1
                        output_tokens = max(int(len(new_text.split()) * 1.3), 1) if new_text else 1
                        total_tokens = input_tokens + output_tokens
                    else:
                        # If no text generated, still count input tokens
                        input_tokens = max(int(len(prompt.split()) * 1.3), 1) if prompt else 1
                        output_tokens = 0
                        total_tokens = input_tokens
                else:  # fastapi format
                    input_tokens = result.get("input_token_count", 0)
                    output_tokens = result.get("output_token_count", 0)
                    total_tokens = result.get("total_token_count", 0)
                    generated_text = result.get("generated_text", "")
                
                total_time = request_end - request_start
                
                # Calculate LLM-specific metrics
                metrics = self._calculate_llm_metrics(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    total_time=total_time,
                    prompt=prompt,
                    generated_text=generated_text
                )
                
                return {
                    "success": True,
                    "prompt": prompt,
                    "prompt_length": len(prompt),
                    "generated_text": generated_text,
                    "generated_text_length": len(generated_text),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "total_time": total_time,
                    "request_start": request_start,
                    "request_end": request_end,
                    **metrics,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "prompt": prompt,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "total_time": request_end - request_start
                }
                
        except Exception as e:
            return {
                "success": False,
                "prompt": prompt,
                "error": str(e),
                "total_time": time.time() - request_start
            }
    
    def _calculate_llm_metrics(self, input_tokens: int, output_tokens: int, total_tokens: int, 
                              total_time: float, prompt: str, generated_text: str) -> Dict[str, float]:
        """Calculate LLM-specific inference metrics"""
        
        # Time to First Token (TTFT) - Estimated
        # Since we don't have streaming, we estimate based on request overhead and generation
        estimated_processing_overhead = 0.1  # seconds for request processing
        ttft = min(total_time * 0.3, estimated_processing_overhead + (total_time * 0.1))
        
        # Tokens per Second (TPS) - Overall generation rate
        tps = output_tokens / total_time if total_time > 0 and output_tokens > 0 else 0
        
        # Inter-Token Latency (ITL) - Average time between tokens
        # Estimated as (total_time - ttft) / (output_tokens - 1)
        generation_time = total_time - ttft
        itl = generation_time / max(output_tokens - 1, 1) if output_tokens > 1 else generation_time
        
        # Throughput metrics
        total_tps = total_tokens / total_time if total_time > 0 else 0
        
        # Efficiency metrics
        processing_efficiency = output_tokens / total_time if total_time > 0 else 0
        token_generation_ratio = output_tokens / max(input_tokens, 1)
        
        # Quality proxy metrics
        avg_word_length = np.mean([len(word) for word in generated_text.split()]) if generated_text.split() else 0
        response_completeness = len(generated_text.strip()) / max(len(prompt), 1)
        
        return {
            "ttft": ttft,  # Time to First Token
            "tps": tps,    # Tokens per Second (output only)
            "itl": itl,    # Inter-Token Latency
            "total_tps": total_tps,  # Total throughput
            "processing_efficiency": processing_efficiency,
            "token_generation_ratio": token_generation_ratio,
            "avg_word_length": avg_word_length,
            "response_completeness": response_completeness,
            "generation_time": generation_time
        }
    
    def run_prompt_complexity_tests(self, requests_per_complexity: int = 5) -> None:
        """Test different prompt complexities"""
        for complexity, prompts in self.test_prompts.items():
            # Adjust max_tokens based on complexity
            max_tokens = {"short": 20, "medium": 50, "long": 100}[complexity]
            
            for i in range(requests_per_complexity):
                prompt = prompts[i % len(prompts)]
                result = self.single_inference_test(prompt, max_tokens=max_tokens)
                self._record_inference_result(result, complexity)
    
    def run_token_length_tests(self, token_lengths: List[int] = [10, 25, 50, 100]) -> None:
        """Test different output token lengths"""
        base_prompt = "Write a detailed explanation about artificial intelligence"
        
        for token_length in token_lengths:
            for i in range(3):  # 3 tests per length
                result = self.single_inference_test(base_prompt, max_tokens=token_length)
                self._record_inference_result(result, f"tokens_{token_length}")
    
    def run_concurrent_inference_tests(self, num_requests: int = 100, max_workers: int = 10) -> None:
        """Test concurrent inference performance"""
        prompts = self.test_prompts["medium"]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            # Submit all requests
            for i in range(num_requests):
                prompt = prompts[i % len(prompts)]
                future = executor.submit(self.single_inference_test, prompt, 30)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                self._record_inference_result(result, "concurrent")
    
    def _record_inference_result(self, result: Dict[str, Any], test_type: str) -> None:
        """Record inference result with test type"""
        result["test_type"] = test_type
        self.inference_results.append(result)
        
        if result["success"]:
            self.successful_inferences.append(result)
            # Collect LLM metrics
            self.ttft_times.append(result["ttft"])
            self.tps_rates.append(result["tps"])
            self.itl_times.append(result["itl"])
            self.total_inference_times.append(result["total_time"])
        else:
            self.failed_inferences.append(result)
    
    def calculate_comprehensive_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive LLM inference metrics"""
        if not self.successful_inferences:
            return {"error": "No successful inferences to analyze"}
        
        # Basic statistics
        total_requests = len(self.inference_results)
        successful_requests = len(self.successful_inferences)
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        
        # TTFT Statistics
        ttft_stats = {
            "avg_ms": round(statistics.mean(self.ttft_times) * 1000, 2),
            "median_ms": round(statistics.median(self.ttft_times) * 1000, 2),
            "min_ms": round(min(self.ttft_times) * 1000, 2),
            "max_ms": round(max(self.ttft_times) * 1000, 2),
            "p95_ms": round(sorted(self.ttft_times)[int(0.95 * len(self.ttft_times))] * 1000, 2),
            "std_ms": round(statistics.stdev(self.ttft_times) * 1000, 2) if len(self.ttft_times) > 1 else 0
        }
        
        # TPS Statistics
        tps_stats = {
            "avg": round(statistics.mean(self.tps_rates), 2),
            "median": round(statistics.median(self.tps_rates), 2),
            "min": round(min(self.tps_rates), 2),
            "max": round(max(self.tps_rates), 2),
            "p95": round(sorted(self.tps_rates)[int(0.95 * len(self.tps_rates))], 2),
            "std": round(statistics.stdev(self.tps_rates), 2) if len(self.tps_rates) > 1 else 0
        }
        
        # ITL Statistics
        itl_stats = {
            "avg_ms": round(statistics.mean(self.itl_times) * 1000, 2),
            "median_ms": round(statistics.median(self.itl_times) * 1000, 2),
            "min_ms": round(min(self.itl_times) * 1000, 2),
            "max_ms": round(max(self.itl_times) * 1000, 2),
            "p95_ms": round(sorted(self.itl_times)[int(0.95 * len(self.itl_times))] * 1000, 2),
            "std_ms": round(statistics.stdev(self.itl_times) * 1000, 2) if len(self.itl_times) > 1 else 0
        }
        
        # Throughput Analysis
        total_input_tokens = sum([r["input_tokens"] for r in self.successful_inferences])
        total_output_tokens = sum([r["output_tokens"] for r in self.successful_inferences])
        total_time = sum(self.total_inference_times)
        
        throughput_stats = {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_time_seconds": round(total_time, 2),
            "input_tokens_per_second": round(total_input_tokens / total_time, 2) if total_time > 0 else 0,
            "output_tokens_per_second": round(total_output_tokens / total_time, 2) if total_time > 0 else 0,
            "requests_per_second": round(successful_requests / total_time, 2) if total_time > 0 else 0
        }
        

        
        # Token efficiency analysis
        avg_input_tokens = statistics.mean([r["input_tokens"] for r in self.successful_inferences])
        avg_output_tokens = statistics.mean([r["output_tokens"] for r in self.successful_inferences])
        avg_generation_ratio = statistics.mean([r["token_generation_ratio"] for r in self.successful_inferences])
        
        return {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": len(self.failed_inferences),
                "success_rate_percent": round(success_rate, 2)
            },
            "ttft_metrics": ttft_stats,
            "tps_metrics": tps_stats,
            "itl_metrics": itl_stats,
            "throughput_metrics": throughput_stats,
            "token_efficiency": {
                "avg_input_tokens": round(avg_input_tokens, 2),
                "avg_output_tokens": round(avg_output_tokens, 2),
                "avg_generation_ratio": round(avg_generation_ratio, 2)
            }
        }
    
    def print_llm_metrics_report(self) -> None:
        """Print comprehensive LLM inference metrics report"""
        metrics = self.calculate_comprehensive_metrics()
        
        if "error" in metrics:
            print(f"❌ {metrics['error']}")
            return
        
        print("\n" + "="*70)
        print("🧠 LLM INFERENCE PERFORMANCE METRICS REPORT")
        print("="*70)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Summary
        print(f"\n📊 Test Summary:")
        summary = metrics["summary"]
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Successful: {summary['successful_requests']} ({summary['success_rate_percent']}%)")
        print(f"  Failed: {summary['failed_requests']}")
        
        # TTFT Metrics
        print(f"\n⚡ Time to First Token (TTFT):")
        ttft = metrics["ttft_metrics"]
        print(f"  Average: {ttft['avg_ms']} ms")
        print(f"  Median: {ttft['median_ms']} ms")
        print(f"  Min: {ttft['min_ms']} ms")
        print(f"  Max: {ttft['max_ms']} ms")
        print(f"  95th percentile: {ttft['p95_ms']} ms")
        print(f"  Std deviation: {ttft['std_ms']} ms")
        
        # TPS Metrics
        print(f"\n🚀 Tokens per Second (TPS):")
        tps = metrics["tps_metrics"]
        print(f"  Average: {tps['avg']} tokens/sec")
        print(f"  Median: {tps['median']} tokens/sec")
        print(f"  Min: {tps['min']} tokens/sec")
        print(f"  Max: {tps['max']} tokens/sec")
        print(f"  95th percentile: {tps['p95']} tokens/sec")
        print(f"  Std deviation: {tps['std']} tokens/sec")
        
        # ITL Metrics
        print(f"\n⏰ Inter-Token Latency (ITL):")
        itl = metrics["itl_metrics"]
        print(f"  Average: {itl['avg_ms']} ms")
        print(f"  Median: {itl['median_ms']} ms")
        print(f"  Min: {itl['min_ms']} ms")
        print(f"  Max: {itl['max_ms']} ms")
        print(f"  95th percentile: {itl['p95_ms']} ms")
        print(f"  Std deviation: {itl['std_ms']} ms")
        
        # Throughput
        print(f"\n📈 System Throughput:")
        throughput = metrics["throughput_metrics"]
        print(f"  Input tokens/second: {throughput['input_tokens_per_second']}")
        print(f"  Output tokens/second: {throughput['output_tokens_per_second']}")
        print(f"  Requests/second: {throughput['requests_per_second']}")
        print(f"  Total processing time: {throughput['total_time_seconds']} seconds")
        
        # Token Efficiency
        print(f"\n🔤 Token Efficiency:")
        efficiency = metrics["token_efficiency"]
        print(f"  Average input tokens: {efficiency['avg_input_tokens']}")
        print(f"  Average output tokens: {efficiency['avg_output_tokens']}")
        print(f"  Generation ratio: {efficiency['avg_generation_ratio']}")
        
        # Summary Table
        print(f"\n" + "="*50)
        print("📋 SUMMARY TABLE")
        print("="*50)
        
        # Core metrics summary
        ttft = metrics["ttft_metrics"]
        tps = metrics["tps_metrics"] 
        itl = metrics["itl_metrics"]
        throughput = metrics["throughput_metrics"]
        efficiency = metrics["token_efficiency"]
        summary = metrics["summary"]
        
        print(f"Success Rate - {summary['success_rate_percent']}%")
        print(f"Total Requests - {summary['total_requests']}")
        print(f"Average TTFT - {ttft['avg_ms']} ms")
        print(f"Median TTFT - {ttft['median_ms']} ms")
        print(f"95th Percentile TTFT - {ttft['p95_ms']} ms")
        print(f"Average TPS - {tps['avg']} tokens/sec")
        print(f"Median TPS - {tps['median']} tokens/sec")
        print(f"Max TPS - {tps['max']} tokens/sec")
        print(f"Average ITL - {itl['avg_ms']} ms")
        print(f"Median ITL - {itl['median_ms']} ms")
        print(f"95th Percentile ITL - {itl['p95_ms']} ms")
        print(f"Output Tokens/Second - {throughput['output_tokens_per_second']}")
        print(f"Requests/Second - {throughput['requests_per_second']}")
        print(f"Average Input Tokens - {efficiency['avg_input_tokens']}")
        print(f"Average Output Tokens - {efficiency['avg_output_tokens']}")
        print(f"Generation Ratio - {efficiency['avg_generation_ratio']}")
        print("="*50)
    
    def save_metrics_to_file(self, filename: str = None) -> None:
        """Save comprehensive metrics to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_inference_metrics_{timestamp}.json"
        
        metrics = self.calculate_comprehensive_metrics()
        
        # Add raw data for further analysis
        metrics["raw_inference_data"] = self.successful_inferences
        metrics["failed_inferences"] = self.failed_inferences
        
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"\n💾 LLM metrics saved to: {filename}")

def parse_arguments():
    """Parse command line arguments for LLM inference testing"""
    parser = argparse.ArgumentParser(
        description="🧠 LLM Inference Metrics Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python llm_inference_metrics.py                               # Run all tests with defaults (FastAPI)
  python llm_inference_metrics.py --api-format triton           # Use Triton format
  python llm_inference_metrics.py --endpoint "/v2/models/llama3_2_1b_local/generate" --api-format triton
  python llm_inference_metrics.py --endpoint "/v2/models/ensemble/infer" --api-format tensorrt
  python llm_inference_metrics.py --complexity-tests 3          # 3 requests per complexity
  python llm_inference_metrics.py --token-lengths 20 50 100     # Test specific token lengths
  python llm_inference_metrics.py --concurrent-requests 20      # 20 concurrent requests
  python llm_inference_metrics.py --url http://localhost:8001   # Custom API URL
  python llm_inference_metrics.py --skip-complexity             # Skip complexity tests
        """
    )
    
    # API Configuration
    parser.add_argument('--url', '--base-url', 
                       default='http://localhost:8000',
                       help='Base URL of the API (default: http://localhost:8000)')
    
    parser.add_argument('--endpoint', '--endpoint-path',
                       default='/generate',
                       help='API endpoint path (default: /generate)')
    
    parser.add_argument('--api-format', 
                       choices=['fastapi', 'triton', 'tensorrt'],
                       default='fastapi',
                       help='API format: fastapi, triton, or tensorrt (default: fastapi)')
    
    # Test Configuration
    parser.add_argument('--complexity-tests',
                       type=int, default=5,
                       help='Number of requests per complexity level (default: 5)')
    
    parser.add_argument('--skip-complexity',
                       action='store_true',
                       help='Skip prompt complexity tests')
    
    parser.add_argument('--token-lengths',
                       type=int, nargs='+', default=[10, 25, 50, 100],
                       help='Token lengths to test (default: 10 25 50 100)')
    
    parser.add_argument('--skip-token-tests',
                       action='store_true',
                       help='Skip token length tests')
    
    parser.add_argument('--concurrent-requests',
                       type=int, default=100,
                       help='Number of concurrent requests')
    
    parser.add_argument('--concurrent-workers',
                       type=int, default=10,
                       help='Number of concurrent workers')
    
    parser.add_argument('--skip-concurrent',
                       action='store_true',
                       help='Skip concurrent tests')
    
    # Output Options
    parser.add_argument('--output', '--output-file',
                       help='Output file for metrics (default: auto-generated timestamp)')
    
    parser.add_argument('--no-save',
                       action='store_true',
                       help='Do not save metrics to file')
    
    return parser.parse_args()

    
def main():
    """Main function to run LLM inference tests"""
    args = parse_arguments()
    
    print("🧠 LLM Inference Metrics Testing Tool")
    print("=" * 40)
    print(f"📡 Target: {args.url}{args.endpoint}")
    print(f"🔧 API Format: {args.api_format}")
    
    # Count total tests
    total_tests = 0
    if not args.skip_complexity:
        total_tests += args.complexity_tests * 3  # 3 complexity levels
    if not args.skip_token_tests:
        total_tests += len(args.token_lengths) * 3  # 3 tests per token length
    if not args.skip_concurrent:
        total_tests += args.concurrent_requests
    
    print(f"📊 Total requests: ~{total_tests}")
    print()
    
    # Initialize metrics collector
    llm_metrics = LLMInferenceMetrics(
        base_url=args.url, 
        endpoint_path=args.endpoint,
        api_format=args.api_format
    )
    
    try:
        # Run complexity tests
        if not args.skip_complexity:
            llm_metrics.run_prompt_complexity_tests(requests_per_complexity=args.complexity_tests)
        
        # Run token length tests
        if not args.skip_token_tests:
            llm_metrics.run_token_length_tests(token_lengths=args.token_lengths)
        
        # Run concurrent tests
        if not args.skip_concurrent:
            llm_metrics.run_concurrent_inference_tests(
                num_requests=args.concurrent_requests,
                max_workers=args.concurrent_workers
            )
        
        # Print comprehensive report
        llm_metrics.print_llm_metrics_report()
        
        # Save to file
        if not args.no_save:
            llm_metrics.save_metrics_to_file(args.output)
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        if llm_metrics.successful_inferences:
            llm_metrics.print_llm_metrics_report()
            if not args.no_save:
                llm_metrics.save_metrics_to_file(args.output)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    main() 