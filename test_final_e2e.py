#!/usr/bin/env python3
"""
Intent Engine - Final End-to-End Test Report
"""

import json
import sys
import time
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8000"


def test_endpoint(name, endpoint, method="GET", data=None, timeout=30):
    """Test endpoint and return result"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None

    start = time.time()
    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            latency = (time.time() - start) * 1000
            return True, result, latency
    except Exception as e:
        latency = (time.time() - start) * 1000
        return False, str(e), latency


def main():
    print("=" * 70)
    print("Intent Engine - Final End-to-End Test Report")
    print("=" * 70)
    print()

    results = []

    # Test 1: Health
    print("1. Testing Health Endpoint...")
    success, data, latency = test_endpoint("Health", "/health")
    print(f"   {'✓' if success else '✗'} {latency / 1000:.2f}s")
    results.append(("Health", success, latency))

    # Test 2: Intent Extraction
    print("2. Testing Intent Extraction...")
    success, data, latency = test_endpoint(
        "Intent Extraction",
        "/extract-intent",
        "POST",
        {
            "product": "search",
            "input": {"text": "best python tutorial"},
            "context": {"sessionId": "test"},
        },
    )
    goal = (
        data.get("intent", {}).get("declared", {}).get("goal", "unknown")
        if success
        else "N/A"
    )
    print(f"   {'✓' if success else '✗'} {latency / 1000:.2f}s - Goal: {goal}")
    results.append(("Intent Extraction", success, latency))

    # Test 3: Search (with longer timeout)
    print("3. Testing Search (may take 5-15s)...")
    success, data, latency = test_endpoint(
        "Search",
        "/search",
        "POST",
        {"query": "python tutorial", "max_results": 5},
        timeout=60,
    )
    result_count = len(data.get("results", [])) if success else 0
    processing_time = data.get("processing_time_ms", 0) / 1000 if success else 0
    print(
        f"   {'✓' if success else '✗'} {latency / 1000:.2f}s - {result_count} results (API: {processing_time:.2f}s)"
    )
    results.append(("Search", success, latency))

    # Test 4: Cache Stats
    print("4. Testing Cache Stats...")
    success, data, latency = test_endpoint("Cache Stats", "/cache/stats")
    hit_rate = data.get("cache_stats", {}).get("hit_rate_percent", 0) if success else 0
    print(f"   {'✓' if success else '✗'} {latency / 1000:.2f}s - Hit Rate: {hit_rate}%")
    results.append(("Cache Stats", success, latency))

    # Test 5: Status
    print("5. Testing Status...")
    success, data, latency = test_endpoint("Status", "/status")
    version = data.get("version", "unknown") if success else "N/A"
    print(f"   {'✓' if success else '✗'} {latency / 1000:.2f}s - Version: {version}")
    results.append(("Status", success, latency))

    # Summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for _, success, _ in results if success)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed / total * 100:.0f}%")
    print()

    # Performance summary
    latencies = [lat for _, success, lat in results if success]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average Latency: {avg_latency / 1000:.2f}s")

    # Search-specific metrics
    search_results = [r for r in results if r[0] == "Search" and r[1]]
    if search_results:
        _, _, search_latency = search_results[0]
        print(f"Search Latency: {search_latency / 1000:.2f}s")

    print()
    if passed == total:
        print("✅ All tests passed! Docker Compose setup is working correctly.")
        return 0
    else:
        print(f"⚠️ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
