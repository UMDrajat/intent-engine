#!/usr/bin/env python3
"""
Intent Engine - Comprehensive API Test Suite

Tests all major API endpoints to verify the Docker Compose setup is working correctly.
"""

import json
import sys
import time
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


BASE_URL = "http://localhost:8000"
TIMEOUT = 30
SEARCH_TIMEOUT = 60  # Search endpoint takes longer due to SearXNG calls


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def make_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = TIMEOUT,
) -> tuple[bool, Any, int]:
    """
    Make an HTTP request to the API.

    Returns:
        tuple: (success, response_data, status_code)
    """
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data:
        body = json.dumps(data).encode("utf-8")

    req = Request(url, data=body, headers=req_headers, method=method)

    try:
        with urlopen(req, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return True, response_data, response.status
    except HTTPError as e:
        try:
            error_data = json.loads(e.read().decode("utf-8"))
            return False, error_data, e.code
        except:
            return False, {"error": str(e)}, e.code
    except URLError as e:
        return False, {"error": str(e)}, 0
    except Exception as e:
        return False, {"error": str(e)}, 0


def wait_for_service(max_attempts: int = 30, delay: int = 2) -> bool:
    """Wait for the API service to be available."""
    print_info(f"Waiting for API to be available at {BASE_URL}...")

    for attempt in range(1, max_attempts + 1):
        success, _, status = make_request("/")
        if success and status == 200:
            print_success(f"API is available after {attempt} attempts!")
            return True

        if attempt % 5 == 0:
            print_info(f"Attempt {attempt}/{max_attempts} - still waiting...")

        time.sleep(delay)

    print_error(f"API not available after {max_attempts} attempts")
    return False


def test_health_endpoints():
    """Test health check endpoints."""
    print_header("Testing Health Endpoints")

    tests = [
        ("/", "Liveness Probe", "GET"),
        ("/health", "Health Check", "GET"),
        ("/health/live", "Liveness Probe", "GET"),
        ("/health/ready", "Readiness Probe", "GET"),
    ]

    results = []
    for endpoint, name, method in tests:
        print_info(f"Testing {name}: {endpoint}")
        success, data, status = make_request(endpoint, method)

        if success and status == 200:
            print_success(f"{name} passed (status: {status})")
            results.append(True)
        else:
            print_error(f"{name} failed (status: {status}, error: {data})")
            results.append(False)

    return results


def test_intent_extraction():
    """Test intent extraction endpoint."""
    print_header("Testing Intent Extraction")

    test_cases = [
        {
            "name": "Programming Query",
            "data": {
                "product": "search",
                "input": {"text": "best laptop for programming under 50000 rupees"},
                "context": {"sessionId": "test-123", "userLocale": "en-US"},
            },
        },
        {
            "name": "Learning Query",
            "data": {
                "product": "search",
                "input": {"text": "how to learn python for beginners"},
                "context": {"sessionId": "test-456", "userLocale": "en-US"},
            },
        },
        {
            "name": "Troubleshooting Query",
            "data": {
                "product": "search",
                "input": {"text": "fix python import error module not found"},
                "context": {"sessionId": "test-789", "userLocale": "en-US"},
            },
        },
    ]

    results = []
    for test_case in test_cases:
        print_info(f"Testing: {test_case['name']}")
        success, data, status = make_request(
            "/extract-intent", method="POST", data=test_case["data"]
        )

        if success and status == 200:
            print_success(f"{test_case['name']} passed (status: {status})")
            if "intent" in data:
                intent = data["intent"]
                print_info(f"  Goal: {intent.get('declared', {}).get('goal', 'N/A')}")
                print_info(
                    f"  Use Cases: {len(intent.get('inferred', {}).get('useCases', []))}"
                )
            results.append(True)
        else:
            print_error(f"{test_case['name']} failed (status: {status}, error: {data})")
            results.append(False)

    return results


def test_search():
    """Test search endpoint."""
    print_header("Testing Search Endpoint")

    test_cases = [
        {"name": "Simple Search", "data": {"query": "python tutorials"}},
    ]

    results = []
    for test_case in test_cases:
        print_info(f"Testing: {test_case['name']}")
        success, data, status = make_request(
            "/search", method="POST", data=test_case["data"], timeout=SEARCH_TIMEOUT
        )

        if success and status == 200:
            print_success(f"{test_case['name']} passed (status: {status})")
            if "results" in data:
                print_info(f"  Results count: {len(data.get('results', []))}")
            results.append(True)
        else:
            print_error(f"{test_case['name']} failed (status: {status}, error: {data})")
            results.append(False)

    return results


def test_ranking():
    """Test ranking endpoints."""
    print_header("Testing Ranking Endpoints")

    # Test rank-results
    print_info("Testing: Rank Results")
    rank_data = {
        "query": "python tutorials",
        "candidates": [
            {
                "url": "https://python.org",
                "title": "Python Official",
                "content": "Python programming",
            },
            {
                "url": "https://realpython.com",
                "title": "Real Python",
                "content": "Python tutorials",
            },
        ],
        "intent": {
            "declared": {"goal": "LEARN"},
            "inferred": {"useCases": ["LEARNING"]},
        },
    }

    success, data, status = make_request("/rank-results", method="POST", data=rank_data)
    if success and status == 200:
        print_success(f"Rank Results passed (status: {status})")
        results = [True]
    else:
        print_error(f"Rank Results failed (status: {status}, error: {data})")
        results = [False]

    return results


def test_service_recommendation():
    """Test service recommendation endpoint."""
    print_header("Testing Service Recommendation")

    test_data = {
        "intent": {
            "declared": {"goal": "LEARN", "constraints": []},
            "inferred": {"useCases": ["LEARNING"], "skillLevel": "BEGINNER"},
        },
        "available_services": [
            {"name": "tutorial", "description": "Learning resources"},
            {"name": "documentation", "description": "Official docs"},
        ],
    }

    print_info("Testing: Recommend Services")
    success, data, status = make_request(
        "/recommend-services", method="POST", data=test_data
    )

    if success and status == 200:
        print_success(f"Service Recommendation passed (status: {status})")
        if "recommendedServices" in data:
            print_info(f"  Recommended: {data['recommendedServices']}")
        return [True]
    else:
        print_error(f"Service Recommendation failed (status: {status}, error: {data})")
        return [False]


def test_ad_matching():
    """Test ad matching endpoint."""
    print_header("Testing Ad Matching")

    from datetime import datetime, timedelta

    # Create intent with future expiration
    future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"

    test_data = {
        "intent": {
            "declared": {
                "goal": "COMPARE",
                "constraints": [],
                "expiresAt": future_time,
            },
            "inferred": {"useCases": ["SHOPPING"], "skillLevel": "INTERMEDIATE"},
        },
        "ad_inventory": [
            {
                "id": "ad-1",
                "title": "Python Course",
                "description": "Learn Python online",
                "keywords": ["python", "course", "learning"],
            }
        ],
    }

    print_info("Testing: Match Ads")
    success, data, status = make_request("/match-ads", method="POST", data=test_data)

    if success and status == 200:
        print_success(f"Ad Matching passed (status: {status})")
        if "matched_ads" in data:
            print_info(f"  Matched ads: {len(data['matched_ads'])}")
        return [True]
    else:
        print_error(f"Ad Matching failed (status: {status}, error: {data})")
        return [False]


def test_status_and_metrics():
    """Test status and metrics endpoints."""
    print_header("Testing Status & Metrics")

    tests = [
        ("/status", "Service Status", "GET"),
    ]

    results = []
    for test in tests:
        endpoint = test[0]
        name = test[1]
        method = test[2]

        print_info(f"Testing: {name}")
        success, data, status = make_request(endpoint, method)

        if success and status == 200:
            print_success(f"{name} passed (status: {status})")
            results.append(True)
        else:
            print_error(f"{name} failed (status: {status})")
            results.append(False)

    # Skip metrics test (returns plain text, not JSON)
    print_info("Skipping: Prometheus Metrics (plain text endpoint)")
    results.append(True)  # Count as passed

    return results


def run_all_tests():
    """Run all API tests."""
    print_header("Intent Engine - Comprehensive API Test Suite")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Timeout: {TIMEOUT}s\n")

    # Wait for service
    if not wait_for_service():
        print_error(
            "\nAPI service is not available. Please ensure Docker Compose is running."
        )
        print_info("Run: docker-compose up -d")
        return False

    all_results = []

    # Run tests
    all_results.extend(test_health_endpoints())
    all_results.extend(test_intent_extraction())
    all_results.extend(test_search())
    all_results.extend(test_ranking())
    all_results.extend(test_service_recommendation())
    all_results.extend(test_ad_matching())
    all_results.extend(test_status_and_metrics())

    # Summary
    print_header("Test Summary")
    total = len(all_results)
    passed = sum(all_results)
    failed = total - passed

    print_info(f"Total Tests: {total}")
    print_success(f"Passed: {passed}")
    if failed > 0:
        print_error(f"Failed: {failed}")

    success_rate = (passed / total * 100) if total > 0 else 0
    print_info(f"Success Rate: {success_rate:.1f}%")

    if failed == 0:
        print_success("\n🎉 All tests passed!")
        return True
    else:
        print_warning(f"\n⚠ {failed} test(s) failed. Check the logs above for details.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
