#!/usr/bin/env python3
"""
Demo script for Programming Error Detection feature

This script demonstrates how the Intent Engine automatically detects
programming-related queries and provides developer-focused assistance.

Usage:
    python demos/demo_programming_error_detection.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extraction.developer_assistance import get_developer_assistance_engine
from app.extraction.extractor import IntentExtractionRequest, extract_intent


def demo_programming_queries():
    """Demonstrate programming error detection with various queries"""

    print("=" * 80)
    print("PROGRAMMING ERROR DETECTION DEMO")
    print("=" * 80)
    print()

    # Test queries
    test_queries = [
        # Python errors
        "NameError: name 'x' is not defined in my Python script",
        # JavaScript errors
        "TypeError: Cannot read property 'map' of undefined in React",
        # Java errors
        "java.lang.NullPointerException at com.example.MyClass.main(MyClass.java:10)",
        # Code snippet with error
        """```python
def divide(a, b):
    return a / b

result = divide(5, 0)
```
Why does this crash?""",
        # Stack trace
        """Traceback (most recent call last):
  File "app.py", line 42, in <module>
    data = load_file("data.csv")
  File "app.py", line 15, in load_file
    with open(filename) as f:
FileNotFoundError: [Errno 2] No such file or directory: 'data.csv' """,
        # C++ compilation error
        "error: undefined reference to 'main' in C++ program",
        # Go error
        "panic: runtime error: index out of range [5] with length 3",
        # Non-programming query (should not be detected)
        "How to fix my bike?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}: {query[:60]}{'...' if len(query) > 60 else ''}")
        print(f"{'=' * 80}")

        # Create extraction request
        request = IntentExtractionRequest(
            product="search",
            input={"text": query},
            context={"sessionId": f"demo-session-{i}"},
        )

        # Extract intent
        response = extract_intent(request)
        intent = response.intent
        metrics = response.extractionMetrics

        # Display results
        print("\n📊 Intent Analysis:")
        print(f"   Goal: {intent.declared.goal.value}")
        print(f"   Use Cases: {[uc.value for uc in intent.inferred.useCases]}")

        # Programming-specific info
        print("\n💻 Programming Detection:")
        print(f"   Is Programming Query: {metrics.get('isProgrammingQuery', False)}")
        print(
            f"   Programming Confidence: {metrics.get('programmingConfidence', 0):.2f}"
        )

        if intent.inferred.programmingContext:
            prog_ctx = intent.inferred.programmingContext
            print(f"   Language: {prog_ctx.language.value}")
            print(f"   Error Type: {prog_ctx.errorType.value}")

            if prog_ctx.errorMessage:
                print(
                    f"   Error Message: {prog_ctx.errorMessage[:80]}{'...' if len(prog_ctx.errorMessage) > 80 else ''}"
                )

            if prog_ctx.fileName:
                print(f"   File: {prog_ctx.fileName}")

            if prog_ctx.lineNumber:
                print(f"   Line: {prog_ctx.lineNumber}")

            if prog_ctx.hasStackTrace:
                print("   Has Stack Trace: Yes")

            if prog_ctx.codeSnippet:
                snippet_preview = prog_ctx.codeSnippet[:50].replace("\n", "\\n")
                print(f"   Has Code Snippet: Yes ({snippet_preview}...)")

        # Get debugging suggestions
        if intent.inferred.programmingContext and metrics.get("isProgrammingQuery"):
            assistance = get_developer_assistance_engine()
            suggestions = assistance.generate_assistance_response(intent)

            print("\n🔧 Debugging Suggestions:")
            if suggestions.quick_fixes:
                print("   Quick Fixes:")
                for fix in suggestions.quick_fixes[:3]:
                    print(f"      • {fix}")

            if suggestions.suggestions:
                print("   Top Suggestion:")
                top = suggestions.suggestions[0]
                print(f"      {top.title}: {top.description}")

            if suggestions.recommended_resources:
                print("   Recommended Resources:")
                for resource in suggestions.recommended_resources[:2]:
                    print(f"      • {resource}")

            if suggestions.research_plan:
                plan = suggestions.research_plan
                print("\n📋 Dynamic Research Plan:")
                print("   Investigation Steps:")
                for step in plan.investigation_steps:
                    print(f"      □ {step}")

                print("   Optimized Search Queries:")
                for site, sq in plan.optimized_search_queries.items():
                    print(f"      🔍 {site}: {sq}")

                if plan.key_concepts:
                    print(f"   Key Concepts: {', '.join(plan.key_concepts)}")

            print()


def demo_api_usage():
    """Demonstrate programmatic API usage"""

    print(f"\n{'=' * 80}")
    print("PROGRAMMATIC API USAGE EXAMPLE")
    print(f"{'=' * 80}")
    print()

    print("""
```python
from app.extraction.extractor import IntentExtractionRequest, extract_intent
from app.extraction.developer_assistance import get_developer_assistance_engine

# Create a request with a programming query
request = IntentExtractionRequest(
    product='search',
    input={'text': "TypeError: 'int' object is not subscriptable"},
    context={'sessionId': 'dev-session-123'}
)

# Extract intent
response = extract_intent(request)
intent = response.intent

# Check if it's a programming query
if response.extractionMetrics.get('isProgrammingQuery'):
    prog_context = intent.inferred.programmingContext

    print(f"Language: {prog_context.language.value}")
    print(f"Error Type: {prog_context.errorType.value}")
    print(f"Error Message: {prog_context.errorMessage}")

    # Get debugging suggestions
    assistance = get_developer_assistance_engine()
    suggestions = assistance.generate_assistance_response(intent)

    print("\\nQuick Fixes:")
    for fix in suggestions.quick_fixes:
        print(f"  - {fix}")
```
    """)


def demo_search_enhancement():
    """Demonstrate search query enhancement"""

    print(f"\n{'=' * 80}")
    print("SEARCH QUERY ENHANCEMENT")
    print(f"{'=' * 80}")
    print()

    from app.extraction.programming_error_detector import (
        get_programming_intent_extractor,
    )

    extractor = get_programming_intent_extractor()

    # Extract context from a query
    query = "fix TypeError in Python when accessing list"
    context = extractor.extract_programming_context(query)

    # Get search enhancements
    assistance = get_developer_assistance_engine()
    enhancements = assistance.format_search_query_for_programming(query, context)

    print(f"Original Query: {enhancements['original_query']}")
    print(f"Enhanced Query: {enhancements['enhanced_query']}")
    print(f"Suggested Tags: {enhancements['suggested_tags']}")
    print("\nSite Boosts:")
    for site, boost in enhancements["site_boosts"].items():
        print(f"   {site}: {boost}x")


if __name__ == "__main__":
    # Run demos
    demo_programming_queries()
    demo_api_usage()
    demo_search_enhancement()

    print(f"\n{'=' * 80}")
    print("DEMO COMPLETE!")
    print(f"{'=' * 80}")
    print()
    print("For more information, see:")
    print("  - Documentation: docs/reference/PROGRAMMING_ERROR_DETECTION.md")
    print("  - Tests: tests/test_programming_error_detection.py")
    print()
