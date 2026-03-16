"""
Intent Engine - Core Schema Definitions

This module defines the universal intent schema and related data structures
used across all components of the Intent Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# Define enums matching the TypeScript definitions from the docs
class IntentGoal(Enum):
    # Search-specific
    FIND_INFORMATION = "find_information"
    COMPARISON = "comparison"
    TROUBLESHOOTING = "troubleshooting"
    PURCHASE = "purchase"
    LOCAL_SERVICE = "local_service"
    NAVIGATION = "navigation"

    # Docs/Mail-specific
    DRAFT_DOCUMENT = "draft_document"
    COLLABORATE = "collaborate"
    ORGANIZE = "organize"
    ANALYZE = "analyze"
    SCHEDULE = "schedule"

    # Cross-product
    LEARN = "learn"
    CREATE = "create"
    REFLECT = "reflect"  # Diary

    # Programming & Development
    PROGRAMMING_ERROR = "programming_error"
    CODE_DEBUG = "code_debug"
    CODE_REVIEW = "code_review"
    API_INTEGRATION = "api_integration"


class UseCase(Enum):
    COMPARISON = "comparison"
    LEARNING = "learning"
    TROUBLESHOOTING = "troubleshooting"
    VERIFICATION = "verification"
    ENTERTAINMENT = "entertainment"
    COMMUNITY_ENGAGEMENT = "community_engagement"
    PROFESSIONAL_DEVELOPMENT = "professional_development"
    MARKET_RESEARCH = "market_research"

    # Programming & Development
    DEBUGGING = "debugging"
    CODE_FIX = "code_fix"
    ERROR_RESOLUTION = "error_resolution"
    CODE_OPTIMIZATION = "code_optimization"
    LEARNING_TO_CODE = "learning_to_code"


class ConstraintType(Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    RANGE = "range"
    DATATYPE = "datatype"


class Urgency(Enum):
    IMMEDIATE = "immediate"
    SOON = "soon"
    FLEXIBLE = "flexible"
    EXPLORATORY = "exploratory"


class SkillLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TemporalHorizon(Enum):
    IMMEDIATE = "immediate"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    LONGTERM = "longterm"
    FLEXIBLE = "flexible"


class Recency(Enum):
    BREAKING = "breaking"
    RECENT = "recent"
    EVERGREEN = "evergreen"
    HISTORICAL = "historical"


class Frequency(Enum):
    ONEOFF = "oneoff"
    RECURRING = "recurring"
    EXPLORATORY = "exploratory"
    FLEXIBLE = "flexible"


class EthicalDimension(Enum):
    PRIVACY = "privacy"
    SUSTAINABILITY = "sustainability"
    ETHICS = "ethics"
    ACCESSIBILITY = "accessibility"
    OPENNESS = "openness"


class ResultType(Enum):
    ANSWER = "answer"
    TUTORIAL = "tutorial"
    TOOL = "tool"
    MARKETPLACE = "marketplace"
    COMMUNITY = "community"

    # Programming-specific
    CODE_SNIPPET = "code_snippet"
    DOCUMENTATION = "documentation"
    STACK_OVERFLOW = "stack_overflow"
    GITHUB_REPO = "github_repo"
    API_REFERENCE = "api_reference"


class Complexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    ADVANCED = "advanced"


class ContentType(Enum):
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    FORM = "form"


class ProgrammingLanguage(Enum):
    """Common programming languages for intent extraction"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C_SHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SQL = "sql"
    SHELL = "shell"
    HTML = "html"
    CSS = "css"
    UNKNOWN = "unknown"


class ErrorType(Enum):
    """Types of programming errors"""

    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TYPE_ERROR = "type_error"
    NULL_REFERENCE = "null_reference"
    IMPORT_ERROR = "import_error"
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    COMPILATION_ERROR = "compilation_error"
    MEMORY_ERROR = "memory_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN = "unknown"


@dataclass
class Constraint:
    """Represents a constraint extracted from user input"""

    type: ConstraintType
    dimension: str  # 'language', 'region', 'price', 'license', 'format', 'recency'
    value: str | int | float | list[str | int | float] | list[int]  # Single value, range, or list
    hardFilter: bool  # Must exclude results violating this


@dataclass
class TemporalIntent:
    """Temporal aspects of user intent"""

    horizon: TemporalHorizon
    recency: Recency
    frequency: Frequency


@dataclass
class DocumentContext:
    """Context from open documents"""

    docId: str | None = None
    content: str | None = None  # First 1000 chars only, not persisted
    lastEditTime: str | None = None
    collaborators: int | None = None  # Count only, not names
    contentType: ContentType | None = None


@dataclass
class MeetingContext:
    """Context from calendar/meetings"""

    meetingId: str | None = None
    subject: str | None = None
    participantCount: int | None = None
    isRecurring: bool | None = None
    timeZone: str | None = None


@dataclass
class ProgrammingContext:
    """Context for programming-related queries"""

    language: ProgrammingLanguage = ProgrammingLanguage.UNKNOWN
    errorType: ErrorType = ErrorType.UNKNOWN
    errorCode: str | None = None  # e.g., "E0301", "TS2304"
    errorMessage: str | None = None  # e.g., "NameError: name 'x' is not defined"
    stackTrace: str | None = None  # Full or partial stack trace
    codeSnippet: str | None = None  # Code snippet from the query
    lineNumber: int | None = None  # Line number where error occurred
    fileName: str | None = None  # File name from error
    framework: str | None = None  # e.g., "Django", "React", "Spring"
    library: str | None = None  # e.g., "pandas", "lodash", "requests"
    isCompilationError: bool = False
    isRuntimeError: bool = False
    hasStackTrace: bool = False
    confidence: float = 0.0  # Confidence that this is a programming error


@dataclass
class EthicalSignal:
    """Ethical preferences extracted from intent"""

    dimension: EthicalDimension
    preference: str  # "privacy-first", "open-source", "carbon-neutral", etc.


@dataclass
class DeclaredIntent:
    """User-declared intent components"""

    query: str | None = None  # Free-form text
    goal: IntentGoal | None = None  # Structured goal
    constraints: list[Constraint] = field(default_factory=list)  # Hard filters
    negativePreferences: list[str] = field(default_factory=list)  # "not X", "no Y"
    urgency: Urgency = Urgency.FLEXIBLE
    budget: str | None = None  # "under 1000", "premium", null
    skillLevel: SkillLevel = SkillLevel.INTERMEDIATE


@dataclass
class InferredIntent:
    """Inferred intent components"""

    useCases: list[UseCase] = field(default_factory=list)  # [comparison, learning, troubleshooting, ...]
    temporalIntent: TemporalIntent | None = None
    documentContext: DocumentContext | None = None  # From open docs/emails
    meetingContext: MeetingContext | None = None  # From calendar/Meet
    programmingContext: ProgrammingContext | None = None  # From programming queries
    resultType: ResultType | None = None
    complexity: Complexity = Complexity.MODERATE
    ethicalSignals: list[EthicalSignal] = field(default_factory=list)  # Privacy, sustainability, etc.


@dataclass
class SessionFeedback:
    """Feedback captured during the session"""

    clicked: list[str] | None = None  # URLs clicked
    dwell: int | None = None  # Seconds on result
    reformulated: bool | None = None  # User refined query
    bounced: bool | None = None  # Left immediately


@dataclass
class UniversalIntent:
    """Main intent object matching the schema from the whitepaper"""

    # Unique session-scoped ID (not persistent)
    intentId: str

    # Product context (which service generated this)
    context: dict[str, Any]

    # Declared intent (user-supplied constraints and goals)
    declared: DeclaredIntent

    # Inferred intent (derived from context without tracking)
    inferred: InferredIntent

    # Feedback (captured in current session only)
    sessionFeedback: SessionFeedback = field(default_factory=SessionFeedback)

    # TTL: Auto-delete after session ends
    expiresAt: str = ""


@dataclass
class IntentExtractionRequest:
    """Request object for intent extraction API"""

    product: str  # 'search' | 'docs' | 'mail' | 'calendar' | 'meet' | 'forms' | 'diary' | 'sites'
    input: dict[str, str]  # TextInput | FormInput | DocumentInput | EventInput
    context: dict[str, Any]  # ExtractionContext
    options: dict[str, Any] | None = None  # ExtractionOptions


@dataclass
class IntentExtractionResponse:
    """Response object for intent extraction API"""

    intent: UniversalIntent
    extractionMetrics: dict[str, Any]  # confidence, extractedDimensions, warnings
