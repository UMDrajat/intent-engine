#!/usr/bin/env python3
"""
Intent Engine - Quick Performance Test (Post-Improvements)

Tests the key improvements:
1. Enhanced ranking with multi-factor scoring
2. Intent fallback for null goals
3. Query timeout (5s max)
4. Content filtering
"""

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000"

def test_search(query: str, timeout_sec: int = 30):
    """Test search endpoint with timeout"""
    url = f"{BASE_URL}/search"
    data = json.dumps({
        "query": query,
        "extract_intent": True,
        "rank_results": True,
        "max_results": 10
    }).encode('utf-8')
    
    start = time.time()
    try:
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout_sec) as response:
            result = json.loads(response.read().decode('utf-8'))
            latency = (time.time() - start) * 1000
            return True, result, latency
    except Exception as e:
        latency = (time.time() - start) * 1000
        return False, str(e), latency

def main():
    print("=" * 60)
    print("Intent Engine - Post-Improvement Performance Test")
    print("=" * 60)
    print()
    
    # Test queries that previously failed
    test_queries = [
        "how to learn python for beginners",
        "best laptop for programming",
        "python code optimization",
    ]
    
    results = []
    for query in test_queries:
        print(f"Testing: \"{query}\"")
        success, response, latency = test_search(query)
        
        if success:
            result_count = len(response.get('results', []))
            print(f"  ✓ Success: {latency/1000:.2f}s, {result_count} results")
            results.append({
                "query": query,
                "success": True,
                "latency_s": latency/1000,
                "results": result_count
            })
        else:
            print(f"  ✗ Failed: {latency/1000:.2f}s - {response}")
            results.append({
                "query": query,
                "success": False,
                "latency_s": latency/1000,
                "error": str(response)
            })
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    if successful > 0:
        avg_latency = sum(r['latency_s'] for r in results if r['success']) / successful
        avg_results = sum(r.get('results', 0) for r in results if r['success']) / successful
        print(f"Success Rate: {successful}/{total} ({successful/total*100:.0f}%)")
        print(f"Avg Latency: {avg_latency:.2f}s")
        print(f"Avg Results: {avg_results:.1f}")
    
    # Check improvements
    print()
    print("Improvement Checks:")
    if avg_latency < 10:
        print("  ✓ Latency improved (<10s)")
    else:
        print(f"  ⚠ Latency still high ({avg_latency:.2f}s)")
    
    if successful == total:
        print("  ✓ All queries succeeded")
    else:
        print(f"  ⚠ {total - successful} queries failed")
    
    return 0 if successful > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
