# Programming Error Detection Guide

## Overview

The Intent Engine now includes **automatic programming error detection** to help developers debug code issues more effectively. When a user submits a programming-related query, the system:

1. **Detects** that it's a programming query
2. **Identifies** the programming language
3. **Parses** error messages and stack traces
4. **Extracts** code snippets
5. **Provides** developer-focused search enhancements
6. **Suggests** debugging steps

---

## Features

### 1. Programming Language Detection

Automatically detects 15+ programming languages:

- **Python** - Detects `def`, `import`, Python error types
- **JavaScript** - Detects `function`, `const`, `console.log`
- **TypeScript** - Detects `interface`, `type`, generics
- **Java** - Detects `public class`, `System.out`
- **C/C++** - Detects `#include`, `std::`, `cout`
- **C#** - Detects `using System`, `namespace`
- **Go** - Detects `func`, `package`, `goroutine`
- **Rust** - Detects `fn`, `let`, `match`
- **PHP** - Detects `<?php`, `$variables`
- **SQL** - Detects `SELECT`, `FROM`, `JOIN`
- **Shell/Bash** - Detects functions, pipes, redirects
- **And more...**

### 2. Error Message Parsing

Recognizes and categorizes error types:

| Error Type | Examples |
|------------|----------|
| `SYNTAX_ERROR` | `SyntaxError: invalid syntax` |
| `TYPE_ERROR` | `TypeError: 'int' object is not subscriptable` |
| `NULL_REFERENCE` | `NameError: name 'x' is not defined` |
| `IMPORT_ERROR` | `ModuleNotFoundError: No module named 'requests'` |
| `RUNTIME_ERROR` | `ZeroDivisionError: division by zero` |
| `DATABASE_ERROR` | `SQL Error: table doesn't exist` |
| `API_ERROR` | `HTTP Error 404: Not Found` |
| `AUTHENTICATION_ERROR` | `AuthenticationError: Invalid token` |
| `MEMORY_ERROR` | `MemoryError: Unable to allocate` |
| `COMPILATION_ERROR` | `error: undefined reference to` |

### 3. Stack Trace Extraction

Automatically extracts and analyzes stack traces:

**Example Input:**
```
Traceback (most recent call last):
  File "app.py", line 10, in <module>
    result = divide(5, 0)
  File "app.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero
```

**Extracted Information:**
- File: `app.py`
- Line: `10`
- Error: `ZeroDivisionError`
- Full stack trace preserved

### 4. Code Snippet Detection

Extracts code from various formats:

- **Markdown code blocks**: \`\`\`python ... \`\`\`
- **Inline code**: \`code\`
- **HTML code tags**: `<code>...</code>`
- **BBCode**: `[code]...[/code]`

### 5. Developer-Focused Search Enhancements

For programming queries, the system:

- **Boosts** developer-focused sites (Stack Overflow, GitHub, official docs)
- **Adds** language tags to queries
- **Suggests** relevant tags for filtering
- **Prioritizes** recent solutions for the specific language version

### 6. Debugging Suggestions

Provides contextual debugging tips:

**For TypeError:**
- "Verify variable types before operations"
- "Check function return types"
- "Add type checking with type hints"

**For Import Error:**
- "Verify the package is installed"
- "Check the import path spelling"
- "Ensure virtual environment is activated"

---

## Usage Examples

### Example 1: Python Error

**User Query:**
```
NameError: name 'x' is not defined in my Python script
```

**Extracted Intent:**
```json
{
  "goal": "programming_error",
  "useCases": ["debugging", "error_resolution", "code_fix"],
  "programmingContext": {
    "language": "python",
    "errorType": "null_reference",
    "errorMessage": "NameError: name 'x' is not defined",
    "confidence": 0.92
  }
}
```

**Search Enhancements:**
- Boost: `stackoverflow.com` (1.5x)
- Boost: `docs.python.org` (2.0x)
- Tags: `["python", "null_reference"]`

---

### Example 2: JavaScript TypeError

**User Query:**
```
TypeError: Cannot read property 'map' of undefined in React component
```

**Extracted Intent:**
```json
{
  "goal": "programming_error",
  "useCases": ["debugging", "error_resolution"],
  "programmingContext": {
    "language": "javascript",
    "errorType": "null_reference",
    "errorMessage": "Cannot read property 'map' of undefined",
    "framework": "React"
  }
}
```

**Debugging Suggestions:**
1. "Add null checks before calling .map()"
2. "Use optional chaining: data?.map()"
3. "Check if props.data is initialized"

---

### Example 3: Code Snippet with Error

**User Query:**
````
```python
def divide(a, b):
    return a / b

result = divide(5, 0)
```
Why does this crash?
````

**Extracted Intent:**
```json
{
  "goal": "programming_error",
  "useCases": ["debugging", "code_fix"],
  "programmingContext": {
    "language": "python",
    "errorType": "runtime_error",
    "codeSnippet": "def divide(a, b):\n    return a / b\n\nresult = divide(5, 0)",
    "isRuntimeError": true
  }
}
```

---

### Example 4: Stack Trace

**User Query:**
```
Getting this error:
Traceback (most recent call last):
  File "app.py", line 42, in <module>
    data = load_file("data.csv")
  File "app.py", line 15, in load_file
    with open(filename) as f:
FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'
```

**Extracted Information:**
- Language: Python
- Error Type: File/Permission Error
- File: `app.py`
- Line: `42`
- Has Stack Trace: `true`

---

## API Response Format

When a programming query is detected, the API response includes:

```json
{
  "intent": {
    "declared": {
      "goal": "programming_error",
      "query": "NameError: x is not defined"
    },
    "inferred": {
      "useCases": ["debugging", "error_resolution"],
      "programmingContext": {
        "language": "python",
        "errorType": "null_reference",
        "errorMessage": "NameError: name 'x' is not defined",
        "confidence": 0.92
      }
    }
  },
  "extractionMetrics": {
    "isProgrammingQuery": true,
    "programmingConfidence": 0.92
  }
}
```

---

## For Developers: Using the Feature

### Programmatic Usage

```python
from extraction.extractor import IntentExtractionRequest, extract_intent

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
    from extraction.developer_assistance import get_developer_assistance_engine
    assistance = get_developer_assistance_engine()
    suggestions = assistance.generate_assistance_response(intent)
    
    print("Quick Fixes:")
    for fix in suggestions.quick_fixes:
        print(f"  - {fix}")
```

### Getting Debugging Suggestions

```python
from extraction.developer_assistance import (
    get_developer_assistance_engine,
    DeveloperAssistanceResponse
)

# Get the assistance engine
engine = get_developer_assistance_engine()

# Generate suggestions for the intent
response: DeveloperAssistanceResponse = engine.generate_assistance_response(intent)

# Access suggestions
for suggestion in response.suggestions:
    print(f"{suggestion.title}: {suggestion.description}")
    if suggestion.code_example:
        print(f"  Example: {suggestion.code_example}")

# Get recommended resources
for resource in response.recommended_resources:
    print(f"Resource: {resource}")
```

### Search Query Enhancement

```python
# Enhance search query for programming context
enhancements = engine.format_search_query_for_programming(
    query="fix type error",
    context=intent.inferred.programmingContext
)

print(f"Enhanced Query: {enhancements['enhanced_query']}")
print(f"Site Boosts: {enhancements['site_boosts']}")
print(f"Suggested Tags: {enhancements['suggested_tags']}")
```

---

## Configuration

### Language Detection Threshold

Adjust the confidence threshold for language detection:

```python
# In programming_error_detector.py
# Default: 0.3 (30% confidence)
if confidence < 0.3:
    return ProgrammingLanguage.UNKNOWN, confidence
```

### Search Boost Factors

Customize site boost factors in `developer_assistance.py`:

```python
self.programming_search_boost = {
    "stackoverflow.com": 1.5,
    "github.com": 1.4,
    "docs.python.org": 2.0,  # Increase for Python queries
    "developer.mozilla.org": 2.0,  # Increase for JS queries
}
```

---

## Testing

Run the test suite:

```bash
# Run programming error detection tests
pytest tests/test_programming_error_detection.py -v

# Run with coverage
pytest --cov=extraction.programming_error_detector tests/test_programming_error_detection.py
```

### Test Examples

```python
# Test language detection
from extraction.programming_error_detector import get_programming_intent_extractor

extractor = get_programming_intent_extractor()

# Python detection
lang, confidence = extractor.language_detector.detect_language(
    "def hello():\n    print('Hi')"
)
assert lang == ProgrammingLanguage.PYTHON

# Error parsing
from extraction.programming_error_detector import ErrorMessageParser

parser = ErrorMessageParser()
result = parser.parse_error_message("TypeError: 'int' object is not subscriptable")
assert result["error_type"] == ErrorType.TYPE_ERROR
```

---

## Troubleshooting

### Language Not Detected

**Problem:** Query contains code but language shows as `UNKNOWN`

**Solutions:**
1. Check if code snippet is properly formatted
2. Ensure code has language-specific keywords
3. Increase detection sensitivity in config

### Wrong Error Type

**Problem:** Error categorized incorrectly

**Solutions:**
1. Check error message format
2. Add new error patterns to `ErrorMessageParser`
3. Verify regex patterns match the error format

### Search Results Not Enhanced

**Problem:** Programming queries don't get boosted results

**Solutions:**
1. Verify `isProgrammingQuery` metric is `true`
2. Check search integration uses boost factors
3. Ensure ranking module processes programming context

---

## Extending the System

### Adding a New Language

1. Add to `ProgrammingLanguage` enum in `core/schema.py`
2. Add patterns in `ProgrammingLanguageDetector.__init__()`
3. Add resources in `DeveloperAssistanceEngine.language_resources`

```python
# Example: Adding Kotlin
ProgrammingLanguage.KOTLIN = "kotlin"

# In language_detector
ProgrammingLanguage.KOTLIN: {
    "keywords": [
        r"\bfun\s+\w+\s*\(",
        r"\bval\s+\w+\s*=",
        r"\bvar\s+\w+\s*=",
        r"\bclass\s+\w+",
    ],
    "error_prefixes": ["Kotlin: "],
    "file_extensions": [".kt", ".kts"],
}
```

### Adding a New Error Type

1. Add to `ErrorType` enum in `core/schema.py`
2. Add patterns in `ErrorMessageParser.__init__()`
3. Add solutions in `DeveloperAssistanceEngine.error_solutions`

---

## Performance Considerations

- **Language Detection:** ~5ms per query (compiled regex)
- **Error Parsing:** ~2ms per query
- **Code Extraction:** ~3ms per query
- **Total Overhead:** <15ms for full programming analysis

### Caching

The extractor uses singleton pattern for optimal performance:

```python
# Reuse the same instance
extractor = get_programming_intent_extractor()
```

---

## Future Enhancements

Planned improvements:

- [ ] **Semantic Error Analysis** - Use ML to understand error context
- [ ] **Solution Database** - Pre-computed solutions for common errors
- [ ] **Code Fix Suggestions** - Auto-generate fix patches
- [ ] **Version-Specific Help** - Detect language version and tailor results
- [ ] **Framework Detection** - Identify Django, React, Spring, etc.
- [ ] **Interactive Debugging** - Step-by-step debugging guidance

---

## Contributing

To contribute improvements:

1. Add new error patterns to `ErrorMessageParser`
2. Enhance language detection patterns
3. Add debugging suggestions for new error types
4. Submit tests with your changes

---

## Support

For issues or questions:

- **GitHub Issues:** https://github.com/itxLikhith/intent-engine/issues
- **Documentation:** See `docs/` directory
- **Examples:** Check `tests/test_programming_error_detection.py`

---

**Last Updated:** March 16, 2026  
**Version:** 2.1.0 (Programming Error Detection)
