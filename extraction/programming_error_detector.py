"""
Intent Engine - Programming Error Detection Module

This module detects programming-related queries, extracts error information,
and provides developer-focused intent extraction.

Features:
- Programming language detection
- Error message parsing
- Stack trace extraction
- Code snippet detection
- Framework/library identification
"""

import logging
import re
from typing import Any

from core.schema import (
    ErrorType,
    IntentGoal,
    ProgrammingContext,
    ProgrammingLanguage,
    UseCase,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgrammingLanguageDetector:
    """Detects programming language from query text and code snippets"""

    def __init__(self):
        # Language keywords and patterns
        self.language_patterns = {
            ProgrammingLanguage.PYTHON: {
                "keywords": [
                    r"\bdef\s+\w+\s*\(",
                    r"\bimport\s+\w+",
                    r"\bfrom\s+\w+\s+import",
                    r"\bprint\s*\(",
                    r"\bclass\s+\w+",
                    r"\bif\s+__name__\s*==\s*['\"]__main__['\"]",
                    r"\bself\.",
                    r"\bNone\b",
                    r"\bTrue\b|\bFalse\b",
                    r"__\w+__",  # Dunder methods
                ],
                "error_prefixes": [
                    "NameError:",
                    "TypeError:",
                    "ValueError:",
                    "IndexError:",
                    "KeyError:",
                    "AttributeError:",
                    "ImportError:",
                    "ModuleNotFoundError:",
                    "SyntaxError:",
                    "IndentationError:",
                    "TabError:",
                    "FileNotFoundError:",
                    "PermissionError:",
                    "ZeroDivisionError:",
                ],
                "file_extensions": [".py", ".pyw", ".pyi"],
            },
            ProgrammingLanguage.JAVASCRIPT: {
                "keywords": [
                    r"\bfunction\s+\w*\s*\(",
                    r"\bconst\s+\w+\s*=",
                    r"\blet\s+\w+\s*=",
                    r"\bvar\s+\w+\s*=",
                    r"\b=>\s*{",  # Arrow functions
                    r"\bconsole\.\w+\(",
                    r"\bdocument\.\w+",
                    r"\bwindow\.\w+",
                    r"\brequire\s*\(",
                    r"\bmodule\.exports",
                    r"\basync\s+\w+\s*\(",
                    r"\bawait\s+",
                ],
                "error_prefixes": [
                    "TypeError:",
                    "ReferenceError:",
                    "SyntaxError:",
                    "RangeError:",
                    "URIError:",
                    "EvalError:",
                ],
                "file_extensions": [".js", ".jsx", ".mjs"],
            },
            ProgrammingLanguage.TYPESCRIPT: {
                "keywords": [
                    r"\binterface\s+\w+",
                    r"\btype\s+\w+\s*=",
                    r":\s*(string|number|boolean|any|void|null|undefined)",
                    r"<\w+>",  # Generics
                    r"\benum\s+\w+",
                    r"\bimplements\s+",
                ],
                "error_prefixes": ["TS"],  # TypeScript error codes start with TS
                "file_extensions": [".ts", ".tsx"],
            },
            ProgrammingLanguage.JAVA: {
                "keywords": [
                    r"\bpublic\s+class\s+\w+",
                    r"\bprivate\s+",
                    r"\bprotected\s+",
                    r"\bstatic\s+",
                    r"\bvoid\s+\w+\s*\(",
                    r"\bSystem\.out\.print",
                    r"\bnew\s+\w+\s*\(",
                    r"\bthrows\s+\w+",
                    r"\b@Override",
                    r"\bimport\s+java\.",
                ],
                "error_prefixes": [
                    "java.lang.",
                    "Exception in thread",
                    "Caused by:",
                ],
                "file_extensions": [".java"],
            },
            ProgrammingLanguage.CPP: {
                "keywords": [
                    r"#include\s*[<\"]",
                    r"\bstd::",
                    r"\bcout\s*<<",
                    r"\bcin\s*>>",
                    r"\bint\s+main\s*\(",
                    r"\bclass\s+\w+",
                    r"\btemplate\s*<",
                    r"\bnamespace\s+",
                ],
                "error_prefixes": [
                    "error:",
                    "fatal error:",
                    "warning:",
                    "undefined reference to",
                    "segmentation fault",
                ],
                "file_extensions": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            },
            ProgrammingLanguage.C_SHARP: {
                "keywords": [
                    r"\busing\s+System;",
                    r"\bnamespace\s+",
                    r"\bclass\s+\w+",
                    r"\bpublic\s+(static|void|int|string)",
                    r"\bConsole\.Write",
                    r"\bvar\s+\w+\s*=",
                    r"\bLINQ",
                    r"\basync\s+Task",
                ],
                "error_prefixes": ["CS"],  # C# error codes start with CS
                "file_extensions": [".cs"],
            },
            ProgrammingLanguage.GO: {
                "keywords": [
                    r"\bfunc\s+\w*\s*\(",
                    r"\bpackage\s+\w+",
                    r"\bimport\s+\(",
                    r"\bvar\s+\w+\s+\w+",
                    r"\b:=\s*",  # Short variable declaration
                    r"\bfmt\.\w+\(",
                    r"\bgo\s+\w+\(",  # Goroutines
                    r"\bchan\s+",  # Channels
                    r"\bdefer\s+",
                    r"\binterface\s+\{",
                ],
                "error_prefixes": [
                    "# command-line-arguments",
                    "undefined:",
                    "cannot use",
                ],
                "file_extensions": [".go"],
            },
            ProgrammingLanguage.RUST: {
                "keywords": [
                    r"\bfn\s+\w+\s*\(",
                    r"\blet\s+(mut\s+)?\w+",
                    r"\bimpl\s+\w+",
                    r"\bstruct\s+\w+",
                    r"\btrait\s+\w+",
                    r"\bmatch\s+\w+\s*\{",
                    r"\bOption<\w+>",
                    r"\bResult<\w+>",
                    r"\b->\s*\w+",  # Return type
                ],
                "error_prefixes": ["error[E"],  # Rust error codes: error[E0301]
                "file_extensions": [".rs"],
            },
            ProgrammingLanguage.PHP: {
                "keywords": [
                    r"<\?php",
                    r"\$\w+",  # Variables start with $
                    r"\bfunction\s+\w+\s*\(",
                    r"\bclass\s+\w+",
                    r"\bpublic\s+function",
                    r"\becho\s+",
                    r"\barray\s*\(",
                    r"\b=>\s*",  # Array syntax
                ],
                "error_prefixes": [
                    "PHP Fatal error:",
                    "PHP Warning:",
                    "PHP Notice:",
                    "Parse error:",
                ],
                "file_extensions": [".php"],
            },
            ProgrammingLanguage.SQL: {
                "keywords": [
                    r"\bSELECT\s+\w+",
                    r"\bFROM\s+\w+",
                    r"\bWHERE\s+",
                    r"\bJOIN\s+",
                    r"\bINSERT\s+INTO",
                    r"\bUPDATE\s+\w+\s+SET",
                    r"\bDELETE\s+FROM",
                    r"\bCREATE\s+TABLE",
                    r"\bALTER\s+TABLE",
                ],
                "error_prefixes": [
                    "SQL Error:",
                    "ORA-",  # Oracle
                    "MySQL Error:",
                    "PostgreSQL Error:",
                ],
            },
            ProgrammingLanguage.RUBY: {
                "keywords": [
                    r"\bdef\s+\w+",
                    r"\bclass\s+\w+",
                    r"\bmodule\s+\w+",
                    r"\brequire\s+['\"]",
                    r"\byield\b",
                    r"\battr_accessor\b",
                    r"\|\w+\|", # Blocks
                ],
                "error_prefixes": [
                    "NoMethodError:",
                    "ArgumentError:",
                    "RuntimeError:",
                    "NameError:",
                    "LoadError:",
                ],
                "file_extensions": [".rb", ".rake", ".gemfile"],
            },
            ProgrammingLanguage.SWIFT: {
                "keywords": [
                    r"\bfunc\s+\w+\s*\(",
                    r"\blet\s+\w+",
                    r"\bvar\s+\w+",
                    r"\bguard\s+let\b",
                    r"\bif\s+let\b",
                    r"\bstruct\s+\w+",
                    r"\benum\s+\w+",
                    r"\b@objc\b",
                    r"\bprint\s*\(",
                ],
                "error_prefixes": [
                    "error:",
                    "fatal error:",
                    "Thread 1: signal SIGABRT",
                ],
                "file_extensions": [".swift"],
            },
            ProgrammingLanguage.KOTLIN: {
                "keywords": [
                    r"\bfun\s+\w+\s*\(",
                    r"\bval\s+\w+",
                    r"\bvar\s+\w+",
                    r"\bclass\s+\w+",
                    r"\bdata\s+class\b",
                    r"\bobject\s+\w+",
                    r"\bsuspend\s+fun\b",
                    r"\?.", # Null safety
                ],
                "error_prefixes": [
                    "Exception in thread",
                    "Caused by:",
                    "kotlin.KotlinNullPointerException",
                ],
                "file_extensions": [".kt", ".kts"],
            },
            ProgrammingLanguage.SHELL: {
                "keywords": [
                    r"^\s*\w+\s*\(\s*\)\s*\{",  # Function definition
                    r"\$\{?\w+\}?",  # Variables
                    r"\bif\s+\[",
                    r"\bfi\b",
                    r"\bdone\b",
                    r"\besac\b",
                    r"\|",  # Pipes
                    r">>",  # Redirect
                ],
                "error_prefixes": [
                    "bash:",
                    "sh:",
                    "zsh:",
                    "command not found",
                    "permission denied",
                ],
            },
        }

        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for lang, patterns in self.language_patterns.items():
            self.compiled_patterns[lang] = {
                "keywords": [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns["keywords"]],
                "error_prefixes": patterns.get("error_prefixes", []),
                "file_extensions": patterns.get("file_extensions", []),
            }

    def detect_language(self, text: str) -> tuple[ProgrammingLanguage, float]:
        """
        Detect programming language from text.
        Returns (language, confidence_score)
        """
        if not text:
            return ProgrammingLanguage.UNKNOWN, 0.0

        scores = {}
        text_lower = text.lower()

        for lang, patterns in self.compiled_patterns.items():
            score = 0

            # Count keyword matches
            for keyword_pattern in patterns["keywords"]:
                matches = keyword_pattern.findall(text)
                score += len(matches)

            # Check for error prefixes
            for error_prefix in patterns["error_prefixes"]:
                if error_prefix.lower() in text_lower:
                    score += 3  # Error prefixes are strong indicators

            # Check file name if present
            for ext in patterns["file_extensions"]:
                if ext in text_lower:
                    score += 2

            scores[lang] = score

        if not scores or max(scores.values()) == 0:
            return ProgrammingLanguage.UNKNOWN, 0.0

        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]

        # Normalize confidence (0-1)
        total_score = sum(scores.values())
        confidence = best_score / max(total_score, 1)

        # Minimum threshold
        if confidence < 0.3:
            return ProgrammingLanguage.UNKNOWN, confidence

        return best_lang, min(confidence, 1.0)


class ErrorMessageParser:
    """Parses error messages to extract structured information"""

    def __init__(self):
        # Common error patterns
        self.error_patterns = {
            ErrorType.SYNTAX_ERROR: [
                r"SyntaxError:\s*(.+)",
                r"syntax error, unexpected\s+'(.+)'",
                r"invalid syntax",
                r"unexpected EOF while parsing",
                r"missing\s+\w+\s+at\s+",
            ],
            ErrorType.TYPE_ERROR: [
                r"TypeError:\s*(.+)",
                r"type\s+mismatch",
                r"cannot convert\s+.+\s+to\s+",
                r"expected\s+\w+\s+but found",
                r"is not a\s+(function|number|string|object)",
            ],
            ErrorType.NULL_REFERENCE: [
                r"NullPointerException",
                r"NoneType\s+has no attribute",
                r"Cannot read propert",
                r"is null",
                r"undefined\s+is not a function",
                r"Cannot read properties of null",
            ],
            ErrorType.IMPORT_ERROR: [
                r"ImportError:\s*(.+)",
                r"ModuleNotFoundError:\s*(.+)",
                r"cannot find module",
                r"failed to resolve import",
                r"package\s+.+\s+does not exist",
                r"no module named",
            ],
            ErrorType.RUNTIME_ERROR: [
                r"RuntimeError:\s*(.+)",
                r"Exception in thread",
                r"uncaught exception",
                r"fatal error",
                r"panic:",  # Go panic
            ],
            ErrorType.DATABASE_ERROR: [
                r"SQL Error:\s*(.+)",
                r"database error",
                r"connection refused",
                r"query failed",
                r"table\s+.+\s+doesn't exist",
                r"column\s+.+\s+doesn't exist",
            ],
            ErrorType.API_ERROR: [
                r"HTTP Error\s+(\d+)",
                r"API request failed",
                r"status code\s+(\d+)",
                r"rate limit exceeded",
                r"unauthorized",
                r"forbidden",
            ],
            ErrorType.AUTHENTICATION_ERROR: [
                r"AuthenticationError",
                r"unauthorized",
                r"invalid credentials",
                r"access denied",
                r"permission denied",
                r"token expired",
            ],
            ErrorType.MEMORY_ERROR: [
                r"MemoryError",
                r"out of memory",
                r"heap space",
                r"stack overflow",
                r"memory allocation failed",
            ],
            ErrorType.COMPILATION_ERROR: [
                r"compilation failed",
                r"error:.*",
                r"fatal error:",
                r"undefined reference to",
                r"ld returned 1 exit status",
            ],
        }

        # Compile patterns
        self.compiled_patterns = {}
        for error_type, patterns in self.error_patterns.items():
            self.compiled_patterns[error_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        # Error code patterns
        self.error_code_patterns = [
            (r"error\s*\[([A-Z]?\d+)\]", "generic"),  # [E0301], [CS1234]
            (r"TS(\d{4})", "typescript"),  # TS2304
            (r"E(\d{4})", "rust"),  # E0301
            (r"CS(\d{4})", "csharp"),  # CS0123
            (r"ORA-(\d{5})", "oracle"),  # ORA-00942
            (r"SQLSTATE\s*\[\w+\]\s*\[(\d+)\]", "sql"),  # SQLSTATE[42S02]
        ]

    def parse_error_message(self, text: str) -> dict[str, Any]:
        """
        Parse error message to extract structured information.
        Returns dict with error_type, error_code, error_message, etc.
        """
        result = {
            "error_type": ErrorType.UNKNOWN,
            "error_code": None,
            "error_message": None,
            "confidence": 0.0,
        }

        if not text:
            return result

        # Detect error type
        max_score = 0
        for error_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    result["error_type"] = error_type
                    result["error_message"] = match.group(0)
                    max_score += 1

        # Extract error code
        for pattern, _ in self.error_code_patterns:
            match = re.search(pattern, text)
            if match:
                result["error_code"] = match.group(1)
                break

        # If no specific error message extracted, use first line
        if not result["error_message"]:
            lines = text.strip().split("\n")
            if lines:
                result["error_message"] = lines[0][:200]  # First 200 chars

        # Calculate confidence
        if result["error_type"] != ErrorType.UNKNOWN:
            result["confidence"] = min(max_score / 3, 1.0)  # Max confidence at 3+ matches

        return result

    def extract_stack_trace(self, text: str) -> str | None:
        """
        Extract stack trace from text.
        Returns the stack trace portion if found.
        """
        # Common stack trace patterns
        stack_patterns = [
            r"Traceback \(most recent call last\):.*?(?=\n\n|\Z)",
            r"at\s+\S+\s+\([^)]+\).*?(?=\n\n|\Z)",
            r"Stack trace:.*?(?=\n\n|\Z)",
            r"Call Stack:.*?(?=\n\n|\Z)",
            r"goroutine\s+\d+\s+\[.*?\]:.*?(?=\n\n|\Z)",  # Go
            r"thread\s+'.*?'.*?Stack Trace.*?(?=\n\n|\Z)",  # Java
        ]

        for pattern in stack_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0).strip()

        return None

    def extract_file_location(self, text: str) -> dict[str, Any]:
        """
        Extract file name and line number from error message.
        """
        result = {"file_name": None, "line_number": None}

        # File:line patterns
        patterns = [
            r'File\s+"([^"]+)",\s+line\s+(\d+)',  # Python: File "test.py", line 10
            r"at\s+[^(]+\(([^:]+):(\d+)\)",  # Java/JS: at func (file.js:10)
            r"([^:\s]+):(\d+):\s*(\d+):",  # GCC: file.cpp:10:5:
            r"in\s+([^\s]+)\s+on\s+line\s+(\d+)",  # Generic: in file.py on line 10
            r"([^\s]+\.(?:py|js|ts|java|cpp|go|rs|php))\((\d+)\)",  # file.ext(line)
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["file_name"] = match.group(1)
                result["line_number"] = int(match.group(2))
                break

        return result


class CodeSnippetDetector:
    """Detects and extracts code snippets from queries"""

    def __init__(self):
        # Code block patterns
        self.code_patterns = [
            r"```(\w+)?\n(.*?)```",  # Markdown code blocks
            r"`([^`]+)`",  # Inline code
            r"<code>(.*?)</code>",  # HTML code tags
            r"\[code\](.*?)\[/code\]",  # BBCode
        ]

    def extract_code_snippets(self, text: str) -> list[dict[str, str]]:
        """
        Extract code snippets from text.
        Returns list of {language, code} dicts.
        """
        snippets = []

        # Multi-line code blocks
        for match in re.finditer(self.code_patterns[0], text, re.DOTALL):
            lang = match.group(1) or "unknown"
            code = match.group(2).strip()
            snippets.append({"language": lang, "code": code, "type": "block"})

        # Inline code
        for match in re.finditer(self.code_patterns[1], text):
            code = match.group(1).strip()
            # Only add if it looks like code (has programming characters)
            if re.search(r"[\(\)\{\}\[\];=]", code):
                snippets.append({"language": "unknown", "code": code, "type": "inline"})

        return snippets


class ProgrammingIntentExtractor:
    """
    Main class for extracting programming-related intent from queries.
    Combines language detection, error parsing, and code extraction.
    """

    def __init__(self):
        self.language_detector = ProgrammingLanguageDetector()
        self.error_parser = ErrorMessageParser()
        self.code_detector = CodeSnippetDetector()

        # Framework-specific patterns
        self.framework_patterns = {
            "React": [r"\bReact\b", r"\buseState\b", r"\beffect\b", r"\bJSX\b", r"render\s*\(", r"\bComponent\b"],
            "Django": [r"\bDjango\b", r"\bmodels\.Model\b", r"\burls\.py\b", r"\bviews\.py\b", r"\bmanage\.py\b", r"\{\{\s*[\w.]+\s*\}\}"],
            "FastAPI": [r"\bFastAPI\b", r"@app\.\w+\s*\(", r"Pydantic", r"uvicorn", r"async\s+def\b"],
            "Flask": [r"\bFlask\b", r"@app\.route\b", r"render_template", r"flask\s+run"],
            "Spring Boot": [r"@SpringBootApplication", r"@RestController", r"@Autowired", r"Spring\s*Boot"],
            "Express": [r"\bExpress\b", r"app\.get\s*\(", r"app\.use\s*\(", r"req,\s*res", r"middleware"],
            "Rails": [r"\bRails\b", r"ActiveRecord", r"ActionController", r"ActiveStorage", r"rails\s+server"],
            "Angular": [r"\b@Component\b", r"\[\w+\]\s*=", r"\(\w+\)\s*=", r"ngIf", r"ngFor", r"\bAngular\b"],
            "Flutter": [r"\bFlutter\b", r"\bWidget\b", r"\bStatelessWidget\b", r"\bStatefulWidget\b", r"setState\s*\("],
            "Vue": [r"\bVue\b", r"v-if", r"v-for", r"v-bind", r"v-model", r"computed\s*:"],
        }
        self.compiled_frameworks = {
            name: [re.compile(p, re.IGNORECASE) for p in patterns]
            for name, patterns in self.framework_patterns.items()
        }

        # Programming-specific keywords
        self.programming_keywords = [
            r"\b(error|exception|bug|issue|problem|fix|debug)\b",
            r"\b(code|coding|program|programming|script)\b",
            r"\b(function|method|class|interface|module|package)\b",
            r"\b(variable|array|list|dict|object|instance)\b",
            r"\b(compile|build|run|execute|deploy)\b",
            r"\b(import|require|include|export)\b",
            r"\b(return|yield|async|await|promise)\b",
            r"\b(loop|iteration|recursion|callback)\b",
        ]

        # Compile patterns
        self.compiled_keywords = [
            re.compile(p, re.IGNORECASE) for p in self.programming_keywords
        ]

    def is_programming_query(self, text: str) -> tuple[bool, float]:
        """
        Determine if a query is programming-related.
        Returns (is_programming, confidence_score)
        """
        if not text:
            return False, 0.0

        # Check for code snippets
        code_snippets = self.code_detector.extract_code_snippets(text)
        if code_snippets:
            return True, 0.9

        # Check for error messages
        error_analysis = self.error_parser.parse_error_message(text)
        if error_analysis["error_type"] != ErrorType.UNKNOWN:
            return True, error_analysis["confidence"]

        # Check for programming keywords
        keyword_matches = sum(
            1 for pattern in self.compiled_keywords if pattern.search(text)
        )

        # Check for programming language
        lang, lang_confidence = self.language_detector.detect_language(text)
        if lang != ProgrammingLanguage.UNKNOWN and lang_confidence > 0.5:
            return True, lang_confidence

        # Keyword-based detection
        if keyword_matches >= 2:
            return True, min(keyword_matches / 5, 0.8)

        return False, 0.0

    def extract_programming_context(self, text: str) -> ProgrammingContext:
        """
        Extract programming context from query text.
        """
        context = ProgrammingContext()

        # Detect language
        lang, confidence = self.language_detector.detect_language(text)
        context.language = lang
        context.confidence = confidence

        # Parse error message
        error_analysis = self.error_parser.parse_error_message(text)
        context.errorType = error_analysis["error_type"]
        context.errorCode = error_analysis["error_code"]
        context.errorMessage = error_analysis["error_message"]

        # Extract stack trace
        stack_trace = self.error_parser.extract_stack_trace(text)
        if stack_trace:
            context.stackTrace = stack_trace
            context.hasStackTrace = True

        # Extract file location
        file_location = self.error_parser.extract_file_location(text)
        context.fileName = file_location["file_name"]
        context.lineNumber = file_location["line_number"]

        # Detect framework
        for framework, patterns in self.compiled_frameworks.items():
            if any(p.search(text) for p in patterns):
                context.framework = framework
                break

        # Extract code snippets
        code_snippets = self.code_detector.extract_code_snippets(text)
        if code_snippets:
            context.codeSnippet = code_snippets[0]["code"]
            # Update language if detected in code block
            if code_snippets[0]["language"] != "unknown":
                lang_map = {
                    "python": ProgrammingLanguage.PYTHON,
                    "javascript": ProgrammingLanguage.JAVASCRIPT,
                    "typescript": ProgrammingLanguage.TYPESCRIPT,
                    "java": ProgrammingLanguage.JAVA,
                    "cpp": ProgrammingLanguage.CPP,
                    "c#": ProgrammingLanguage.C_SHARP,
                    "go": ProgrammingLanguage.GO,
                    "rust": ProgrammingLanguage.RUST,
                    "php": ProgrammingLanguage.PHP,
                    "sql": ProgrammingLanguage.SQL,
                    "bash": ProgrammingLanguage.SHELL,
                    "shell": ProgrammingLanguage.SHELL,
                }
                detected = lang_map.get(code_snippets[0]["language"].lower())
                if detected:
                    context.language = detected

        # Determine error type
        if context.errorCode or context.hasStackTrace:
            context.isRuntimeError = True
        elif context.errorType == ErrorType.SYNTAX_ERROR:
            context.isCompilationError = True

        return context

    def get_intent_goal(self, text: str) -> IntentGoal:
        """
        Determine the appropriate IntentGoal for programming queries.
        """
        text_lower = text.lower()

        # Check for error/exception keywords
        if any(
            kw in text_lower
            for kw in ["error", "exception", "bug", "not working", "broken", "fix"]
        ):
            return IntentGoal.PROGRAMMING_ERROR

        # Check for debugging keywords
        if any(
            kw in text_lower
            for kw in ["debug", "debugging", "trace", "breakpoint", "step through"]
        ):
            return IntentGoal.CODE_DEBUG

        # Check for code review keywords
        if any(
            kw in text_lower
            for kw in ["review", "optimize", "refactor", "improve", "best practice"]
        ):
            return IntentGoal.CODE_REVIEW

        # Check for API integration keywords
        if any(
            kw in text_lower
            for kw in ["api", "integration", "connect", "endpoint", "rest", "graphql"]
        ):
            return IntentGoal.API_INTEGRATION

        # Default to troubleshooting for programming queries
        return IntentGoal.TROUBLESHOOTING

    def get_use_cases(self, context: ProgrammingContext) -> list[UseCase]:
        """
        Determine use cases based on programming context.
        """
        use_cases = [UseCase.DEBUGGING]

        if context.errorType != ErrorType.UNKNOWN:
            use_cases.append(UseCase.ERROR_RESOLUTION)

        if context.codeSnippet:
            use_cases.append(UseCase.CODE_FIX)

        if context.isRuntimeError or context.hasStackTrace:
            use_cases.append(UseCase.DEBUGGING)

        return use_cases


# Singleton instance
_programming_intent_extractor = None


def get_programming_intent_extractor() -> ProgrammingIntentExtractor:
    """Get or create the ProgrammingIntentExtractor singleton"""
    global _programming_intent_extractor
    if _programming_intent_extractor is None:
        _programming_intent_extractor = ProgrammingIntentExtractor()
    return _programming_intent_extractor
