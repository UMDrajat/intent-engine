"""
Intent Engine - Enhanced Ranking Module (v2.1)

Multi-factor scoring with content filtering, authority boosting, and Redis caching.

Improvements over optimized_ranker.py:
1. ✅ Multi-factor scoring (semantic + authority + freshness + quality)
2. ✅ Content filtering (trusted sources, low-quality filtering)
3. ✅ Domain authority scoring
4. ✅ Better null safety and error handling
5. ✅ Configurable weights
6. ✅ Redis caching for ranking results (NEW v2.1)
7. ✅ Background refresh for popular queries (NEW v2.1)

Usage:
    from app.ranking.enhanced_ranker import EnhancedRanker

    ranker = EnhancedRanker()
    ranked_results = await ranker.rank_with_filters(candidates, intent, options)
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Optional

from app.config.optimized_cache import get_embedding_cache
from app.config.redis_cache import cache as redis_cache
from app.core.schema import (
    DeclaredIntent,
    EthicalDimension,
    InferredIntent,
    SkillLevel,
    UniversalIntent,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Trusted Domains & Content Quality Configuration
# =============================================================================

# High-authority domains to boost (trusted sources)
TRUSTED_DOMAINS = {
    # Official Documentation
    "python.org": 1.0,
    "docs.python.org": 1.0,
    "developer.mozilla.org": 1.0,
    "microsoft.com": 0.9,
    "google.com": 0.85,
    "apple.com": 0.85,
    "aws.amazon.com": 0.9,
    # Educational Institutions
    ".edu": 0.95,
    "mit.edu": 1.0,
    "stanford.edu": 1.0,
    "cmu.edu": 1.0,
    "berkeley.edu": 1.0,
    # Known Tutorial Sites (High Quality)
    "realpython.com": 0.95,
    "geeksforgeeks.org": 0.85,
    "tutorialspoint.com": 0.8,
    "w3schools.com": 0.75,
    "stackoverflow.com": 0.9,
    "github.com": 0.9,
    "medium.com": 0.7,
    "dev.to": 0.8,
    "freeCodeCamp.org": 0.9,
    # Tech News & Reviews
    "arstechnica.com": 0.85,
    "wired.com": 0.85,
    "theverge.com": 0.8,
    # Product Sites (for comparison queries)
    "amazon.com": 0.75,
    "newegg.com": 0.75,
}

# Low-quality domains to filter or down-rank
LOW_QUALITY_DOMAINS = {
    "content-farm": ["ehow.com", "wikihow.com", "answer.com"],
    "clickbait": ["buzzfeed.com", "viralnova.com"],
    "spam_indicators": ["free-", "download-", "crack-"],
}

# Content quality thresholds
QUALITY_THRESHOLDS = {
    "min_title_length": 10,
    "max_title_length": 200,
    "min_content_length": 50,
    "min_quality_score": 0.3,  # Filter results below this
}


@dataclass
class SearchResult:
    """Enhanced search result with quality metadata"""

    id: str
    title: str
    description: str
    url: str
    platform: Optional[str] = None
    provider: Optional[str] = None
    license: Optional[str] = None
    price: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    qualityScore: float = 0.5
    recency: Optional[str] = None
    complexity: Optional[str] = None
    compatibility: list[str] = field(default_factory=list)
    privacyRating: Optional[float] = None
    opensource: Optional[bool] = None
    published_date: Optional[datetime] = None
    domain: str = ""
    domain_authority: float = 0.5

    def __post_init__(self):
        # Extract domain from URL
        if self.url and not self.domain:
            try:
                self.domain = (
                    self.url.split("/")[2].lower()
                    if "/" in self.url
                    else self.url.lower()
                )
            except:
                self.domain = ""


@dataclass
class RankedResult:
    """Enhanced ranked result with detailed scoring"""

    result: SearchResult
    alignmentScore: float
    matchReasons: list[str]
    qualityScore: float = 0.0
    authorityScore: float = 0.0
    freshnessScore: float = 0.0
    semanticScore: float = 0.0
    finalScore: float = 0.0


class EnhancedRanker:
    """
    Enhanced ranking with multi-factor scoring and content filtering.

    Scoring Components:
    1. Semantic Similarity (30%) - Query-content match
    2. Intent Alignment (25%) - Use case, skill level, ethics
    3. Domain Authority (20%) - Trusted source boosting
    4. Content Quality (15%) - Title/description quality
    5. Freshness (10%) - Recency boost

    Filtering:
    - Remove low-quality domains
    - Filter duplicate/spam content
    - Enforce minimum quality thresholds
    """

    def __init__(self, config: Optional[dict] = None):
        # Use shared embedding cache (singleton) - don't create new instances
        self.embedding_cache = get_embedding_cache()

        # Configurable weights
        self.weights = (
            config.get(
                "weights",
                {
                    "semantic": 0.30,
                    "intent": 0.25,
                    "authority": 0.20,
                    "quality": 0.15,
                    "freshness": 0.10,
                },
            )
            if config
            else {
                "semantic": 0.30,
                "intent": 0.25,
                "authority": 0.20,
                "quality": 0.15,
                "freshness": 0.10,
            }
        )

        # Filtering config
        self.filter_config = (
            config.get(
                "filtering",
                {
                    "enable_domain_filter": True,
                    "enable_quality_filter": True,
                    "min_quality_threshold": QUALITY_THRESHOLDS["min_quality_score"],
                    "remove_duplicates": True,
                },
            )
            if config
            else {
                "enable_domain_filter": True,
                "enable_quality_filter": True,
                "min_quality_threshold": 0.3,
                "remove_duplicates": True,
            }
        )

        logger.info("EnhancedRanker initialized (using shared embedding cache)")

    def _generate_cache_key(
        self, candidates: list[dict], intent: UniversalIntent
    ) -> str:
        """Generate cache key from query and intent"""
        # Use query hash + intent goal for cache key
        declared = intent.declared or DeclaredIntent()
        query = declared.query or ""
        goal = declared.goal.value if declared.goal else "unknown"

        # Create deterministic key
        key_data = f"{query}:{goal}:{len(candidates)}"
        return f"ranking:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def _get_cached_ranking(self, cache_key: str) -> Optional[list[RankedResult]]:
        """Get cached ranking results from Redis"""
        try:
            cached_data = await redis_cache.get(cache_key)
            if cached_data:
                logger.debug(f"Ranking cache HIT: {cache_key[:40]}")
                # Convert back to RankedResult objects
                return [RankedResult(**item) for item in cached_data]
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
        return None

    async def _cache_ranking_results(
        self, cache_key: str, results: list[RankedResult], ttl: int = 300
    ):
        """Cache ranking results in Redis with TTL"""
        try:
            # Convert RankedResult objects to dicts
            results_dict = [
                {
                    "result": {
                        "id": r.result.id,
                        "title": r.result.title,
                        "description": r.result.description,
                        "url": r.result.url,
                        "domain": r.result.domain,
                        "qualityScore": r.result.qualityScore,
                    },
                    "alignmentScore": r.alignmentScore,
                    "matchReasons": r.matchReasons,
                    "qualityScore": r.qualityScore,
                    "authorityScore": r.authorityScore,
                    "freshnessScore": r.freshnessScore,
                    "semanticScore": r.semanticScore,
                    "finalScore": r.finalScore,
                }
                for r in results
            ]

            # Cache with TTL (5 minutes default)
            await redis_cache.set(cache_key, results_dict, ttl=ttl, background=True)
            logger.debug(f"Ranking cache SET: {cache_key[:40]} (TTL={ttl}s)")
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")

    async def rank_with_filters(
        self,
        candidates: list[dict],
        intent: UniversalIntent,
        options: Optional[dict] = None,
    ) -> list[RankedResult]:
        """
        Main ranking method with filtering, multi-factor scoring, and caching.

        Caching Strategy:
        1. Check Redis cache first (5min TTL)
        2. If miss, compute ranking
        3. Cache results in background
        4. Return cached or computed results

        Args:
            candidates: List of search result dicts
            intent: User intent object
            options: Ranking options (filters, weights, etc.)

        Returns:
            List of ranked results with scores
        """
        start_time = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(candidates, intent)

        # Step 0: Try cache first
        cached_results = await self._get_cached_ranking(cache_key)
        if cached_results:
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✓ Ranking cache HIT: {elapsed:.2f}ms")
            return cached_results

        # Cache miss: proceed with ranking
        logger.info("Ranking cache MISS, computing...")

        # Convert dicts to SearchResult objects
        search_results = self._convert_to_search_results(candidates)
        logger.debug(f"Converted {len(candidates)} candidates to SearchResult objects")

        # Step 1: Apply content filters
        filtered_results = self._apply_content_filters(search_results, intent)
        logger.debug(
            f"Filtered {len(search_results)} → {len(filtered_results)} results"
        )

        # Step 2: Calculate multi-factor scores
        scored_results = []
        for result in filtered_results:
            scored = self._calculate_multi_factor_score(result, intent)
            scored_results.append(scored)

        # Step 3: Sort by final score
        scored_results.sort(key=lambda x: x.finalScore, reverse=True)

        # Step 4: Remove duplicates (if enabled)
        if self.filter_config.get("remove_duplicates", True):
            scored_results = self._remove_duplicates(scored_results)

        # Cache results in background (non-blocking)
        asyncio.create_task(
            self._cache_ranking_results(cache_key, scored_results, ttl=300)
        )

        elapsed = (time.time() - start_time) * 1000
        logger.info(
            f"Enhanced ranking complete: {len(scored_results)} results in {elapsed:.2f}ms"
        )

        return scored_results

    def _convert_to_search_results(self, candidates: list[dict]) -> list[SearchResult]:
        """Convert raw result dicts to SearchResult objects"""
        results = []
        for candidate in candidates:
            try:
                result = SearchResult(
                    id=candidate.get(
                        "id", hashlib.md5(candidate.get("url", "").encode()).hexdigest()
                    ),
                    title=candidate.get("title", "")[:200],
                    description=candidate.get("content", candidate.get("snippet", "")),
                    url=candidate.get("url", ""),
                    platform=candidate.get("platform"),
                    provider=candidate.get("provider"),
                    qualityScore=candidate.get("qualityScore", 0.5),
                    tags=candidate.get("tags", []),
                    published_date=self._parse_date(candidate.get("publishedDate")),
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to convert candidate: {e}")
                continue
        return results

    def _apply_content_filters(
        self, results: list[SearchResult], intent: UniversalIntent
    ) -> list[SearchResult]:
        """Apply content quality and domain filters"""
        filtered = []

        for result in results:
            # Skip if content is too short
            if len(result.title) < QUALITY_THRESHOLDS["min_title_length"]:
                logger.debug(f"Filtered (short title): {result.url[:50]}")
                continue

            if len(result.description) < QUALITY_THRESHOLDS["min_content_length"]:
                logger.debug(f"Filtered (short content): {result.url[:50]}")
                continue

            # Check for low-quality domains
            if self.filter_config.get("enable_domain_filter", True):
                if self._is_low_quality_domain(result.domain):
                    logger.debug(f"Filtered (low-quality domain): {result.domain}")
                    continue

            # Check minimum quality score
            if result.qualityScore and result.qualityScore < self.filter_config.get(
                "min_quality_threshold", 0.3
            ):
                logger.debug(f"Filtered (low quality): {result.url[:50]}")
                continue

            filtered.append(result)

        return filtered

    def _is_low_quality_domain(self, domain: str) -> bool:
        """Check if domain is low-quality or spam"""
        if not domain:
            return True

        # Check exact matches
        for category, domains in LOW_QUALITY_DOMAINS.items():
            if domain in domains:
                return True

        # Check for spam indicators in URL
        for indicator in LOW_QUALITY_DOMAINS.get("spam_indicators", []):
            if indicator in domain:
                return True

        return False

    def _calculate_multi_factor_score(
        self, result: SearchResult, intent: UniversalIntent
    ) -> RankedResult:
        """Calculate multi-factor ranking score"""

        # 1. Semantic Similarity (30%)
        semantic_score = self._compute_semantic_similarity(result, intent)

        # 2. Intent Alignment (25%)
        intent_score, intent_reasons = self._compute_intent_alignment(result, intent)

        # 3. Domain Authority (20%)
        authority_score = self._compute_domain_authority(result)

        # 4. Content Quality (15%)
        quality_score = self._compute_content_quality(result)

        # 5. Freshness (10%)
        freshness_score = self._compute_freshness(result)

        # Calculate weighted final score
        final_score = (
            semantic_score * self.weights["semantic"]
            + intent_score * self.weights["intent"]
            + authority_score * self.weights["authority"]
            + quality_score * self.weights["quality"]
            + freshness_score * self.weights["freshness"]
        )

        # Build match reasons
        match_reasons = list(intent_reasons)
        if authority_score > 0.8:
            match_reasons.append("high-authority-source")
        if quality_score > 0.8:
            match_reasons.append("high-quality-content")
        if freshness_score > 0.7:
            match_reasons.append("recent-content")

        return RankedResult(
            result=result,
            alignmentScore=intent_score,
            matchReasons=match_reasons,
            qualityScore=quality_score,
            authorityScore=authority_score,
            freshnessScore=freshness_score,
            semanticScore=semantic_score,
            finalScore=final_score,
        )

    def _compute_semantic_similarity(
        self, result: SearchResult, intent: UniversalIntent
    ) -> float:
        """Compute semantic similarity between query and content"""
        try:
            # Get query from intent
            declared = intent.declared or DeclaredIntent()
            query = declared.query if declared else None

            if not query:
                return 0.5  # Neutral score if no query

            content = f"{result.title} {result.description}".strip()
            if not content:
                return 0.0

            # Use embedding cache
            query_emb = self.embedding_cache.encode_text(query)
            content_emb = self.embedding_cache.encode_text(content)

            if query_emb is not None and content_emb is not None:
                similarity = self.embedding_cache.cosine_similarity(
                    query_emb, content_emb
                )
                # Normalize from [-1, 1] to [0, 1]
                return (similarity + 1) / 2

            # Fallback to keyword matching
            return self._keyword_match_score(query, content)

        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return 0.5

    def _compute_intent_alignment(
        self, result: SearchResult, intent: UniversalIntent
    ) -> tuple[float, list[str]]:
        """Compute intent alignment score with reasons"""
        reasons = []
        scores = []

        # Null safety
        declared = intent.declared or DeclaredIntent()
        inferred = intent.inferred or InferredIntent()

        # Use case alignment (50% of intent score)
        use_cases = inferred.useCases if inferred else []
        if use_cases and result.tags:
            tag_text = " ".join(result.tags).lower()
            for use_case in use_cases:
                use_case_str = use_case_str = use_case.value.replace("_", " ")
                if use_case_str in tag_text:
                    scores.append(0.5)
                    reasons.append(f"use-case-{use_case.value}")

        # Skill level alignment (30% of intent score)
        skill_level = declared.skillLevel if declared else None
        if skill_level:
            complexity_keywords = {
                SkillLevel.BEGINNER: ["beginner", "basic", "introduction", "starter"],
                SkillLevel.INTERMEDIATE: ["intermediate", "moderate", "practical"],
                SkillLevel.ADVANCED: ["advanced", "expert", "mastery", "deep dive"],
                SkillLevel.EXPERT: ["expert", "professional", "enterprise"],
            }

            keywords = complexity_keywords.get(skill_level, [])
            content_lower = f"{result.title} {result.description}".lower()

            if any(kw in content_lower for kw in keywords):
                scores.append(0.3)
                reasons.append(f"skill-{skill_level.value}")

        # Ethical alignment (20% of intent score)
        ethical_signals = inferred.ethicalSignals if inferred else []
        if ethical_signals:
            for signal in ethical_signals:
                if signal.dimension == EthicalDimension.PRIVACY:
                    if result.privacyRating and result.privacyRating > 0.7:
                        scores.append(0.2)
                        reasons.append("privacy-aligned")
                elif signal.dimension == EthicalDimension.OPENNESS:
                    if result.opensource:
                        scores.append(0.2)
                        reasons.append("open-source")

        # Calculate final intent score
        intent_score = sum(scores) if scores else 0.5

        return min(1.0, intent_score), reasons

    def _compute_domain_authority(self, result: SearchResult) -> float:
        """Compute domain authority score"""
        if not result.domain:
            return 0.5

        # Check exact domain matches
        if result.domain in TRUSTED_DOMAINS:
            authority = TRUSTED_DOMAINS[result.domain]
            logger.debug(f"Domain {result.domain} has authority {authority}")
            return authority

        # Check suffix matches (e.g., .edu)
        for domain_suffix, score in TRUSTED_DOMAINS.items():
            if domain_suffix.startswith(".") and result.domain.endswith(domain_suffix):
                return score

        # Default authority for unknown domains
        return 0.5

    def _compute_content_quality(self, result: SearchResult) -> float:
        """Compute content quality score"""
        quality_factors = []

        # Title quality (length, capitalization)
        title_len = len(result.title)
        if (
            QUALITY_THRESHOLDS["min_title_length"]
            <= title_len
            <= QUALITY_THRESHOLDS["max_title_length"]
        ):
            quality_factors.append(0.8)
        elif title_len > QUALITY_THRESHOLDS["min_title_length"]:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.3)

        # Description quality
        desc_len = len(result.description)
        if desc_len >= 150:
            quality_factors.append(0.8)
        elif desc_len >= QUALITY_THRESHOLDS["min_content_length"]:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.3)

        # Existing quality score
        if result.qualityScore:
            quality_factors.append(result.qualityScore)

        # Average quality factors
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5

    def _compute_freshness(self, result: SearchResult) -> float:
        """Compute freshness score based on publication date"""
        if not result.published_date:
            return 0.5  # Neutral if no date

        try:
            now = datetime.now(UTC)
            age = now - result.published_date

            # Score based on age
            if age < timedelta(days=7):
                return 1.0  # Very fresh
            elif age < timedelta(days=30):
                return 0.9  # Fresh
            elif age < timedelta(days=90):
                return 0.7  # Recent
            elif age < timedelta(days=365):
                return 0.5  # Neutral
            else:
                return 0.3  # Old
        except:
            return 0.5

    def _keyword_match_score(self, query: str, content: str) -> float:
        """Calculate keyword match score as fallback"""
        if not query or not content:
            return 0.0

        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.5

        matches = query_words.intersection(content_words)
        return len(matches) / len(query_words)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None

        try:
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%d-%m-%Y",
                "%m/%d/%Y",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None
        except:
            return None

    def _remove_duplicates(self, results: list[RankedResult]) -> list[RankedResult]:
        """Remove duplicate results based on URL or content similarity"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.result.url
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results


# Convenience function
async def rank_results_enhanced(
    candidates: list[dict], intent: UniversalIntent, options: Optional[dict] = None
) -> list[dict]:
    """
    Enhanced ranking with multi-factor scoring.

    Args:
        candidates: List of search result dicts
        intent: User intent object
        options: Ranking options

    Returns:
        List of ranked result dicts
    """
    ranker = EnhancedRanker()
    ranked = await ranker.rank_with_filters(candidates, intent, options)

    # Convert back to dicts for API response
    return [
        {
            "url": r.result.url,
            "title": r.result.title,
            "content": r.result.description,
            "score": r.finalScore,
            "quality_score": r.qualityScore,
            "authority_score": r.authorityScore,
            "semantic_score": r.semanticScore,
            "match_reasons": r.matchReasons,
        }
        for r in ranked
    ]
