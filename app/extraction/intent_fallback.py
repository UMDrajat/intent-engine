"""
Intent Engine - Intent Fallback & Enhancement Module

Fixes null goal detection gaps with intelligent fallback logic.

Features:
1. ✅ Fallback goal detection from use cases
2. ✅ Query pattern recognition ("how to" → learn, "best" → comparison)
3. ✅ Enhanced use case inference
4. ✅ Null safety for all intent fields

Usage:
    from app.extraction.intent_fallback import enhance_intent_with_fallback

    enhanced_intent = enhance_intent_with_fallback(original_intent, query)
"""

import logging
import re
from typing import Optional

from app.core.schema import (
    DeclaredIntent,
    Goal,
    InferredIntent,
    UniversalIntent,
    UseCase,
)

logger = logging.getLogger(__name__)


# Query pattern mappings for fallback goal detection
QUERY_PATTERNS = {
    # Learning patterns
    Goal.LEARN: [
        r"\bhow to\b",
        r"\blearn\b",
        r"\btutorial\b",
        r"\bguide\b",
        r"\bbeginner\b",
        r"\bintroduction\b",
        r"\bgetting started\b",
        r"\bwhat is\b",
        r"\bexplain\b",
        r"\bbecome a\b",
        r"\bcareer\b",
        r"\bskills?\b",
    ],
    # Comparison patterns
    Goal.COMPARISON: [
        r"\bbest\b",
        r"\bvs\b",
        r"\bversus\b",
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\btop\b",
        r"\breview\b",
        r"\branking\b",
        r"\bunder\b",  # "under 50000" implies comparison shopping
        r"\bcheap\b",
        r"\baffordable\b",
    ],
    # Troubleshooting patterns
    Goal.PROGRAMMING_ERROR: [
        r"\bfix\b",
        r"\berror\b",
        r"\bbug\b",
        r"\bdebug\b",
        r"\bissue\b",
        r"\bproblem\b",
        r"\bnot working\b",
        r"\bfailed\b",
        r"\bexception\b",
        r"\btraceback\b",
        r"\bimport error\b",
        r"\bmodule not found\b",
    ],
    # Purchase patterns
    Goal.PURCHASE: [
        r"\bbuy\b",
        r"\bpurchase\b",
        r"\border\b",
        r"\bprice\b",
        r"\bdiscount\b",
        r"\bdeal\b",
        r"\bcoupon\b",
    ],
}


def enhance_intent_with_fallback(
    intent: Optional[UniversalIntent], query: str
) -> UniversalIntent:
    """
    Enhance intent with fallback logic for null/missing fields.

    Args:
        intent: Original intent (may have null fields)
        query: Original user query

    Returns:
        Enhanced intent with all fields populated
    """
    if intent is None:
        # Create new intent from query
        logger.info(f"Creating new intent from query: {query[:50]}")
        return create_intent_from_query(query)

    # Ensure declared intent exists
    if not intent.declared:
        intent.declared = DeclaredIntent()

    # Ensure inferred intent exists
    if not intent.inferred:
        intent.inferred = InferredIntent()

    # Fix null goal
    if not intent.declared.goal:
        detected_goal = detect_goal_from_query(query)
        intent.declared.goal = detected_goal
        logger.info(f"Detected goal from query pattern: {detected_goal.value}")

    # Fix null use cases
    if not intent.inferred.useCases:
        inferred_use_cases = infer_use_cases_from_query(query, intent.declared.goal)
        intent.inferred.useCases = inferred_use_cases
        logger.info(f"Inferred use cases: {[uc.value for uc in inferred_use_cases]}")

    # Fix null skill level
    if not intent.declared.skillLevel:
        detected_skill = detect_skill_level(query)
        intent.declared.skillLevel = detected_skill
        logger.info(f"Detected skill level: {detected_skill}")

    return intent


def create_intent_from_query(query: str) -> UniversalIntent:
    """Create complete intent object from query"""
    goal = detect_goal_from_query(query)
    use_cases = infer_use_cases_from_query(query, goal)
    skill_level = detect_skill_level(query)

    return UniversalIntent(
        declared=DeclaredIntent(
            goal=goal,
            query=query,
            skillLevel=skill_level,
            constraints=[],
        ),
        inferred=InferredIntent(
            useCases=use_cases,
            ethicalSignals=[],
        ),
    )


def detect_goal_from_query(query: str) -> Goal:
    """
    Detect intent goal from query patterns.

    Uses regex matching on query to determine user intent.

    Args:
        query: User query string

    Returns:
        Detected Goal enum value
    """
    query_lower = query.lower()

    # Check each goal pattern
    for goal, patterns in QUERY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                logger.debug(
                    f"Query '{query[:30]}' matched pattern '{pattern}' for goal {goal.value}"
                )
                return goal

    # Default to LEARN if no pattern matches
    logger.debug(f"No pattern matched for query '{query[:30]}', defaulting to LEARN")
    return Goal.LEARN


def infer_use_cases_from_query(
    query: str, goal: Optional[Goal] = None
) -> list[UseCase]:
    """
    Infer use cases from query and goal.

    Args:
        query: User query
        goal: Detected goal (optional)

    Returns:
        List of inferred UseCase enums
    """
    use_cases = []
    query_lower = query.lower()

    # Learning-related use cases
    if goal == Goal.LEARN or any(
        kw in query_lower for kw in ["learn", "tutorial", "guide", "course"]
    ):
        use_cases.append(UseCase.LEARNING)

    # Troubleshooting use cases
    if goal == Goal.PROGRAMMING_ERROR or any(
        kw in query_lower for kw in ["fix", "error", "debug", "issue"]
    ):
        use_cases.append(UseCase.TROUBLESHOOTING)
        use_cases.append(UseCase.DEBUGGING)

    # Shopping use cases
    if goal == Goal.COMPARISON or goal == Goal.PURCHASE:
        if any(kw in query_lower for kw in ["laptop", "buy", "price", "best"]):
            use_cases.append(UseCase.SHOPPING)

    # Research use cases
    if any(kw in query_lower for kw in ["research", "study", "analysis"]):
        use_cases.append(UseCase.RESEARCH)

    # Career use cases
    if any(kw in query_lower for kw in ["career", "job", "become", "salary"]):
        use_cases.append(UseCase.CAREER)

    # Default to LEARNING if nothing else matched
    if not use_cases:
        use_cases.append(UseCase.LEARNING)

    return use_cases


def detect_skill_level(query: str):
    """
    Detect user skill level from query.

    Args:
        query: User query

    Returns:
        SkillLevel enum value
    """
    query_lower = query.lower()

    # Beginner indicators
    beginner_keywords = [
        "beginner",
        "basic",
        "introduction",
        "starter",
        "fundamentals",
        "101",
    ]
    if any(kw in query_lower for kw in beginner_keywords):
        return SkillLevel.BEGINNER

    # Advanced indicators
    advanced_keywords = ["advanced", "expert", "mastery", "deep dive", "professional"]
    if any(kw in query_lower for kw in advanced_keywords):
        return SkillLevel.ADVANCED

    # Expert indicators
    expert_keywords = ["expert", "professional", "enterprise", "architecture"]
    if any(kw in query_lower for kw in expert_keywords):
        return SkillLevel.EXPERT

    # Default to INTERMEDIATE
    return SkillLevel.INTERMEDIATE


# Import SkillLevel at module level to avoid circular imports
from app.core.schema import SkillLevel


def get_fallback_intent(query: str) -> UniversalIntent:
    """
    Get fallback intent when extraction fails.

    This is a convenience function for creating a complete intent
    from scratch when the extraction service fails.

    Args:
        query: User query

    Returns:
        Complete UniversalIntent object
    """
    return create_intent_from_query(query)
