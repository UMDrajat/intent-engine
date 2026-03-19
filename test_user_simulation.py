#!/usr/bin/env python3
"""
Intent Engine - User Simulation & Quality Test

Simulates real user behavior and measures:
- Latency (response times)
- Search quality (relevance scoring)
- Success rates
- User experience metrics
"""

import json
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://localhost:8000"

# =============================================================================
# Test Scenarios (Real User Queries)
# =============================================================================

TEST_QUERIES = [
    {
        "category": "Programming Tutorial",
        "query": "how to learn python for beginners",
        "expected_intent": "learn",
        "expected_topics": ["python", "tutorial", "beginner", "learning"]
    },
    {
        "category": "Product Comparison",
        "query": "best laptop for programming under 50000 rupees",
        "expected_intent": "comparison",
        "expected_topics": ["laptop", "programming", "budget", "comparison"]
    },
    {
        "category": "Troubleshooting",
        "query": "fix python import error module not found",
        "expected_intent": "programming_error",
        "expected_topics": ["python", "error", "debugging", "import"]
    },
    {
        "category": "Web Development",
        "query": "best python web frameworks for REST API",
        "expected_intent": "comparison",
        "expected_topics": ["python", "web", "framework", "API", "REST"]
    },
    {
        "category": "Data Science",
        "query": "machine learning tutorials with python examples",
        "expected_intent": "learn",
        "expected_topics": ["machine learning", "python", "tutorial", "examples"]
    },
    {
        "category": "Career Development",
        "query": "how to become a data scientist in 2026",
        "expected_intent": "learn",
        "expected_topics": ["career", "data scientist", "skills", "learning path"]
    },
    {
        "category": "Tool Comparison",
        "query": "vscode vs pycharm for python development",
        "expected_intent": "comparison",
        "expected_topics": ["vscode", "pycharm", "IDE", "comparison"]
    },
    {
        "category": "Best Practices",
        "query": "python code optimization techniques",
        "expected_intent": "learn",
        "expected_topics": ["python", "optimization", "performance", "best practices"]
    }
]


class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


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


def make_request(endpoint: str, method: str = "GET", data: dict = None, timeout: int = 60) -> Tuple[bool, Any, float]:
    """Make HTTP request and return (success, response, latency_ms)."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode('utf-8') if data else None
    
    start_time = time.time()
    try:
        req = Request(url, data=body, headers=headers, method=method)
        with urlopen(req, timeout=timeout) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            latency_ms = (time.time() - start_time) * 1000
            return True, response_data, latency_ms
    except HTTPError as e:
        latency_ms = (time.time() - start_time) * 1000
        try:
            error_data = json.loads(e.read().decode('utf-8'))
            return False, error_data, latency_ms
        except:
            return False, {"error": str(e)}, latency_ms
    except URLError as e:
        latency_ms = (time.time() - start_time) * 1000
        return False, {"error": str(e)}, latency_ms
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return False, {"error": str(e)}, latency_ms


def rate_search_results(results: List[dict], query: str, expected_topics: List[str]) -> Dict[str, Any]:
    """Rate search result quality."""
    if not results:
        return {
            "relevance_score": 0,
            "topic_coverage": 0,
            "result_count": 0,
            "avg_title_length": 0,
            "has_descriptions": 0
        }
    
    # Check topic coverage
    query_lower = query.lower()
    topics_found = 0
    for topic in expected_topics:
        if topic.lower() in query_lower:
            topics_found += 1
    
    topic_coverage = topics_found / len(expected_topics) if expected_topics else 0
    
    # Check result quality
    total_score = 0
    has_descriptions = 0
    title_lengths = []
    
    for result in results[:10]:  # Check top 10
        title = result.get('title', '').lower()
        content = result.get('content', result.get('snippet', '')).lower()
        
        # Score based on topic presence
        result_score = 0
        for topic in expected_topics:
            if topic.lower() in title or topic.lower() in content:
                result_score += 1
                topics_found += 1
        
        total_score += result_score
        
        if result.get('content') or result.get('snippet'):
            has_descriptions += 1
        
        if result.get('title'):
            title_lengths.append(len(result['title']))
    
    relevance_score = min(10, total_score / len(results) * 2) if results else 0
    
    return {
        "relevance_score": round(relevance_score, 2),
        "topic_coverage": round(topic_coverage, 2),
        "result_count": len(results),
        "avg_title_length": round(statistics.mean(title_lengths), 1) if title_lengths else 0,
        "has_descriptions": round(has_descriptions / len(results) * 100, 1) if results else 0
    }


def test_intent_extraction(query_data: dict) -> Dict[str, Any]:
    """Test intent extraction endpoint."""
    payload = {
        "product": "search",
        "input": {"text": query_data["query"]},
        "context": {"sessionId": f"test-{int(time.time())}", "userLocale": "en-US"}
    }
    
    success, response, latency = make_request("/extract-intent", "POST", payload)
    
    if not success:
        return {
            "success": False,
            "latency_ms": latency,
            "error": response
        }
    
    intent = response.get('intent', {})
    declared = intent.get('declared', {})
    inferred = intent.get('inferred', {})
    
    goal = declared.get('goal', 'unknown')
    goal_match = goal.lower() == query_data["expected_intent"].lower() if goal else False
    
    use_cases = inferred.get('useCases', [])
    skill_level = inferred.get('skillLevel', 'unknown')
    
    return {
        "success": True,
        "latency_ms": round(latency, 2),
        "goal": goal,
        "goal_match": goal_match,
        "use_cases": len(use_cases),
        "skill_level": skill_level,
        "constraints": len(declared.get('constraints', []))
    }


def test_search(query_data: dict) -> Dict[str, Any]:
    """Test search endpoint."""
    payload = {
        "query": query_data["query"],
        "extract_intent": True,
        "rank_results": True,
        "max_results": 10
    }
    
    success, response, latency = make_request("/search", "POST", payload, timeout=60)
    
    if not success:
        return {
            "success": False,
            "latency_ms": latency,
            "error": response
        }
    
    results = response.get('results', [])
    quality_metrics = rate_search_results(results, query_data["query"], query_data["expected_topics"])
    
    intent_extracted = response.get('intent') is not None
    
    return {
        "success": True,
        "latency_ms": round(latency, 2),
        "result_count": len(results),
        "intent_extracted": intent_extracted,
        "quality": quality_metrics
    }


def simulate_user_session(user_id: str, queries: List[dict]) -> Dict[str, Any]:
    """Simulate a complete user session."""
    session_start = time.time()
    results = []
    
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.CYAN}User Session: {user_id}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")
    
    for i, query_data in enumerate(queries, 1):
        print(f"{Colors.BOLD}Query {i}/{len(queries)}: {query_data['category']}{Colors.ENDC}")
        print(f"Query: \"{query_data['query']}\"")
        
        # Test intent extraction
        print("  Testing intent extraction...", end=" ")
        intent_result = test_intent_extraction(query_data)
        if intent_result['success']:
            print_success(f"{intent_result['latency_ms']}ms - Goal: {intent_result['goal']}")
        else:
            print_error(f"Failed: {intent_result.get('error', {})}")
        
        # Test search
        print("  Testing search...", end=" ")
        search_result = test_search(query_data)
        if search_result['success']:
            quality = search_result['quality']
            print_success(f"{search_result['latency_ms']}ms - {search_result['result_count']} results - Quality: {quality['relevance_score']}/10")
        else:
            print_error(f"Failed: {search_result.get('error', {})}")
        
        results.append({
            "query": query_data,
            "intent": intent_result,
            "search": search_result
        })
        print()
    
    session_duration = time.time() - session_start
    
    # Calculate session metrics
    successful_intents = sum(1 for r in results if r['intent']['success'])
    successful_searches = sum(1 for r in results if r['search']['success'])
    
    intent_latencies = [r['intent']['latency_ms'] for r in results if r['intent']['success']]
    search_latencies = [r['search']['latency_ms'] for r in results if r['search']['success']]
    
    quality_scores = [r['search']['quality']['relevance_score'] for r in results if r['search']['success']]
    
    return {
        "user_id": user_id,
        "duration_seconds": round(session_duration, 2),
        "total_queries": len(queries),
        "successful_intents": successful_intents,
        "successful_searches": successful_searches,
        "intent_accuracy": round(successful_intents / len(queries) * 100, 1) if queries else 0,
        "search_success_rate": round(successful_searches / len(queries) * 100, 1) if queries else 0,
        "avg_intent_latency_ms": round(statistics.mean(intent_latencies), 2) if intent_latencies else 0,
        "avg_search_latency_ms": round(statistics.mean(search_latencies), 2) if search_latencies else 0,
        "p95_intent_latency_ms": round(statistics.quantiles(intent_latencies, n=100)[94], 2) if len(intent_latencies) > 1 else 0,
        "p95_search_latency_ms": round(statistics.quantiles(search_latencies, n=100)[94], 2) if len(search_latencies) > 1 else 0,
        "avg_quality_score": round(statistics.mean(quality_scores), 2) if quality_scores else 0,
        "results": results
    }


def generate_report(sessions: List[dict]) -> str:
    """Generate a comprehensive test report."""
    total_queries = sum(s['total_queries'] for s in sessions)
    total_duration = sum(s['duration_seconds'] for s in sessions)
    
    all_intent_latencies = []
    all_search_latencies = []
    all_quality_scores = []
    
    for session in sessions:
        for result in session['results']:
            if result['intent']['success']:
                all_intent_latencies.append(result['intent']['latency_ms'])
            if result['search']['success']:
                all_search_latencies.append(result['search']['latency_ms'])
                all_quality_scores.append(result['search']['quality']['relevance_score'])
    
    report = f"""
# Intent Engine - User Simulation Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Test Duration:** {total_duration:.2f} seconds  
**Total Queries:** {total_queries}

---

## 📊 Overall Metrics

| Metric | Value | Rating |
|--------|-------|--------|
| **Intent Extraction Accuracy** | {statistics.mean([s['intent_accuracy'] for s in sessions]):.1f}% | {'✅ Excellent' if statistics.mean([s['intent_accuracy'] for s in sessions]) > 90 else '⚠️ Good' if statistics.mean([s['intent_accuracy'] for s in sessions]) > 70 else '❌ Needs Improvement'} |
| **Search Success Rate** | {statistics.mean([s['search_success_rate'] for s in sessions]):.1f}% | {'✅ Excellent' if statistics.mean([s['search_success_rate'] for s in sessions]) > 90 else '⚠️ Good' if statistics.mean([s['search_success_rate'] for s in sessions]) > 70 else '❌ Needs Improvement'} |
| **Avg Search Quality** | {statistics.mean(all_quality_scores):.2f}/10 | {'✅ Excellent' if statistics.mean(all_quality_scores) > 7 else '⚠️ Good' if statistics.mean(all_quality_scores) > 5 else '❌ Needs Improvement'} |

---

## ⏱️ Latency Metrics

### Intent Extraction

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Average** | {statistics.mean(all_intent_latencies):.2f}ms | <100ms | {'✅ Pass' if statistics.mean(all_intent_latencies) < 100 else '❌ Fail'} |
| **P95** | {statistics.quantiles(all_intent_latencies, n=100)[94]:.2f}ms | <200ms | {'✅ Pass' if statistics.quantiles(all_intent_latencies, n=100)[94] < 200 else '❌ Fail'} |
| **Min** | {min(all_intent_latencies):.2f}ms | - | - |
| **Max** | {max(all_intent_latencies):.2f}ms | - | - |

### Search

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Average** | {statistics.mean(all_search_latencies):.2f}ms | <5000ms | {'✅ Pass' if statistics.mean(all_search_latencies) < 5000 else '⚠️ Warning'} |
| **P95** | {statistics.quantiles(all_search_latencies, n=100)[94]:.2f}ms | <10000ms | {'✅ Pass' if statistics.quantiles(all_search_latencies, n=100)[94] < 10000 else '⚠️ Warning'} |
| **Min** | {min(all_search_latencies):.2f}ms | - | - |
| **Max** | {max(all_search_latencies):.2f}ms | - | - |

---

## 🎯 Search Quality Analysis

### By Category

"""
    
    # Group by category
    category_metrics = {}
    for session in sessions:
        for result in session['results']:
            if result['search']['success']:
                category = result['query']['category']
                if category not in category_metrics:
                    category_metrics[category] = []
                category_metrics[category].append(result['search']['quality']['relevance_score'])
    
    report += "| Category | Avg Quality | Results | Rating |\n"
    report += "|----------|-------------|---------|--------|\n"
    
    for category, scores in sorted(category_metrics.items()):
        avg_score = statistics.mean(scores)
        rating = '✅ Excellent' if avg_score > 7 else '⚠️ Good' if avg_score > 5 else '❌ Needs Improvement'
        report += f"| {category} | {avg_score:.2f}/10 | {len(scores)} | {rating} |\n"
    
    report += f"""

---

## 🐛 Issues Identified

"""
    
    # Identify issues
    issues = []
    
    if statistics.mean(all_intent_latencies) > 100:
        issues.append("⚠️ **High Intent Extraction Latency**: Average >100ms")
    
    if statistics.mean(all_search_latencies) > 5000:
        issues.append("⚠️ **High Search Latency**: Average >5s (likely due to SearXNG API calls)")
    
    if statistics.mean(all_quality_scores) < 7:
        issues.append("⚠️ **Search Quality**: Average quality score <7/10")
    
    # Check for specific failures
    failed_queries = []
    for session in sessions:
        for result in session['results']:
            if not result['intent']['success'] or not result['search']['success']:
                failed_queries.append(result['query']['query'])
    
    if failed_queries:
        issues.append(f"❌ **Failed Queries**: {len(failed_queries)} queries failed")
        for query in failed_queries[:3]:
            issues.append(f"   - \"{query}\"")
    
    if not issues:
        report += "✅ **No critical issues identified!**\n"
    else:
        report += "\n".join(issues)
    
    report += f"""

---

## 💡 Recommendations

1. **Performance Optimization**
   - {'✅ Intent extraction is performing well' if statistics.mean(all_intent_latencies) < 100 else '⚠️ Consider caching intent extraction results'}
   - {'✅ Search latency is acceptable' if statistics.mean(all_search_latencies) < 5000 else '⚠️ Consider implementing search result caching'}

2. **Search Quality**
   - {'✅ Search quality is excellent' if statistics.mean(all_quality_scores) > 7 else '⚠️ Consider improving ranking algorithm or result filtering'}

3. **User Experience**
   - Add loading indicators for search (currently ~{statistics.mean(all_search_latencies)/1000:.1f}s average)
   - Implement search suggestions/autocomplete
   - Add result pagination for better UX

---

## 📈 Overall Rating

**{'⭐⭐⭐⭐⭐ Excellent' if statistics.mean(all_quality_scores) > 8 and statistics.mean(all_intent_latencies) < 100 else '⭐⭐⭐⭐ Good' if statistics.mean(all_quality_scores) > 6 and statistics.mean(all_intent_latencies) < 200 else '⭐⭐⭐ Fair' if statistics.mean(all_quality_scores) > 5 else '⭐⭐ Needs Improvement'}**

- Search Quality: {statistics.mean(all_quality_scores):.2f}/10
- Intent Accuracy: {statistics.mean([s['intent_accuracy'] for s in sessions]):.1f}%
- Avg Intent Latency: {statistics.mean(all_intent_latencies):.2f}ms
- Avg Search Latency: {statistics.mean(all_search_latencies):.2f}ms

---

*Report generated by Intent Engine User Simulation Test*
"""
    
    return report


def main():
    """Run user simulation tests."""
    print_header("Intent Engine - User Simulation & Quality Test")
    
    # Run multiple user sessions
    sessions = []
    
    # Session 1: Developer looking for tutorials
    print_info("Starting User Session 1: Developer")
    session1 = simulate_user_session("developer-001", TEST_QUERIES[:4])
    sessions.append(session1)
    
    # Session 2: Student learning programming
    print_info("Starting User Session 2: Student")
    session2 = simulate_user_session("student-001", TEST_QUERIES[4:])
    sessions.append(session2)
    
    # Generate report
    print_header("Generating Test Report")
    report = generate_report(sessions)
    
    # Save report
    report_file = "USER_SIMULATION_REPORT.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print_success(f"Report saved to: {report_file}")
    print("\n" + report)
    
    # Summary
    avg_quality = statistics.mean([statistics.mean([r['search']['quality']['relevance_score'] for r in s['results'] if r['search']['success']]) for s in sessions])
    avg_intent_latency = statistics.mean([s['avg_intent_latency_ms'] for s in sessions])
    avg_search_latency = statistics.mean([s['avg_search_latency_ms'] for s in sessions])
    
    print_header("Final Summary")
    print(f"Search Quality Rating: {avg_quality:.2f}/10")
    print(f"Avg Intent Latency: {avg_intent_latency:.2f}ms")
    print(f"Avg Search Latency: {avg_search_latency:.2f}ms ({avg_search_latency/1000:.1f}s)")
    
    if avg_quality > 7 and avg_intent_latency < 100:
        print_success("✅ System is performing well!")
    elif avg_quality > 5 and avg_intent_latency < 200:
        print_warning("⚠️ System is acceptable but has room for improvement")
    else:
        print_error("❌ System needs optimization")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
