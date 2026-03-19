#!/usr/bin/env python3
"""
Intent Engine - Quick API Test

A lightweight test to verify the Docker Compose setup is working.
"""

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000"


def test_endpoint(name, endpoint, method="GET", data=None):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data else None

    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"✓ {name}: {response.status}")
            return True, result
    except HTTPError as e:
        print(f"✗ {name}: {e.code}")
        return False, str(e)
    except URLError as e:
        print(f"✗ {name}: {e.reason}")
        return False, str(e)


def main():
    print("=" * 50)
    print("Intent Engine - Quick API Test")
    print("=" * 50)
    print()

    tests = [
        ("Liveness", "/", "GET", None),
        ("Health", "/health", "GET", None),
        (
            "Intent Extraction",
            "/extract-intent",
            "POST",
            {
                "product": "search",
                "input": {"text": "best laptop for programming"},
                "context": {"sessionId": "test-123"},
            },
        ),
        ("Search", "/search", "POST", {"query": "python tutorials"}),
        ("Status", "/status", "GET", None),
    ]

    results = []
    for name, endpoint, method, data in tests:
        print(f"Testing {name}...", end=" ")
        success, _ = test_endpoint(name, endpoint, method, data)
        results.append(success)
        if name == "Search":
            print("  (Note: First search may take 30-40 seconds)")

    print()
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")
    print("=" * 50)

    if passed == total:
        print("\n✓ All tests passed! Docker Compose setup is working.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
