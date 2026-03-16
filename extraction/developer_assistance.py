"""
Intent Engine - Developer Assistance Module

This module provides developer-focused enhancements for programming queries:
- Enhanced search result formatting for code
- Debugging suggestions and tips
- Related error solutions
- Code snippet extraction and formatting
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from core.schema import ErrorType, ProgrammingContext, ProgrammingLanguage, UniversalIntent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DebuggingSuggestion:
    """A debugging suggestion for the user"""
    
    title: str
    description: str
    priority: int  # 1-5, 1 being highest
    category: str  # "quick_fix", "investigation", "prevention"
    code_example: str | None = None


@dataclass
class RelatedError:
    """Information about a related error"""
    
    error_name: str
    common_causes: list[str]
    typical_solutions: list[str]
    documentation_url: str | None = None


@dataclass
class ResearchPlan:
    """A structured plan for researching and resolving a programming issue"""
    
    investigation_steps: list[str] = field(default_factory=list)
    optimized_search_queries: dict[str, str] = field(default_factory=dict)
    key_concepts: list[str] = field(default_factory=list)
    consensus_check: str | None = None


@dataclass
class DeveloperAssistanceResponse:
    """Enhanced response for programming queries"""
    
    programming_context: ProgrammingContext
    suggestions: list[DebuggingSuggestion] = field(default_factory=list)
    related_errors: list[RelatedError] = field(default_factory=list)
    search_boost_factors: dict[str, float] = field(default_factory=dict)
    recommended_resources: list[str] = field(default_factory=list)
    quick_fixes: list[str] = field(default_factory=list)
    research_plan: ResearchPlan | None = None


class DynamicResearchPlanner:
    """
    Generates a structured research and debugging plan based on programming context.
    Designed for speed and high performance.
    """

    def generate_plan(self, context: ProgrammingContext, query: str) -> ResearchPlan:
        """
        Generate a dynamic research plan.
        """
        plan = ResearchPlan()
        
        # 1. Generate investigation steps
        plan.investigation_steps = self._generate_investigation_steps(context)
        
        # 2. Generate optimized search queries
        plan.optimized_search_queries = self._generate_search_queries(context, query)
        
        # 3. Identify key concepts
        plan.key_concepts = self._identify_key_concepts(context)
        
        return plan

    def _generate_investigation_steps(self, context: ProgrammingContext) -> list[str]:
        steps = []
        
        # Base steps
        if context.hasStackTrace:
            steps.append("Analyze the stack trace from bottom to top to identify your code's entry point.")
        
        # Error specific steps
        if context.errorType == ErrorType.IMPORT_ERROR:
            steps.extend([
                "Check if the package is installed in your current environment.",
                "Verify your virtual environment is activated.",
                "Check for circular imports in your module structure."
            ])
        elif context.errorType == ErrorType.NULL_REFERENCE:
            steps.extend([
                "Locate the exact line where the null/undefined access occurs.",
                "Check the initialization of the object being accessed.",
                "Verify if a previous function call returned null unexpectedly."
            ])
        elif context.errorType == ErrorType.SYNTAX_ERROR:
            steps.extend([
                "Check for missing delimiters (brackets, quotes, parentheses).",
                "Verify indentation levels (especially for Python).",
                "Check for accidental use of reserved keywords."
            ])
        
        # Framework specific
        if context.framework == "React":
            steps.append("Verify you aren't calling hooks inside loops or conditions.")
        elif context.framework == "Django":
            steps.append("Check if your model migrations are up to date.")
            
        if not steps:
            steps.append("Reproduce the error with the minimal amount of code possible.")
            steps.append("Add print/log statements around the suspected failure point.")
            
        return steps

    def _generate_search_queries(self, context: ProgrammingContext, query: str) -> dict[str, str]:
        queries = {}
        lang = context.language.value if context.language != ProgrammingLanguage.UNKNOWN else ""
        error = context.errorMessage or ""
        framework = context.framework or ""
        
        # Clean query for search
        base_query = query.replace("```", "").strip()
        
        # StackOverflow query
        so_query = f"[{lang}] {error}" if lang else error
        if framework:
            so_query = f"[{framework.lower()}] {so_query}"
        queries["StackOverflow"] = so_query.strip()
        
        # GitHub Issues query
        if framework or lang:
            queries["GitHub Issues"] = f"is:issue {framework or lang} {error}".strip()
            
        # Documentation query
        if framework:
            queries["Official Docs"] = f"{framework} {context.errorType.value} documentation".strip()
        elif lang:
            queries["Official Docs"] = f"{lang} {context.errorType.value} manual".strip()
            
        return queries

    def _identify_key_concepts(self, context: ProgrammingContext) -> list[str]:
        concepts = []
        
        if context.errorType == ErrorType.NULL_REFERENCE:
            concepts.extend(["Null Safety", "Optional Chaining", "Defensive Programming"])
        elif context.errorType == ErrorType.MEMORY_ERROR:
            concepts.extend(["Memory Leak", "Garbage Collection", "Heap vs Stack"])
        elif context.errorType == ErrorType.IMPORT_ERROR:
            concepts.extend(["Dependency Management", "Module Resolution", "Virtual Environments"])
            
        if context.framework == "React":
            concepts.append("React Lifecycle")
            concepts.append("Hook Rules")
            
        return concepts


class DeveloperAssistanceEngine:
    """
    Provides developer-focused assistance for programming queries.
    Enhances search results and provides debugging guidance.
    """

    def __init__(self):
        self.research_planner = DynamicResearchPlanner()
        # Common error patterns and their solutions
        self.error_solutions = {
            ErrorType.SYNTAX_ERROR: {
                "quick_fixes": [
                    "Check for missing colons, parentheses, or brackets",
                    "Verify proper indentation (Python)",
                    "Look for unclosed strings or comments",
                    "Check for reserved keywords used as identifiers",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Use a Linter",
                        description="Run a code linter to identify syntax issues automatically",
                        priority=1,
                        category="prevention",
                        code_example="# Python: pylint or flake8\n# JavaScript: eslint\n# Run: linter your_file.py",
                    ),
                    DebuggingSuggestion(
                        title="Check Recent Changes",
                        description="Review recently modified code for syntax mistakes",
                        priority=2,
                        category="investigation",
                    ),
                ],
            },
            ErrorType.TYPE_ERROR: {
                "quick_fixes": [
                    "Verify variable types before operations",
                    "Check function return types",
                    "Ensure proper type conversions",
                    "Look for None/null values being used incorrectly",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Add Type Checking",
                        description="Use type hints or TypeScript to catch type errors early",
                        priority=1,
                        category="prevention",
                        code_example="# Python type hints\ndef greet(name: str) -> str:\n    return f'Hello, {name}'",
                    ),
                    DebuggingSuggestion(
                        title="Log Variable Types",
                        description="Print or log variable types to identify mismatches",
                        priority=2,
                        category="investigation",
                        code_example="# Python\nprint(type(variable_name))\nprint(variable_name)",
                    ),
                ],
            },
            ErrorType.NULL_REFERENCE: {
                "quick_fixes": [
                    "Add null/undefined checks before accessing properties",
                    "Use optional chaining (?.) in JavaScript",
                    "Initialize variables before use",
                    "Check function return values for null",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Use Null-Safe Operators",
                        description="Implement null-safe patterns in your code",
                        priority=1,
                        category="prevention",
                        code_example="// JavaScript optional chaining\nconst value = obj?.property?.nested;\n\n// Python with getattr\nvalue = getattr(obj, 'property', default_value)",
                    ),
                    DebuggingSuggestion(
                        title="Add Input Validation",
                        description="Validate inputs at function boundaries",
                        priority=2,
                        category="prevention",
                    ),
                ],
            },
            ErrorType.IMPORT_ERROR: {
                "quick_fixes": [
                    "Verify the module/package is installed",
                    "Check the import path spelling",
                    "Ensure virtual environment is activated",
                    "Look for circular imports",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Check Installation",
                        description="Verify the package is installed in your environment",
                        priority=1,
                        category="quick_fix",
                        code_example="# Python\npip install package_name\n\n# Node.js\nnpm install package_name",
                    ),
                    DebuggingSuggestion(
                        title="Verify Import Path",
                        description="Double-check the module path and name",
                        priority=2,
                        category="investigation",
                    ),
                ],
            },
            ErrorType.RUNTIME_ERROR: {
                "quick_fixes": [
                    "Check the stack trace for the error location",
                    "Verify input data and edge cases",
                    "Look for infinite loops or recursion",
                    "Check resource availability (files, network, memory)",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Analyze Stack Trace",
                        description="Read the stack trace from bottom to top to find the root cause",
                        priority=1,
                        category="investigation",
                    ),
                    DebuggingSuggestion(
                        title="Add Error Handling",
                        description="Wrap risky code in try-catch blocks",
                        priority=2,
                        category="prevention",
                        code_example="# Python\ntry:\n    risky_operation()\nexcept SpecificError as e:\n    print(f'Error: {e}')\n    handle_error()",
                    ),
                ],
            },
            ErrorType.DATABASE_ERROR: {
                "quick_fixes": [
                    "Check database connection string",
                    "Verify table and column names",
                    "Look for SQL syntax errors",
                    "Check permissions and access rights",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Test Connection",
                        description="Verify database connectivity separately",
                        priority=1,
                        category="quick_fix",
                    ),
                    DebuggingSuggestion(
                        title="Use Parameterized Queries",
                        description="Prevent SQL injection and syntax errors",
                        priority=2,
                        category="prevention",
                    ),
                ],
            },
            ErrorType.API_ERROR: {
                "quick_fixes": [
                    "Check API endpoint URL",
                    "Verify authentication credentials",
                    "Look at rate limiting headers",
                    "Check request format and headers",
                ],
                "suggestions": [
                    DebuggingSuggestion(
                        title="Test with curl/Postman",
                        description="Test the API endpoint directly to isolate the issue",
                        priority=1,
                        category="investigation",
                        code_example="# Test with curl\ncurl -X GET https://api.example.com/endpoint \\\n  -H 'Authorization: Bearer YOUR_TOKEN'",
                    ),
                    DebuggingSuggestion(
                        title="Check API Documentation",
                        description="Review the API docs for correct usage",
                        priority=2,
                        category="investigation",
                    ),
                ],
            },
        }

        # Language-specific resources
        self.language_resources = {
            ProgrammingLanguage.PYTHON: [
                "https://docs.python.org/3/tutorial/errors.html",
                "https://realpython.com/python-exceptions/",
                "https://stackoverflow.com/questions/tagged/python",
            ],
            ProgrammingLanguage.JAVASCRIPT: [
                "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors",
                "https://javascript.info/",
                "https://stackoverflow.com/questions/tagged/javascript",
            ],
            ProgrammingLanguage.TYPESCRIPT: [
                "https://www.typescriptlang.org/docs/",
                "https://stackoverflow.com/questions/tagged/typescript",
            ],
            ProgrammingLanguage.JAVA: [
                "https://docs.oracle.com/javase/tutorial/essential/exceptions/",
                "https://stackoverflow.com/questions/tagged/java",
            ],
            ProgrammingLanguage.CPP: [
                "https://en.cppreference.com/w/cpp/error",
                "https://stackoverflow.com/questions/tagged/c%2B%2B",
            ],
            ProgrammingLanguage.GO: [
                "https://go.dev/blog/error-handling-and-go",
                "https://stackoverflow.com/questions/tagged/go",
            ],
            ProgrammingLanguage.RUST: [
                "https://doc.rust-lang.org/book/ch09-00-error-handling.html",
                "https://stackoverflow.com/questions/tagged/rust",
            ],
        }

        # Search boost factors for programming queries
        self.programming_search_boost = {
            "stackoverflow.com": 1.5,
            "github.com": 1.4,
            "official documentation": 1.3,
            "medium.com": 1.1,
            "dev.to": 1.2,
            "reddit.com/r/learnprogramming": 1.1,
            "reddit.com/r/programming": 1.1,
        }

    def generate_assistance_response(
        self,
        intent: UniversalIntent,
    ) -> DeveloperAssistanceResponse:
        """
        Generate a developer assistance response based on intent.
        """
        programming_context = intent.inferred.programmingContext
        if not programming_context:
            raise ValueError("No programming context in intent")

        response = DeveloperAssistanceResponse(programming_context=programming_context)

        # Generate dynamic research plan
        query = intent.declared.query or ""
        response.research_plan = self.research_planner.generate_plan(programming_context, query)

        # Add suggestions based on error type
        if programming_context.errorType in self.error_solutions:
            solutions = self.error_solutions[programming_context.errorType]
            response.quick_fixes = solutions["quick_fixes"]
            response.suggestions = solutions["suggestions"]

        # Add related errors
        response.related_errors = self._get_related_errors(programming_context)

        # Add search boost factors
        response.search_boost_factors = self.programming_search_boost.copy()

        # Add recommended resources based on language
        if programming_context.language in self.language_resources:
            response.recommended_resources = self.language_resources[
                programming_context.language
            ]

        # Add language-specific suggestions
        response.suggestions.extend(self._get_language_specific_suggestions(programming_context))

        return response

    def _get_related_errors(self, context: ProgrammingContext) -> list[RelatedError]:
        """
        Get related errors based on the detected error type.
        """
        related = []

        # Common error relationships
        error_relationships = {
            ErrorType.SYNTAX_ERROR: [
                RelatedError(
                    error_name="IndentationError",
                    common_causes=["Mixed tabs and spaces", "Inconsistent indentation"],
                    typical_solutions=["Use consistent indentation", "Configure editor"],
                    documentation_url="https://docs.python.org/3/reference/compound_stmts.html",
                ),
            ],
            ErrorType.TYPE_ERROR: [
                RelatedError(
                    error_name="AttributeError",
                    common_causes=["Calling method on wrong type", "None has no attribute"],
                    typical_solutions=["Check object type", "Add null checks"],
                ),
            ],
            ErrorType.NULL_REFERENCE: [
                RelatedError(
                    error_name="TypeError: Cannot read property",
                    common_causes=["Accessing property of undefined", "Missing initialization"],
                    typical_solutions=["Add existence checks", "Use optional chaining"],
                ),
            ],
            ErrorType.IMPORT_ERROR: [
                RelatedError(
                    error_name="ModuleNotFoundError",
                    common_causes=["Package not installed", "Wrong Python environment"],
                    typical_solutions=["pip install package", "Activate correct venv"],
                ),
            ],
        }

        if context.errorType in error_relationships:
            related = error_relationships[context.errorType]

        return related

    def _get_language_specific_suggestions(
        self,
        context: ProgrammingContext,
    ) -> list[DebuggingSuggestion]:
        """
        Get suggestions specific to the programming language.
        """
        suggestions = []

        if context.language == ProgrammingLanguage.PYTHON:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Use Python Debugger (pdb)",
                    description="Insert breakpoints and step through code",
                    priority=2,
                    category="investigation",
                    code_example="import pdb; pdb.set_trace()\n# Or use: breakpoint() in Python 3.7+",
                ),
                DebuggingSuggestion(
                    title="Check Python Version",
                    description="Ensure you're using the correct Python version",
                    priority=3,
                    category="investigation",
                    code_example="python --version\npython3 --version",
                ),
            ])
        elif context.language == ProgrammingLanguage.JAVASCRIPT:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Use Browser DevTools",
                    description="Open console and use debugger statements",
                    priority=1,
                    category="investigation",
                    code_example="debugger; // Add in code\n// Or use console.log()",
                ),
                DebuggingSuggestion(
                    title="Check Node Version",
                    description="Ensure Node.js version is compatible",
                    priority=3,
                    category="investigation",
                    code_example="node --version\nnpm --version",
                ),
            ])
        elif context.language == ProgrammingLanguage.JAVA:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Use Java Debugger (jdb)",
                    description="Debug Java applications from command line",
                    priority=2,
                    category="investigation",
                ),
                DebuggingSuggestion(
                    title="Check Stack Trace",
                    description="Java exceptions include detailed stack traces",
                    priority=1,
                    category="investigation",
                ),
            ])
        elif context.language == ProgrammingLanguage.CPP:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Use GDB Debugger",
                    description="GNU Debugger for C/C++",
                    priority=1,
                    category="investigation",
                    code_example="g++ -g program.cpp -o program\ngdb ./program",
                ),
                DebuggingSuggestion(
                    title="Check Compilation Warnings",
                    description="Enable all warnings during compilation",
                    priority=2,
                    category="prevention",
                    code_example="g++ -Wall -Wextra -pedantic program.cpp",
                ),
            ])
        elif context.language == ProgrammingLanguage.GO:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Use Go Debugger (delve)",
                    description="Delve is a debugger for Go",
                    priority=1,
                    category="investigation",
                    code_example="go install github.com/go-delve/delve/cmd/dlv@latest\ndlv debug",
                ),
            ])
        elif context.language == ProgrammingLanguage.RUST:
            suggestions.extend([
                DebuggingSuggestion(
                    title="Read Compiler Errors Carefully",
                    description="Rust compiler errors are very detailed and helpful",
                    priority=1,
                    category="investigation",
                ),
                DebuggingSuggestion(
                    title="Use Rust Analyzer",
                    description="IDE extension with real-time error checking",
                    priority=2,
                    category="prevention",
                ),
            ])

        return suggestions

    def format_search_query_for_programming(
        self,
        query: str,
        context: ProgrammingContext,
    ) -> dict[str, Any]:
        """
        Format and enhance search query for programming context.
        Returns query modifications and boost factors.
        """
        enhancements = {
            "original_query": query,
            "enhanced_query": query,
            "site_boosts": {},
            "filters": [],
            "suggested_tags": [],
        }

        # Add language tag
        if context.language != ProgrammingLanguage.UNKNOWN:
            lang_tag = f"[{context.language.value}]"
            enhancements["enhanced_query"] = f"{query} {lang_tag}"
            enhancements["suggested_tags"].append(context.language.value)

        # Add error type tag
        if context.errorType != ErrorType.UNKNOWN:
            enhancements["suggested_tags"].append(context.errorType.value)

        # Add site-specific boosts
        if context.errorType == ErrorType.IMPORT_ERROR:
            # For import errors, boost official docs
            enhancements["site_boosts"]["docs.python.org"] = 2.0
            enhancements["site_boosts"]["npmjs.com"] = 2.0
            enhancements["site_boosts"]["package.json"] = 1.5

        if context.hasStackTrace:
            # For stack traces, boost Stack Overflow
            enhancements["site_boosts"]["stackoverflow.com"] = 1.8

        if context.codeSnippet:
            # For code snippets, boost GitHub
            enhancements["site_boosts"]["github.com"] = 1.5

        return enhancements


# Singleton instance
_developer_assistance_engine = None


def get_developer_assistance_engine() -> DeveloperAssistanceEngine:
    """Get or create the DeveloperAssistanceEngine singleton"""
    global _developer_assistance_engine
    if _developer_assistance_engine is None:
        _developer_assistance_engine = DeveloperAssistanceEngine()
    return _developer_assistance_engine
