#!/usr/bin/env python3
"""
Intent Engine - Complete API Test Suite

Tests ALL API endpoints comprehensively:
- Health & Status
- Intent Extraction
- Search
- Ranking
- Service Recommendation
- Ad Matching
- Cache Management
- Privacy & Compliance
- Campaign Management
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def make_request(
    endpoint: str, method: str = "GET", data: dict = None, timeout: int = TIMEOUT
) -> Tuple[bool, Any, float]:
    """Make HTTP request and return (success, response, latency_ms)"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None

    start_time = time.time()
    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            latency_ms = (time.time() - start_time) * 1000
            return True, response_data, latency_ms
    except HTTPError as e:
        latency_ms = (time.time() - start_time) * 1000
        try:
            error_data = json.loads(e.read().decode("utf-8"))
            return False, error_data, latency_ms
        except:
            return False, {"error": str(e)}, latency_ms
    except URLError as e:
        latency_ms = (time.time() - start_time) * 1000
        return False, {"error": str(e)}, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return False, {"error": str(e)}, latency_ms


# =============================================================================
# Test Categories
# =============================================================================


def test_health_endpoints() -> List[Tuple[str, bool, float]]:
    """Test all health and status endpoints"""
    print_header("Testing Health & Status Endpoints")

    tests = [
        ("Liveness Probe", "/", "GET", None),
        ("Health Check", "/health", "GET", None),
        ("Liveness Probe", "/health/live", "GET", None),
        ("Readiness Probe", "/health/ready", "GET", None),
        ("Service Status", "/status", "GET", None),
    ]

    results = []
    for name, endpoint, method, data in tests:
        print(f"Testing {name}...", end=" ")
        success, response, latency = make_request(endpoint, method, data, timeout=10)

        if success:
            print_success(f"{latency / 1000:.2f}s")
            results.append((name, True, latency))
        else:
            print_warning(f"{latency / 1000:.2f}s - {response.get('status', 'error')}")
            results.append((name, False, latency))

    return results


def test_intent_extraction() -> List[Tuple[str, bool, float]]:
    """Test intent extraction with various queries"""
    print_header("Testing Intent Extraction")

    test_cases = [
        ("Programming Query", "best laptop for programming under 50000"),
        ("Learning Query", "how to learn python for beginners"),
        ("Troubleshooting", "fix python import error module not found"),
        ("Comparison", "vscode vs pycharm for python"),
        ("Career", "how to become a data scientist"),
    ]

    results = []
    for name, query in test_cases:
        print(f"Testing {name}...", end=" ")
        success, response, latency = make_request(
            "/extract-intent",
            "POST",
            {
                "product": "search",
                "input": {"text": query},
                "context": {
                    "sessionId": f"test-{int(time.time())}",
                    "userLocale": "en-US",
                },
            },
        )

        if success:
            goal = response.get("intent", {}).get("declared", {}).get("goal", "unknown")
            print_success(f"{latency / 1000:.2f}s - Goal: {goal}")
            results.append((name, True, latency))
        else:
            print_error(f"{latency / 1000:.2f}s - Failed")
            results.append((name, False, latency))

    return results


def test_search() -> List[Tuple[str, bool, float]]:
    """Test search endpoint"""
    print_header("Testing Search Endpoint")

    test_cases = [
        ("Simple Search", {"query": "python tutorial", "max_results": 5}),
        (
            "With Intent",
            {
                "query": "best programming laptop",
                "extract_intent": True,
                "max_results": 5,
            },
        ),
        (
            "With Ranking",
            {"query": "python web frameworks", "rank_results": True, "max_results": 5},
        ),
    ]

    results = []
    for name, data in test_cases:
        print(f"Testing {name}...", end=" ")
        success, response, latency = make_request("/search", "POST", data, timeout=60)

        if success:
            result_count = len(response.get("results", []))
            processing_time = response.get("processing_time_ms", 0) / 1000
            print_success(
                f"{latency / 1000:.2f}s - {result_count} results (API: {processing_time:.2f}s)"
            )
            results.append((name, True, latency))
        else:
            print_error(
                f"{latency / 1000:.2f}s - {str(response.get('error', 'Failed'))[:50]}"
            )
            results.append((name, False, latency))

    return results


def test_ranking() -> List[Tuple[str, bool, float]]:
    """Test ranking endpoints"""
    print_header("Testing Ranking Endpoints")

    results = []

    # Test rank-results
    print("Testing Rank Results...", end=" ")
    success, response, latency = make_request(
        "/rank-results",
        "POST",
        {
            "query": "python tutorials",
            "candidates": [
                {
                    "url": "https://python.org",
                    "title": "Python Official",
                    "content": "Python programming language",
                },
                {
                    "url": "https://realpython.com",
                    "title": "Real Python",
                    "content": "Python tutorials",
                },
            ],
            "intent": {
                "declared": {"goal": "learn", "query": "python tutorials"},
                "inferred": {"useCases": ["learning"]},
            },
        },
    )

    if success:
        print_success(f"{latency / 1000:.2f}s")
        results.append(("Rank Results", True, latency))
    else:
        print_error(f"{latency / 1000:.2f}s")
        results.append(("Rank Results", False, latency))

    return results


def test_service_recommendation() -> List[Tuple[str, bool, float]]:
    """Test service recommendation"""
    print_header("Testing Service Recommendation")

    results = []
    print("Testing Recommend Services...", end=" ")
    success, response, latency = make_request(
        "/recommend-services",
        "POST",
        {
            "intent": {
                "declared": {"goal": "learn", "constraints": []},
                "inferred": {"useCases": ["learning"], "skillLevel": "BEGINNER"},
            },
            "available_services": [
                {"name": "tutorial", "description": "Learning resources"},
                {"name": "documentation", "description": "Official docs"},
            ],
        },
    )

    if success:
        print_success(f"{latency / 1000:.2f}s")
        results.append(("Service Recommendation", True, latency))
    else:
        print_error(f"{latency / 1000:.2f}s")
        results.append(("Service Recommendation", False, latency))

    return results


def test_ad_matching() -> List[Tuple[str, bool, float]]:
    """Test ad matching"""
    print_header("Testing Ad Matching")

    results = []
    print("Testing Match Ads...", end=" ")
    success, response, latency = make_request(
        "/match-ads",
        "POST",
        {
            "intent": {
                "declared": {
                    "goal": "compare",
                    "constraints": [],
                    "expiresAt": (datetime.utcnow() + timedelta(hours=1)).isoformat()
                    + "Z",
                },
                "inferred": {"useCases": ["shopping"], "skillLevel": "INTERMEDIATE"},
            },
            "ad_inventory": [
                {
                    "id": "ad-1",
                    "title": "Python Course",
                    "description": "Learn Python online",
                    "keywords": ["python", "course", "learning"],
                }
            ],
        },
    )

    if success:
        matched_count = len(response.get("matched_ads", []))
        print_success(f"{latency / 1000:.2f}s - {matched_count} ads matched")
        results.append(("Ad Matching", True, latency))
    else:
        print_error(
            f"{latency / 1000:.2f}s - {str(response.get('detail', 'Failed'))[:50]}"
        )
        results.append(("Ad Matching", False, latency))

    return results


def test_cache_management() -> List[Tuple[str, bool, float]]:
    """Test cache management endpoints"""
    print_header("Testing Cache Management")

    tests = [
        ("Cache Stats", "/cache/stats", "GET", None),
        ("Cache Warm", "/cache/warm", "POST", {"queries": ["test query"]}),
    ]

    results = []
    for name, endpoint, method, data in tests:
        print(f"Testing {name}...", end=" ")
        success, response, latency = make_request(endpoint, method, data, timeout=10)

        if success:
            print_success(f"{latency / 1000:.2f}s")
            results.append((name, True, latency))
        else:
            print_error(f"{latency / 1000:.2f}s")
            results.append((name, False, latency))

    return results


def test_campaign_management() -> List[Tuple[str, bool, float]]:
    """Test campaign management endpoints"""
    print_header("Testing Campaign Management")

    results = []

    # Test create advertiser
    print("Testing Create Advertiser...", end=" ")
    success, response, latency = make_request(
        "/advertisers",
        "POST",
        {
            "name": f"Test Advertiser {int(time.time())}",
            "email": "test@example.com",
            "company": "Test Company",
        },
    )

    if success:
        print_success(f"{latency / 1000:.2f}s")
        results.append(("Create Advertiser", True, latency))
    else:
        print_error(f"{latency / 1000:.2f}s")
        results.append(("Create Advertiser", False, latency))

    # Test list advertisers
    print("Testing List Advertisers...", end=" ")
    success, response, latency = make_request("/advertisers", "GET")

    if success:
        count = len(response) if isinstance(response, list) else 0
        print_success(f"{latency / 1000:.2f}s - {count} advertisers")
        results.append(("List Advertisers", True, latency))
    else:
        print_error(f"{latency / 1000:.2f}s")
        results.append(("List Advertisers", False, latency))

    return results


def test_privacy_endpoints() -> List[Tuple[str, bool, float]]:
    """Test privacy and compliance endpoints"""
    print_header("Testing Privacy & Compliance")

    results = []

    # Test consent summary
    print("Testing Consent Summary...", end=" ")
    success, response, latency = make_request("/consent-summary", "GET")

    if success:
        print_success(f"{latency / 1000:.2f}s")
        results.append(("Consent Summary", True, latency))
    else:
        print_error(f"{latency / 1000:.2f}s")
        results.append(("Consent Summary", False, latency))

    return results


def generate_final_report(all_results: Dict[str, List[Tuple[str, bool, float]]]):
    """Generate comprehensive test report"""
    print_header("Final Test Report")

    total_tests = 0
    total_passed = 0
    total_latency = 0

    print(
        f"{'Category':<30} {'Tests':<8} {'Passed':<8} {'Failed':<8} {'Success':<10} {'Avg Latency':<12}"
    )
    print("-" * 84)

    for category, results in all_results.items():
        tests = len(results)
        passed = sum(1 for _, success, _ in results if success)
        failed = tests - passed
        success_rate = (passed / tests * 100) if tests > 0 else 0
        avg_latency = sum(lat for _, success, lat in results if success) / max(
            passed, 1
        )

        total_tests += tests
        total_passed += passed
        total_latency += sum(lat for _, success, lat in results if success)

        print(
            f"{category:<30} {tests:<8} {passed:<8} {failed:<8} {success_rate:>5.0f}%      {avg_latency / 1000:>6.2f}s"
        )

    print("-" * 84)
    overall_success = (total_passed / total_tests * 100) if total_tests > 0 else 0
    overall_latency = total_latency / max(total_passed, 1)
    print(
        f"{'TOTAL':<30} {total_tests:<8} {total_passed:<8} {total_tests - total_passed:<8} {overall_success:>5.0f}%      {overall_latency / 1000:>6.2f}s"
    )
    print()

    # Overall rating
    if overall_success >= 90:
        rating = "⭐⭐⭐⭐⭐ Excellent"
    elif overall_success >= 70:
        rating = "⭐⭐⭐⭐ Good"
    elif overall_success >= 50:
        rating = "⭐⭐⭐ Fair"
    else:
        rating = "⭐⭐ Needs Improvement"

    print(f"Overall Success Rate: {overall_success:.0f}%")
    print(f"Overall Rating: {rating}")
    print()

    if overall_success >= 80:
        print_success("✅ API is fully functional!")
    elif overall_success >= 50:
        print_warning("⚠️ API has some issues but core functionality works")
    else:
        print_error("❌ API has critical issues")

    return overall_success >= 80


def main():
    """Run all API tests"""
    print_header("Intent Engine - Complete API Test Suite")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Wait for API to be available
    print_info("Waiting for API to be available...")
    for attempt in range(1, 11):
        success, _, _ = make_request("/", timeout=5)
        if success:
            print_success(f"API available after {attempt} attempts!")
            break
        print_info(f"Attempt {attempt}/10 - waiting...")
        time.sleep(2)
    else:
        print_error("API not available after 10 attempts")
        return 1

    # Run all test categories
    all_results = {}

    all_results["Health & Status"] = test_health_endpoints()
    all_results["Intent Extraction"] = test_intent_extraction()
    all_results["Search"] = test_search()
    all_results["Ranking"] = test_ranking()
    all_results["Service Recommendation"] = test_service_recommendation()
    all_results["Ad Matching"] = test_ad_matching()
    all_results["Cache Management"] = test_cache_management()
    all_results["Campaign Management"] = test_campaign_management()
    all_results["Privacy & Compliance"] = test_privacy_endpoints()

    # Generate final report
    success = generate_final_report(all_results)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
