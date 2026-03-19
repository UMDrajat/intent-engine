#!/usr/bin/env python3
"""
Intent Engine API - Comprehensive Test & Benchmark Suite

This script tests all major API endpoints and provides performance benchmarks.
Run this against a running Docker container.

Usage:
    python test_api_benchmark.py [--host HOST] [--port PORT] [--verbose]

Examples:
    python test_api_benchmark.py
    python test_api_benchmark.py --host localhost --port 80
    python test_api_benchmark.py --verbose
"""

import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests
from tabulate import tabulate


@dataclass
class TestResult:
    """Store test result metrics."""

    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error: Optional[str] = None
    result_count: int = 0
    response_size_bytes: int = 0


@dataclass
class BenchmarkStats:
    """Benchmark statistics for an endpoint."""

    endpoint: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    p95_time_ms: float = 0.0
    p99_time_ms: float = 0.0
    success_rate: float = 0.0
    throughput_rps: float = 0.0
    response_times: list = field(default_factory=list)

    def add_result(self, response_time_ms: float, success: bool):
        self.total_requests += 1
        self.response_times.append(response_time_ms)
        self.total_time_ms += response_time_ms

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.min_time_ms = min(self.min_time_ms, response_time_ms)
        self.max_time_ms = max(self.max_time_ms, response_time_ms)
        self.avg_time_ms = self.total_time_ms / self.total_requests

        # Calculate percentiles
        sorted_times = sorted(self.response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        self.p95_time_ms = (
            sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
        )
        self.p99_time_ms = (
            sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1]
        )

        self.success_rate = (self.successful_requests / self.total_requests) * 100


class APITester:
    """Comprehensive API tester and benchmark tool."""

    def __init__(self, base_url: str = "http://localhost:80", verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.session = requests.Session()
        self.results: list[TestResult] = []
        self.benchmark_stats: dict[str, BenchmarkStats] = {}
        self.issues: list[dict[str, Any]] = []

    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def make_request(self, method: str, endpoint: str, **kwargs) -> TestResult:
        """Make HTTP request and record metrics."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=30, **kwargs)
            elif method.upper() == "POST":
                response = self.session.post(url, timeout=30, **kwargs)
            elif method.upper() == "PUT":
                response = self.session.put(url, timeout=30, **kwargs)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=30, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time_ms = (time.time() - start_time) * 1000

            # Check for errors
            success = 200 <= response.status_code < 300
            error = None if success else f"HTTP {response.status_code}"

            # Count results if applicable
            result_count = 0
            try:
                data = response.json()
                if "results" in data and isinstance(data["results"], list):
                    result_count = len(data["results"])
                elif "items" in data and isinstance(data["items"], list):
                    result_count = len(data["items"])
            except:
                pass

            result = TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                success=success,
                error=error,
                result_count=result_count,
                response_size_bytes=len(response.content),
            )

            self.results.append(result)

            # Update benchmark stats
            if endpoint not in self.benchmark_stats:
                self.benchmark_stats[endpoint] = BenchmarkStats(endpoint=endpoint)
            self.benchmark_stats[endpoint].add_result(response_time_ms, success)

            return result

        except requests.exceptions.Timeout:
            response_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=response_time_ms,
                success=False,
                error="Request timeout",
            )
            self.results.append(result)
            return result

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            result = TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=response_time_ms,
                success=False,
                error=str(e),
            )
            self.results.append(result)
            return result

    def test_health_endpoints(self):
        """Test all health and status endpoints."""
        print("\n" + "=" * 60)
        print("Testing Health & Status Endpoints")
        print("=" * 60)

        endpoints = [
            ("GET", "/", "Root endpoint"),
            ("GET", "/health", "Basic health check"),
            ("GET", "/health/detailed", "Detailed health check"),
            ("GET", "/health/ready", "Readiness probe"),
            ("GET", "/health/live", "Liveness probe"),
            ("GET", "/status", "Service status"),
            ("GET", "/metrics", "Prometheus metrics"),
        ]

        for method, endpoint, description in endpoints:
            print(f"\nTesting {description}: {endpoint}")
            result = self.make_request(method, endpoint)
            status = "✓" if result.success else "✗"
            print(
                f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
            )

            if not result.success:
                self.issues.append(
                    {
                        "type": "health_check_failed",
                        "endpoint": endpoint,
                        "error": result.error,
                        "status_code": result.status_code,
                    }
                )

    def test_intent_extraction(self):
        """Test intent extraction endpoints."""
        print("\n" + "=" * 60)
        print("Testing Intent Extraction Endpoints")
        print("=" * 60)

        test_queries = [
            "best laptop for programming under 50000 rupees",
            "how to learn python for beginners",
            "compare iphone vs samsung",
            "fix python syntax error in for loop",
            "buy gaming laptop",
        ]

        for query in test_queries:
            print(f"\nTesting query: '{query}'")
            payload = {
                "product": "search",
                "input": {"text": query},
                "context": {
                    "sessionId": f"test-{int(time.time())}",
                    "userLocale": "en-US",
                },
            }

            result = self.make_request("POST", "/extract-intent", json=payload)
            status = "✓" if result.success else "✗"
            print(
                f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
            )

            if result.success:
                try:
                    data = (
                        result.json()
                        if hasattr(result, "json")
                        else json.loads(
                            requests.post(
                                f"{self.base_url}/extract-intent", json=payload
                            ).text
                        )
                    )
                    # Check if intent was extracted
                    if "intent" in data:
                        intent = data["intent"]
                        goal = intent.get("declared", {}).get("goal", "UNKNOWN")
                        print(f"     Extracted Goal: {goal}")
                except:
                    pass
            else:
                self.issues.append(
                    {
                        "type": "intent_extraction_failed",
                        "query": query,
                        "error": result.error,
                    }
                )

    def test_search_endpoints(self):
        """Test search and unified search endpoints."""
        print("\n" + "=" * 60)
        print("Testing Search Endpoints")
        print("=" * 60)

        test_queries = [
            {
                "query": "best laptop for programming",
                "extract_intent": True,
                "rank_results": True,
                "max_results": 5,
            },
            {
                "query": "python tutorials for beginners",
                "extract_intent": True,
                "rank_results": False,
                "max_results": 5,
            },
            {
                "query": "compare electric cars 2026",
                "extract_intent": True,
                "rank_results": True,
                "max_results": 5,
            },
            {
                "query": "how to fix memory leak in python",
                "extract_intent": True,
                "rank_results": True,
                "max_results": 5,
            },
            {
                "query": "best budget smartphones",
                "extract_intent": False,
                "rank_results": False,
                "max_results": 5,
            },
        ]

        for payload in test_queries:
            print(f"\nTesting search: '{payload['query']}'")
            result = self.make_request("POST", "/search", json=payload)
            status = "✓" if result.success else "✗"
            print(
                f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms, Results: {result.result_count}"
            )

            # Check for zero results
            if result.success and result.result_count == 0:
                print("  ⚠ WARNING: Zero results returned!")
                self.issues.append(
                    {
                        "type": "zero_results",
                        "endpoint": "/search",
                        "query": payload["query"],
                        "payload": payload,
                    }
                )
            elif result.success and result.result_count < payload.get("max_results", 5):
                print(
                    f"  ⚠ Note: Only {result.result_count} results (expected {payload.get('max_results', 5)})"
                )

    def test_ranking_endpoints(self):
        """Test ranking endpoints."""
        print("\n" + "=" * 60)
        print("Testing Ranking Endpoints")
        print("=" * 60)

        # Test with sample results
        payload = {
            "query": "best python tutorials",
            "results": [
                {
                    "title": "Python for Beginners",
                    "url": "https://python.org/beginners",
                    "content": "Learn Python basics",
                },
                {
                    "title": "Advanced Python",
                    "url": "https://realpython.com",
                    "content": "Advanced Python techniques",
                },
                {
                    "title": "Python Data Science",
                    "url": "https://pandas.pydata.org",
                    "content": "Python for data science",
                },
            ],
            "intent": {
                "declared": {
                    "query": "best python tutorials",
                    "goal": "LEARN",
                    "constraints": [],
                }
            },
            "max_results": 3,
        }

        print(f"\nTesting /rank-results with {len(payload['results'])} results")
        result = self.make_request("POST", "/rank-results", json=payload)
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
        )

        if not result.success:
            self.issues.append(
                {
                    "type": "ranking_failed",
                    "endpoint": "/rank-results",
                    "error": result.error,
                }
            )

    def test_service_recommendation(self):
        """Test service recommendation endpoints."""
        print("\n" + "=" * 60)
        print("Testing Service Recommendation")
        print("=" * 60)

        payload = {
            "intent": {
                "declared": {
                    "query": "how to learn machine learning",
                    "goal": "LEARN",
                    "constraints": [],
                },
                "inferred": {"useCases": ["LEARNING"], "skillLevel": "BEGINNER"},
            },
            "available_services": [
                {
                    "id": "tutorial-service",
                    "type": "EDUCATIONAL",
                    "capabilities": ["LEARNING", "TUTORIALS"],
                },
                {
                    "id": "search-service",
                    "type": "SEARCH",
                    "capabilities": ["INFORMATION_RETRIEVAL"],
                },
                {
                    "id": "forum-service",
                    "type": "COMMUNITY",
                    "capabilities": ["Q&A", "DISCUSSION"],
                },
            ],
        }

        print("\nTesting /recommend-services")
        result = self.make_request("POST", "/recommend-services", json=payload)
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
        )

    def test_ad_matching(self):
        """Test ad matching endpoints."""
        print("\n" + "=" * 60)
        print("Testing Ad Matching")
        print("=" * 60)

        payload = {
            "query": "best laptop for programming",
            "intent": {
                "declared": {
                    "query": "best laptop for programming",
                    "goal": "RESEARCH",
                    "constraints": [],
                }
            },
            "max_ads": 3,
        }

        print("\nTesting /match-ads")
        result = self.make_request("POST", "/match-ads", json=payload)
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms, Ads: {result.result_count}"
        )

    def test_campaign_management(self):
        """Test campaign management endpoints."""
        print("\n" + "=" * 60)
        print("Testing Campaign Management")
        print("=" * 60)

        # Test listing campaigns (should work without creating data)
        print("\nTesting GET /campaigns")
        result = self.make_request("GET", "/campaigns")
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
        )

        # Test listing ads
        print("\nTesting GET /ads")
        result = self.make_request("GET", "/ads")
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
        )

    def test_privacy_endpoints(self):
        """Test privacy and consent endpoints."""
        print("\n" + "=" * 60)
        print("Testing Privacy & Consent Endpoints")
        print("=" * 60)

        # Test consent summary
        print("\nTesting GET /consent-summary")
        result = self.make_request("GET", "/consent-summary")
        status = "✓" if result.success else "✗"
        print(
            f"  {status} Status: {result.status_code}, Time: {result.response_time_ms:.2f}ms"
        )

    def run_benchmark(
        self,
        endpoint: str,
        method: str = "POST",
        payload: dict = None,
        iterations: int = 10,
    ):
        """Run benchmark for a specific endpoint."""
        print(f"\n{'=' * 60}")
        print(f"Benchmarking {endpoint} ({iterations} iterations)")
        print(f"{'=' * 60}")

        for i in range(iterations):
            if payload:
                result = self.make_request(method, endpoint, json=payload)
            else:
                result = self.make_request(method, endpoint)

            if self.verbose:
                status = "✓" if result.success else "✗"
                print(
                    f"  [{i + 1}/{iterations}] {status} {result.response_time_ms:.2f}ms"
                )

            # Small delay between requests
            time.sleep(0.1)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total_tests - passed

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed} ({(passed / total_tests * 100):.1f}%)")
        print(f"Failed: {failed} ({(failed / total_tests * 100):.1f}%)")
        print(
            f"Total Time: {sum(r.response_time_ms for r in self.results) / 1000:.2f}s"
        )

        # Print benchmark stats
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARKS")
        print("=" * 60)

        table_data = []
        for endpoint, stats in sorted(self.benchmark_stats.items()):
            if stats.total_requests > 0:
                table_data.append(
                    [
                        endpoint,
                        stats.total_requests,
                        f"{stats.success_rate:.1f}%",
                        f"{stats.avg_time_ms:.2f}ms",
                        f"{stats.min_time_ms:.2f}ms",
                        f"{stats.max_time_ms:.2f}ms",
                        f"{stats.p95_time_ms:.2f}ms",
                    ]
                )

        if table_data:
            print(
                tabulate(
                    table_data,
                    headers=[
                        "Endpoint",
                        "Requests",
                        "Success Rate",
                        "Avg",
                        "Min",
                        "Max",
                        "P95",
                    ],
                    tablefmt="grid",
                )
            )

    def print_issues(self):
        """Print identified issues."""
        if not self.issues:
            print("\n" + "=" * 60)
            print("NO ISSUES FOUND ✓")
            print("=" * 60)
            return

        print("\n" + "=" * 60)
        print(f"ISSUES FOUND: {len(self.issues)}")
        print("=" * 60)

        # Group issues by type
        issues_by_type = defaultdict(list)
        for issue in self.issues:
            issues_by_type[issue["type"]].append(issue)

        for issue_type, issues in issues_by_type.items():
            print(f"\n{issue_type.upper()} ({len(issues)} occurrences):")
            for issue in issues:
                print(f"  - Endpoint: {issue.get('endpoint', 'N/A')}")
                if "query" in issue:
                    print(f"    Query: {issue['query']}")
                if "error" in issue:
                    print(f"    Error: {issue['error']}")
                if issue.get("type") == "zero_results":
                    print(
                        f"    Payload: {json.dumps(issue.get('payload', {}), indent=6)}"
                    )

    def run_all_tests(self):
        """Run all test suites."""
        print("\n" + "=" * 60)
        print("INTENT ENGINE API - COMPREHENSIVE TEST SUITE")
        print(f"Target: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        print("=" * 60)

        start_time = time.time()

        # Run all test suites
        self.test_health_endpoints()
        self.test_intent_extraction()
        self.test_search_endpoints()
        self.test_ranking_endpoints()
        self.test_service_recommendation()
        self.test_ad_matching()
        self.test_campaign_management()
        self.test_privacy_endpoints()

        # Run benchmarks
        benchmark_payload = {
            "query": "best laptop for programming",
            "extract_intent": True,
            "rank_results": True,
            "max_results": 5,
        }
        self.run_benchmark("/search", "POST", benchmark_payload, iterations=20)

        total_time = time.time() - start_time

        # Print results
        self.print_summary()
        self.print_issues()

        print(f"\n{'=' * 60}")
        print(f"TOTAL EXECUTION TIME: {total_time:.2f}s")
        print(f"{'=' * 60}")

        return len(self.issues) == 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Intent Engine API Test & Benchmark Suite"
    )
    parser.add_argument(
        "--host", default="localhost", help="API host (default: localhost)"
    )
    parser.add_argument("--port", default="80", type=int, help="API port (default: 80)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--benchmark-only", action="store_true", help="Run benchmarks only"
    )

    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print("\nIntent Engine API Test Suite")
    print(f"Target: {base_url}")
    print(f"Verbose: {args.verbose}")
    print(f"Benchmark Only: {args.benchmark_only}")

    # Test connectivity first
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✓ API is reachable")
        else:
            print(f"✗ API returned status {response.status_code}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API at {base_url}")
        print("Make sure the Docker container is running:")
        print("  docker ps | grep intent")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error connecting to API: {e}")
        sys.exit(1)

    # Run tests
    tester = APITester(base_url, verbose=args.verbose)

    if args.benchmark_only:
        benchmark_payload = {
            "query": "best laptop for programming",
            "extract_intent": True,
            "rank_results": True,
            "max_results": 5,
        }
        tester.run_benchmark("/search", "POST", benchmark_payload, iterations=50)
        tester.print_summary()
    else:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
