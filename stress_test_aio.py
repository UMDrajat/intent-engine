#!/usr/bin/env python3
"""
Comprehensive Stress Test for Intent Engine AIO Container
Tests: Basic functionality, load, edge cases, resource limits, security
"""

import requests
import json
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE_URL = "http://localhost:80"
TIMEOUT = 30

class StressTestResults:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.errors = []
        self.status_codes = {}
        
    def add_result(self, success, response_time, status_code=None, error=None):
        self.total_requests += 1
        self.response_times.append(response_time)
        if success:
            self.successful_requests += 1
            if status_code:
                self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        else:
            self.failed_requests += 1
            self.errors.append(error)
    
    def summary(self):
        if not self.response_times:
            return "No results"
        return {
            "total": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{(self.successful_requests/self.total_requests)*100:.1f}%",
            "mean_response_time": f"{statistics.mean(self.response_times):.2f}ms",
            "median_response_time": f"{statistics.median(self.response_times):.2f}ms",
            "p95_response_time": f"{sorted(self.response_times)[int(len(self.response_times)*0.95)]:.2f}ms" if len(self.response_times) > 20 else "N/A",
            "min_response_time": f"{min(self.response_times):.2f}ms",
            "max_response_time": f"{max(self.response_times):.2f}ms",
            "status_codes": self.status_codes,
            "unique_errors": len(set(self.errors)),
        }

def make_request(method, endpoint, data=None, headers=None):
    """Make a single request and return (success, response_time, status_code, error)"""
    start = time.time()
    try:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT, headers=headers)
        elif method == "POST":
            resp = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT, headers=headers)
        elif method == "PUT":
            resp = requests.put(f"{BASE_URL}{endpoint}", json=data, timeout=TIMEOUT, headers=headers)
        elif method == "DELETE":
            resp = requests.delete(f"{BASE_URL}{endpoint}", timeout=TIMEOUT, headers=headers)
        else:
            return False, 0, None, "Invalid method"
        
        response_time = (time.time() - start) * 1000
        success = 200 <= resp.status_code < 400
        return success, response_time, resp.status_code, None
    except requests.exceptions.Timeout:
        return False, (time.time() - start) * 1000, None, "Timeout"
    except requests.exceptions.ConnectionError as e:
        return False, (time.time() - start) * 1000, None, f"ConnectionError: {str(e)}"
    except Exception as e:
        return False, (time.time() - start) * 1000, None, str(e)

def test_health_endpoints():
    """Test all health check endpoints"""
    print("\n=== Testing Health Endpoints ===")
    endpoints = ["/", "/health", "/health/live", "/health/ready", "/status"]
    results = []
    for endpoint in endpoints:
        success, rt, status, error = make_request("GET", endpoint)
        status_str = "✓" if success else "✗"
        print(f"  {status_str} {endpoint}: {status} ({rt:.1f}ms)")
        results.append((success, rt, status, error))
    return results

def test_intent_extraction():
    """Test intent extraction with various queries"""
    print("\n=== Testing Intent Extraction ===")
    queries = [
        "best laptop for programming under 50000 rupees",
        "how to set up E2E encrypted email on Android",
        "python tutorial for beginners",
        "compare iPhone vs Samsung",
        "troubleshoot wifi connection issues",
        "what is machine learning",
        "buy running shoes size 10 under $100",
        "recipe for vegetarian pasta",
        "debug python null pointer error",
        "learn react hooks tutorial",
    ]
    
    results = StressTestResults()
    for query in queries:
        payload = {
            "product": "search",
            "input": {"text": query},
            "context": {"sessionId": f"test-{int(time.time())}", "userLocale": "en-US"}
        }
        success, rt, status, error = make_request("POST", "/extract-intent", data=payload)
        results.add_result(success, rt, status, error)
        status_str = "✓" if success else "✗"
        print(f"  {status_str} Query: '{query[:40]}...': {status} ({rt:.1f}ms)")
        if error:
            print(f"      Error: {error}")
    
    print(f"\n  Summary: {results.summary()}")
    return results

def test_search_api():
    """Test search API endpoints"""
    print("\n=== Testing Search API ===")
    search_queries = [
        "python programming",
        "machine learning tutorial",
        "best restaurants near me",
        "weather forecast",
        "news today",
    ]
    
    results = StressTestResults()
    for query in search_queries:
        payload = {
            "query": query,
            "limit": 10,
            "intent": {"goal": "LEARN"}
        }
        success, rt, status, error = make_request("POST", "/search", data=payload)
        results.add_result(success, rt, status, error)
        status_str = "✓" if success else "✗"
        print(f"  {status_str} Search: '{query}': {status} ({rt:.1f}ms)")
        if error:
            print(f"      Error: {error}")
    
    print(f"\n  Summary: {results.summary()}")
    return results

def test_concurrent_requests(num_requests=50, num_workers=10):
    """Test concurrent requests"""
    print(f"\n=== Testing Concurrent Requests ({num_requests} requests, {num_workers} workers) ===")
    
    results = StressTestResults()
    start_time = time.time()
    
    def worker(request_id):
        payload = {
            "product": "search",
            "input": {"text": f"test query {request_id}"},
            "context": {"sessionId": f"concurrent-test-{request_id}", "userLocale": "en-US"}
        }
        success, rt, status, error = make_request("POST", "/extract-intent", data=payload)
        results.add_result(success, rt, status, error)
        return success, rt, status
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, i) for i in range(num_requests)]
        for future in as_completed(futures):
            pass
    
    total_time = time.time() - start_time
    summary = results.summary()
    summary["total_time"] = f"{total_time:.2f}s"
    summary["requests_per_second"] = f"{num_requests/total_time:.2f}"
    
    print(f"\n  Summary: {summary}")
    return results

def test_edge_cases():
    """Test edge cases and invalid inputs"""
    print("\n=== Testing Edge Cases ===")
    
    test_cases = [
        ("Empty query", {"product": "search", "input": {"text": ""}, "context": {}}),
        ("Very long query", {"product": "search", "input": {"text": "a" * 10000}, "context": {}}),
        ("Missing fields", {"product": "search"}),
        ("Invalid JSON type", {"product": 123, "input": "not a dict"}),
        ("Unicode query", {"product": "search", "input": {"text": "你好世界"}, "context": {}}),
        ("SQL injection attempt", {"product": "search", "input": {"text": "'; DROP TABLE users; --"}, "context": {}}),
        ("XSS attempt", {"product": "search", "input": {"text": "<script>alert('xss')</script>"}, "context": {}}),
        ("Null payload", None),
    ]
    
    results = StressTestResults()
    for name, payload in test_cases:
        success, rt, status, error = make_request("POST", "/extract-intent", data=payload, headers={"Content-Type": "application/json"})
        results.add_result(success, rt, status, error)
        status_str = "✓" if 200 <= (status or 0) < 500 else "✗"  # Any non-500 is acceptable for edge cases
        print(f"  {status_str} {name}: {status} ({rt:.1f}ms)")
        if error and "Timeout" in str(error):
            print(f"      ⚠ TIMEOUT - This is a potential issue!")
    
    print(f"\n  Summary: {results.summary()}")
    return results

def test_large_payloads():
    """Test with large payloads"""
    print("\n=== Testing Large Payloads ===")
    
    results = StressTestResults()
    
    # Test with large context
    large_context = {"sessionId": "test", "data": "x" * 100000}  # 100KB context
    payload = {"product": "search", "input": {"text": "test"}, "context": large_context}
    success, rt, status, error = make_request("POST", "/extract-intent", data=payload)
    results.add_result(success, rt, status, error)
    print(f"  {'✓' if success else '✗'} Large context (100KB): {status} ({rt:.1f}ms)")
    
    # Test with many fields
    many_fields = {f"field_{i}": f"value_{i}" for i in range(100)}
    payload = {"product": "search", "input": {"text": "test"}, "context": many_fields}
    success, rt, status, error = make_request("POST", "/extract-intent", data=payload)
    results.add_result(success, rt, status, error)
    print(f"  {'✓' if success else '✗'} Many fields (100): {status} ({rt:.1f}ms)")
    
    print(f"\n  Summary: {results.summary()}")
    return results

def test_rate_limiting():
    """Test rate limiting"""
    print("\n=== Testing Rate Limiting ===")
    
    results = StressTestResults()
    rate_limited_count = 0
    
    # Send rapid requests
    for i in range(150):
        payload = {"product": "search", "input": {"text": f"rate limit test {i}"}, "context": {}}
        success, rt, status, error = make_request("POST", "/extract-intent", data=payload)
        results.add_result(success, rt, status, error)
        if status == 429:
            rate_limited_count += 1
            if rate_limited_count == 1:
                print(f"  ✓ Rate limiting triggered after {i+1} requests")
    
    print(f"  Rate limited requests: {rate_limited_count}/{results.total_requests}")
    print(f"\n  Summary: {results.summary()}")
    return results

def test_service_dependencies():
    """Test service dependencies through API"""
    print("\n=== Testing Service Dependencies ===")
    
    # Test health endpoint which checks all services
    success, rt, status, error = make_request("GET", "/health/detailed")
    print(f"  Health detailed: {status} ({rt:.1f}ms)")
    if success:
        try:
            resp = requests.get(f"{BASE_URL}/health/detailed", timeout=TIMEOUT)
            data = resp.json()
            print(f"  Services status:")
            for service, info in data.get("services", {}).items():
                status_icon = "✓" if info.get("healthy") else "✗"
                print(f"    {status_icon} {service}: {info.get('status', 'unknown')}")
        except Exception as e:
            print(f"  Error parsing health: {e}")
    
    return [(success, rt, status, error)]

def test_timeout_handling():
    """Test timeout handling"""
    print("\n=== Testing Timeout Handling ===")
    
    # This tests if the server handles long-running requests properly
    results = StressTestResults()
    
    # Send a request that might take longer
    payload = {"query": "complex query that might timeout", "limit": 1000}
    success, rt, status, error = make_request("POST", "/search", data=payload)
    results.add_result(success, rt, status, error)
    print(f"  Long query: {status} ({rt:.1f}ms)")
    
    return results

def run_all_tests():
    """Run all tests and generate report"""
    print("=" * 70)
    print("INTENT ENGINE AIO CONTAINER - COMPREHENSIVE STRESS TEST")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print("=" * 70)
    
    all_results = {
        "health": test_health_endpoints(),
        "intent": test_intent_extraction(),
        "search": test_search_api(),
        "concurrent": test_concurrent_requests(50, 10),
        "edge_cases": test_edge_cases(),
        "large_payloads": test_large_payloads(),
        "rate_limiting": test_rate_limiting(),
        "dependencies": test_service_dependencies(),
        "timeout": test_timeout_handling(),
    }
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_requests = sum(r.total_requests for r in all_results.values() if isinstance(r, StressTestResults))
    total_success = sum(r.successful_requests for r in all_results.values() if isinstance(r, StressTestResults))
    total_failed = sum(r.failed_requests for r in all_results.values() if isinstance(r, StressTestResults))
    
    print(f"\nTotal Requests: {total_requests}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_failed}")
    print(f"Overall Success Rate: {(total_success/total_requests)*100:.1f}%" if total_requests > 0 else "N/A")
    
    # Collect all errors
    all_errors = []
    for name, results in all_results.items():
        if isinstance(results, StressTestResults) and results.errors:
            all_errors.extend([(name, e) for e in results.errors if e])
    
    if all_errors:
        print(f"\nUnique Errors ({len(set(e[1] for e in all_errors))}):")
        for test_name, error in set(all_errors):
            print(f"  - [{test_name}] {error}")
    
    print(f"\nCompleted at: {datetime.now().isoformat()}")
    return all_results

if __name__ == "__main__":
    run_all_tests()
