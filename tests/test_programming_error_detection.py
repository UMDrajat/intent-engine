"""
Unit tests for programming error detection module
"""

import unittest

from core.schema import (ErrorType, IntentGoal, ProgrammingContext,
                         ProgrammingLanguage, UseCase)
from extraction.programming_error_detector import (
    CodeSnippetDetector,
    ErrorMessageParser,
    ProgrammingIntentExtractor,
    get_programming_intent_extractor,
)


class TestProgrammingLanguageDetector(unittest.TestCase):
    """Test programming language detection"""

    def setUp(self):
        self.extractor = get_programming_intent_extractor()

    def test_detect_python(self):
        """Test Python language detection"""
        test_cases = [
            ("def hello():\n    print('Hello')", True),
            ("import os\nfrom pathlib import Path", True),
            ("class MyClass:\n    def __init__(self):", True),
            ("NameError: name 'x' is not defined", True),
            ("TypeError: 'int' object is not subscriptable", True),
        ]

        for text, should_be_python in test_cases:
            lang, confidence = self.extractor.language_detector.detect_language(text)
            if should_be_python:
                self.assertEqual(lang, ProgrammingLanguage.PYTHON)
                self.assertGreater(confidence, 0.5)

    def test_detect_javascript(self):
        """Test JavaScript language detection"""
        test_cases = [
            ("function hello() {\n    console.log('Hello');\n}", True),
            ("const x = require('module');", True),
            ("TypeError: Cannot read property 'map' of undefined", True),
            ("ReferenceError: x is not defined", True),
        ]

        for text, should_be_js in test_cases:
            lang, confidence = self.extractor.language_detector.detect_language(text)
            if should_be_js:
                self.assertEqual(lang, ProgrammingLanguage.JAVASCRIPT)
                self.assertGreater(confidence, 0.5)

    def test_detect_java(self):
        """Test Java language detection"""
        test_cases = [
            ("public class Main {\n    public static void main(String[] args) {", True),
            ("System.out.println('Hello');", True),
            ("java.lang.NullPointerException", True),
            ("Exception in thread \"main\"", True),
        ]

        for text, should_be_java in test_cases:
            lang, confidence = self.extractor.language_detector.detect_language(text)
            if should_be_java:
                self.assertEqual(lang, ProgrammingLanguage.JAVA)
                self.assertGreater(confidence, 0.5)

    def test_unknown_language(self):
        """Test unknown language detection"""
        text = "How to fix my computer?"
        lang, confidence = self.extractor.language_detector.detect_language(text)
        self.assertEqual(lang, ProgrammingLanguage.UNKNOWN)


class TestErrorMessageParser(unittest.TestCase):
    """Test error message parsing"""

    def setUp(self):
        self.parser = ErrorMessageParser()

    def test_parse_python_error(self):
        """Test Python error message parsing"""
        test_cases = [
            (
                "NameError: name 'x' is not defined",
                ErrorType.NULL_REFERENCE,
            ),
            (
                "TypeError: 'int' object is not subscriptable",
                ErrorType.TYPE_ERROR,
            ),
            (
                "ModuleNotFoundError: No module named 'requests'",
                ErrorType.IMPORT_ERROR,
            ),
            (
                "SyntaxError: invalid syntax",
                ErrorType.SYNTAX_ERROR,
            ),
        ]

        for error_msg, expected_type in test_cases:
            result = self.parser.parse_error_message(error_msg)
            self.assertEqual(result["error_type"], expected_type,
                           f"Failed for: {error_msg}")

    def test_parse_javascript_error(self):
        """Test JavaScript error message parsing"""
        test_cases = [
            (
                "TypeError: Cannot read property 'length' of undefined",
                ErrorType.NULL_REFERENCE,
            ),
            (
                "ReferenceError: x is not defined",
                ErrorType.NULL_REFERENCE,
            ),
            (
                "SyntaxError: Unexpected token ','",
                ErrorType.SYNTAX_ERROR,
            ),
        ]

        for error_msg, expected_type in test_cases:
            result = self.parser.parse_error_message(error_msg)
            self.assertEqual(result["error_type"], expected_type,
                           f"Failed for: {error_msg}")

    def test_extract_stack_trace(self):
        """Test stack trace extraction"""
        text = """Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = divide(5, 0)
  File "test.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero"""

        stack_trace = self.parser.extract_stack_trace(text)
        self.assertIsNotNone(stack_trace)
        self.assertIn("Traceback", stack_trace)

    def test_extract_file_location(self):
        """Test file location extraction"""
        test_cases = [
            ('File "test.py", line 10', "test.py", 10),
            ("at Function.module.exports (app.js:42)", "app.js", 42),
        ]

        for text, expected_file, expected_line in test_cases:
            location = self.parser.extract_file_location(text)
            self.assertEqual(location["file_name"], expected_file)
            self.assertEqual(location["line_number"], expected_line)


class TestCodeSnippetDetector(unittest.TestCase):
    """Test code snippet detection"""

    def setUp(self):
        self.detector = CodeSnippetDetector()

    def test_extract_markdown_code_block(self):
        """Test extracting code from markdown blocks"""
        text = """Here's my code:
```python
def hello():
    print('Hello')
```
What's wrong?"""

        snippets = self.detector.extract_code_snippets(text)
        self.assertEqual(len(snippets), 1)
        self.assertEqual(snippets[0]["language"], "python")
        self.assertIn("def hello():", snippets[0]["code"])

    def test_extract_inline_code(self):
        """Test extracting inline code"""
        text = "I'm getting an error with `console.log()` function"

        snippets = self.detector.extract_code_snippets(text)
        self.assertGreater(len(snippets), 0)

    def test_no_code_snippets(self):
        """Test when no code snippets present"""
        text = "How do I fix this error?"

        snippets = self.detector.extract_code_snippets(text)
        self.assertEqual(len(snippets), 0)


class TestProgrammingIntentExtractor(unittest.TestCase):
    """Test the main programming intent extractor"""

    def setUp(self):
        self.extractor = get_programming_intent_extractor()

    def test_is_programming_query(self):
        """Test programming query detection"""
        programming_queries = [
            "NameError: name 'x' is not defined in Python",
            "How to fix TypeError in JavaScript?",
            "```python\ndef test():\n    pass\n```\nWhy doesn't this work?",
            "Getting 'undefined reference to' error in C++",
            "Traceback (most recent call last): File 'app.py', line 10",
        ]

        for query in programming_queries:
            is_prog, confidence = self.extractor.is_programming_query(query)
            self.assertTrue(is_prog, f"Should detect as programming: {query}")

    def test_not_programming_query(self):
        """Test non-programming query detection"""
        non_programming_queries = [
            "How to fix my bike?",
            "What's the best restaurant nearby?",
            "How to cook pasta?",
        ]

        for query in non_programming_queries:
            is_prog, confidence = self.extractor.is_programming_query(query)
            self.assertFalse(is_prog, f"Should not detect as programming: {query}")

    def test_extract_programming_context(self):
        """Test programming context extraction"""
        text = "NameError: name 'x' is not defined in test.py line 10"

        context = self.extractor.extract_programming_context(text)

        self.assertEqual(context.language, ProgrammingLanguage.PYTHON)
        self.assertEqual(context.errorType, ErrorType.NULL_REFERENCE)
        self.assertIsNotNone(context.errorMessage)

    def test_get_intent_goal(self):
        """Test intent goal classification"""
        test_cases = [
            ("NameError: x is not defined", IntentGoal.PROGRAMMING_ERROR),
            ("How to debug this function?", IntentGoal.CODE_DEBUG),
            ("Can you review my code?", IntentGoal.CODE_REVIEW),
            ("How to integrate with REST API?", IntentGoal.API_INTEGRATION),
        ]

        for text, expected_goal in test_cases:
            goal = self.extractor.get_intent_goal(text)
            self.assertEqual(goal, expected_goal, f"Failed for: {text}")

    def test_get_use_cases(self):
        """Test use case extraction"""
        context = ProgrammingContext(
            language=ProgrammingLanguage.PYTHON,
            errorType=ErrorType.TYPE_ERROR,
            codeSnippet="def test(): pass",
        )

        use_cases = self.extractor.get_use_cases(context)

        self.assertIn(UseCase.DEBUGGING, use_cases)
        self.assertIn(UseCase.ERROR_RESOLUTION, use_cases)
        self.assertIn(UseCase.CODE_FIX, use_cases)


class TestIntegrationWithExtractor(unittest.TestCase):
    """Test integration with main intent extractor"""

    def test_full_intent_extraction_with_programming(self):
        """Test full intent extraction for programming queries"""
        from extraction.extractor import IntentExtractionRequest, extract_intent

        test_cases = [
            "NameError: name 'x' is not defined in Python",
            "TypeError: Cannot read property 'map' of undefined in React",
            "```java\npublic class Test {\n}\n```\nCompilation error",
        ]

        for query in test_cases:
            request = IntentExtractionRequest(
                product="search",
                input={"text": query},
                context={"sessionId": "test_session"},
            )

            response = extract_intent(request)
            intent = response.intent

            # Check that programming context was extracted
            self.assertIsNotNone(intent.inferred.programmingContext)
            self.assertNotEqual(
                intent.inferred.programmingContext.language,
                ProgrammingLanguage.UNKNOWN,
            )

            # Check metrics
            self.assertTrue(response.extractionMetrics.get("isProgrammingQuery"))
            self.assertGreater(
                response.extractionMetrics.get("programmingConfidence"),
                0.5,
            )


if __name__ == "__main__":
    unittest.main()
