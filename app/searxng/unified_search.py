"""
Unified Search Service (Enhanced with Query Router)

Combines SearXNG privacy search, Go Crawler, and Intent Engine ranking
to provide privacy-focused, intent-aware search results.

Flow (Enhanced):
1. Extract intent from user query
2. Route query to optimal backends based on intent
3. Execute federated search across backends (parallel)
4. Aggregate and deduplicate results
5. Rank results based on intent alignment
6. Return privacy-enhanced, ranked results
"""

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from functools import lru_cache
from typing import Any

from app.core.schema import UniversalIntent
from app.extraction.developer_assistance import get_developer_assistance_engine
from app.extraction.extractor import IntentExtractionRequest, extract_intent
from app.models import (
    ExtractedIntent,
    RankedSearchResult,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
)
from app.ranking.url_ranker import URLRankingRequest, rank_urls
from app.searxng.client import get_searxng_client
from app.searxng.query_router import (
    SearchResult as RouterSearchResult,
)
from app.searxng.query_router import (
    get_query_router,
)
from app.searxng.result_aggregator import AggregatedResult, get_result_aggregator

logger = logging.getLogger(__name__)


class UnifiedSearchService:
    """
    Service for unified privacy search with intent ranking.

    Enhanced with Query Router for federated search across multiple backends.

    Features:
    - Privacy-first search (no tracking via SearXNG)
    - Intent extraction from queries
    - Intent-based query routing (Go Crawler, SearXNG, Custom Index)
    - Federated search execution (parallel)
    - Result aggregation and deduplication
    - Intent-aware result ranking
    - Privacy score calculation
    - Ethical alignment scoring
    """

    def __init__(self):
        self.searxng_client = get_searxng_client()
        self.query_router = get_query_router()
        self.result_aggregator = get_result_aggregator()
        logger.info("Unified Search Service initialized with Query Router")

    async def _safe_add_search_query(self, query: str):
        """Safely add search query to topic expander in background."""
        try:
            from app.searxng.topic_expander import get_topic_expander

            expander = get_topic_expander()
            await expander.add_search_query(query)
        except Exception as e:
            logger.debug(f"Query recording background task failed: {e}")

    async def search(self, request: UnifiedSearchRequest) -> UnifiedSearchResponse:
        """
        Perform unified search with intent extraction and ranking.

        Enhanced with Query Router for federated search:
        1. Extract intent (if enabled)
        2. Route query to optimal backends based on intent
        3. Execute federated search (parallel)
        4. Aggregate and deduplicate results
        5. Rank with intent alignment
        6. Apply privacy filters
        7. Record query for topic learning
        8. Cache results for better performance (NEW)

        Args:
            request: Unified search request with query and options

        Returns:
            UnifiedSearchResponse with ranked results
        """
        start_time = time.time()
        logger.info(
            f"Unified search (v2): query='{request.query}', "
            f"extract_intent={request.extract_intent}, rank_results={request.rank_results}"
        )

        # Try to get from cache first (if caching is enabled)
        cache_key = f"search:{normalize_query(request.query)}:{request.max_results}:{request.rank_results}"
        cached_response = await self._get_cached_search_response(cache_key)
        if cached_response:
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"✓ Cache hit for query: {request.query[:50]} (latency: {elapsed:.2f}ms)"
            )
            return cached_response

        # Record query for topic learning (async, non-blocking, fire-and-forget)
        asyncio.create_task(self._safe_add_search_query(request.query))

        # Step 1: Extract intent (with L1 caching - <1ms for cached queries)
        universal_intent = None
        extracted_intent = None
        intent_task = None
        intent_result = None

        if request.extract_intent:
            # L1 cache lookup first (instant for cached queries)
            intent_result = extract_intent_cached(request.query)

            if not intent_result:
                # If not in cache, start background extraction with timeout
                intent_task = asyncio.create_task(
                    asyncio.to_thread(
                        self._extract_intent_with_error_handling, request.query
                    )
                )

                # Phase 1 Optimization: Wait briefly for intent to allow optimized routing
                try:
                    # Wait up to 150ms for intent extraction (usually takes <50ms cached, <200ms uncached)
                    intent_result = await asyncio.wait_for(
                        asyncio.shield(intent_task), timeout=0.15
                    )
                except (asyncio.TimeoutError, Exception):
                    # If it takes longer, we'll continue with default routing
                    logger.debug(
                        "Intent extraction taking >150ms, proceeding with default routing"
                    )

        # Step 2: Determine Route based on intent if available
        from app.searxng.query_router import QueryRoute, SearchBackend

        if intent_result and hasattr(intent_result, "intent"):
            universal_intent = intent_result.intent
            extracted_intent = self._convert_to_extracted_intent(universal_intent)
            route = self.query_router.route(universal_intent)
            logger.info(
                f"Using optimized intent-based route: {[b.value for b in route.backends]}"
            )
        else:
            # Default fallback route
            route = QueryRoute(
                backends=[SearchBackend.GO_CRAWLER, SearchBackend.SEARXNG],
                weights={SearchBackend.GO_CRAWLER: 0.5, SearchBackend.SEARXNG: 0.5},
                parallel=True,
                max_results_per_backend=request.max_results or 20,
            )
            logger.debug("Using default hybrid routing")

        # Execute search across backends
        search_task = asyncio.create_task(
            self.query_router.execute_search(route=route, query=request.query)
        )

        # Wait for intent if it's still running (e.g., if we timed out waiting for it above)
        if request.extract_intent and not intent_result and intent_task:
            try:
                intent_result = await intent_task
                if intent_result and hasattr(intent_result, "intent"):
                    universal_intent = intent_result.intent
                    extracted_intent = self._convert_to_extracted_intent(
                        universal_intent
                    )
                    logger.info(
                        f"Intent extracted (late): goal={extracted_intent.goal}, use_cases={extracted_intent.use_cases}"
                    )
            except Exception as e:
                logger.warning(f"Late intent extraction failed: {e}")

        # Step 3: Wait for federated search results with timeout
        try:
            # Add timeout to prevent hanging on slow backends
            # IMPROVED: Stricter timeout (max 5s) for better user experience
            # Timeout scales with max_results but caps at 5 seconds (Priority 2 fix)
            search_timeout = min(5.0, 2.0 + (request.max_results or 20) * 0.15)
            raw_results = await asyncio.wait_for(search_task, timeout=search_timeout)
            logger.info(
                f"Federated search returned {len(raw_results)} raw results in {search_timeout:.1f}s"
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Federated search timed out after {search_timeout}s, cancelling..."
            )
            search_task.cancel()
            # Fallback to SearXNG only (more reliable)
            logger.warning("Falling back to SearXNG only")
            raw_results = await self._search_searxng_as_router_results(request)
        except Exception as e:
            logger.error(f"Federated search failed: {e}")
            # Fallback to SearXNG only
            logger.warning("Falling back to SearXNG only")
            raw_results = await self._search_searxng_as_router_results(request)

        # Step 4: Aggregate and deduplicate (NEW - Result Aggregator)
        aggregated_results = self.result_aggregator.aggregate(raw_results)
        logger.info(f"Aggregated to {len(aggregated_results)} unique results")

        # Convert aggregated results to ranked results
        # Use enhanced ranker if available, fallback to default
        ranked_results = await self._convert_aggregated_to_ranked_enhanced(
            aggregated_results, universal_intent, request
        )

        # Step 5: Apply privacy filters (if requested)
        if request.min_privacy_score or request.exclude_big_tech:
            logger.debug("Applying privacy filters")
            ranked_results = self._apply_privacy_filters(ranked_results, request)

        # Step 6: Limit to max_results
        max_results = request.max_results or 20
        if len(ranked_results) > max_results:
            ranked_results = ranked_results[:max_results]

        # Step 7: Add search result URLs to crawl queue (NEW - Self-improving loop)
        try:
            await self._add_urls_to_crawl_queue(raw_results)
        except Exception as e:
            logger.debug(f"URL seeding failed (non-critical): {e}")

        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000

        # Build response with enhanced metrics
        backend_distribution = self._count_backend_distribution(raw_results)
        engines_used = list({r.engine for r in raw_results if r.engine})

        response = UnifiedSearchResponse(
            query=request.query,
            results=ranked_results,
            total_results=len(ranked_results),
            processing_time_ms=processing_time_ms,
            extracted_intent=extracted_intent,
            engines_used=engines_used,
            categories_searched=request.categories or ["general"],
            ranking_applied=request.rank_results and universal_intent is not None,
            results_ranked=len(
                [r for r in ranked_results if r.ranked_score != r.original_score]
            ),
            privacy_enhanced=True,
            tracking_blocked=True,
        )

        # Add custom metrics for federated search
        response.metrics = {
            "backend_distribution": backend_distribution,
            "aggregation_ratio": len(aggregated_results) / len(raw_results)
            if raw_results
            else 0,
            "routing_strategy": str([b.value for b in route.backends]),
            "parallel_execution": route.parallel,
        }

        logger.info(
            f"✓ Unified search (v2) complete: {len(response.results)} results in {processing_time_ms:.2f}ms"
        )

        # Cache the response (L2 Redis cache, 1-hour TTL)
        cache_key = f"search:{normalize_query(request.query)}:{request.max_results}:{request.rank_results}"
        asyncio.create_task(self._cache_search_response(cache_key, response, ttl=3600))

        return response

    async def _add_urls_to_crawl_queue(self, raw_results: list) -> int:
        """
        Add search result URLs to Go crawler queue for future crawling.

        This creates a self-improving loop where search results become
        new crawl targets, expanding our indexed content over time.

        Args:
            raw_results: List of raw search results from SearXNG/Go crawler

        Returns:
            Number of URLs added to crawl queue
        """
        try:
            from app.searxng.seed_url_manager import get_seed_url_manager

            seed_manager = get_seed_url_manager()

            # Extract URLs from results
            urls = []
            for result in raw_results:
                if hasattr(result, "url") and result.url:
                    urls.append(
                        {
                            "url": result.url,
                            "title": getattr(result, "title", ""),
                            "engine": getattr(result, "engine", "unknown"),
                            "score": getattr(result, "score", 0),
                        }
                    )

            # Filter to unique URLs
            unique_urls = list({item["url"]: item for item in urls}.values())

            # Prioritize high-scoring results
            high_priority_urls = [
                item["url"] for item in unique_urls if item.get("score", 0) > 5.0
            ][:10]
            normal_priority_urls = [
                item["url"] for item in unique_urls if item.get("score", 0) <= 5.0
            ][:20]

            # Add to crawl queue
            added_high = seed_manager.add_urls_to_crawl_queue(
                high_priority_urls, priority=8, depth=1
            )
            added_normal = seed_manager.add_urls_to_crawl_queue(
                normal_priority_urls, priority=5, depth=2
            )

            total_added = added_high + added_normal

            if total_added > 0:
                logger.info(
                    f"Added {total_added} URLs from search results to crawl queue (high_priority={added_high}, normal={added_normal})"
                )

            return total_added

        except Exception as e:
            logger.warning(f"Failed to add URLs to crawl queue: {e}")
            return 0

    def _extract_intent(self, query: str) -> Any:
        """Extract intent from search query."""
        intent_request = IntentExtractionRequest(
            product="search",
            input={"text": query},
            context={
                "sessionId": f"search_{datetime.utcnow().timestamp()}",
                "userLocale": "en-US",
            },
        )
        return extract_intent(intent_request)

    def _extract_intent_with_error_handling(self, query: str) -> Any:
        """Extract intent with error handling for parallel execution."""
        try:
            return self._extract_intent(query)
        except Exception as e:
            logger.warning(f"Intent extraction error in thread: {e}")
            raise

    def _convert_to_extracted_intent(
        self, universal_intent: UniversalIntent
    ) -> ExtractedIntent:
        """Convert UniversalIntent to ExtractedIntent for API response."""
        # Defensive: handle None values in inferred intent
        inferred = universal_intent.inferred if universal_intent.inferred else None
        declared = universal_intent.declared if universal_intent.declared else None

        # Handle use_cases - might be None or empty list
        use_cases_list = getattr(inferred, "useCases", []) if inferred else []
        if use_cases_list is None:
            use_cases_list = []

        # Handle constraints - might be None or empty list
        constraints_list = getattr(declared, "constraints", []) if declared else []
        if constraints_list is None:
            constraints_list = []

        # Handle programming context
        programming_context_dict = None
        research_plan_dict = None

        if (
            inferred
            and hasattr(inferred, "programmingContext")
            and inferred.programmingContext
        ):
            ctx = inferred.programmingContext
            programming_context_dict = {
                "language": ctx.language.value
                if hasattr(ctx.language, "value")
                else str(ctx.language),
                "errorType": ctx.errorType.value
                if hasattr(ctx.errorType, "value")
                else str(ctx.errorType),
                "errorCode": ctx.errorCode,
                "errorMessage": ctx.errorMessage,
                "framework": ctx.framework,
                "confidence": ctx.confidence,
                "hasStackTrace": ctx.hasStackTrace,
            }

            # Generate research plan using developer assistance engine
            try:
                engine = get_developer_assistance_engine()
                assistance = engine.generate_assistance_response(universal_intent)

                # Get optimized queries from programming extractor if possible
                from app.extraction.programming_error_detector import (
                    get_programming_intent_extractor,
                )

                prog_extractor = get_programming_intent_extractor()
                optimized_queries = prog_extractor.generate_optimized_queries(ctx)

                if assistance.research_plan:
                    rp = assistance.research_plan
                    # Merge optimized queries
                    final_queries = list(
                        set(optimized_queries + rp.optimized_search_queries)
                    )

                    research_plan_dict = {
                        "investigation_steps": rp.investigation_steps,
                        "optimized_search_queries": final_queries[:5],
                        "key_concepts": rp.key_concepts,
                    }
                elif optimized_queries:
                    research_plan_dict = {
                        "investigation_steps": [
                            "Search for the error message",
                            "Analyze community solutions",
                        ],
                        "optimized_search_queries": optimized_queries,
                        "key_concepts": [ctx.language.value]
                        if hasattr(ctx.language, "value")
                        else [str(ctx.language)],
                    }
            except Exception as e:
                logger.warning(f"Failed to generate research plan: {e}")

        return ExtractedIntent(
            goal=(declared.goal.value if declared and declared.goal else "unknown"),
            constraints=[
                {
                    "type": c.type.value if hasattr(c.type, "value") else str(c.type),
                    "dimension": c.dimension,
                    "value": c.value,
                }
                for c in constraints_list
            ],
            use_cases=[
                uc.value if hasattr(uc, "value") else str(uc) for uc in use_cases_list
            ],
            result_type=(
                inferred.resultType.value
                if inferred and inferred.resultType
                else "unknown"
            ),
            complexity=(
                inferred.complexity.value
                if inferred and inferred.complexity
                else "moderate"
            ),
            confidence=0.8,  # Default confidence
            programming_context=programming_context_dict,
            research_plan=research_plan_dict,
        )

    def _apply_privacy_filters(
        self, results: list[RankedSearchResult], request: UnifiedSearchRequest
    ) -> list[RankedSearchResult]:
        """Apply privacy-based filtering to results."""
        filtered = []

        big_tech_domains = [
            "google.com",
            "facebook.com",
            "amazon.com",
            "microsoft.com",
            "apple.com",
            "twitter.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "tiktok.com",
        ]

        for result in results:
            # Filter by privacy score
            if request.min_privacy_score and result.privacy_score:
                if result.privacy_score < request.min_privacy_score:
                    continue

            # Filter big tech
            if request.exclude_big_tech:
                domain = (
                    result.url.split("/")[2].lower()
                    if "/" in result.url
                    else result.url.lower()
                )
                if any(bt in domain for bt in big_tech_domains):
                    continue

            filtered.append(result)

        # Re-number ranks
        for idx, result in enumerate(filtered):
            result.rank = idx + 1

        return filtered

    # NEW: Helper methods for Query Router integration

    async def _search_searxng_as_router_results(
        self, request: UnifiedSearchRequest
    ) -> list[RouterSearchResult]:
        """Search SearXNG and return as RouterSearchResult format (fallback)"""
        from app.searxng.query_router import SearchBackend

        try:
            response = await self.searxng_client.search(
                query=request.query,
                categories=request.categories,
                engines=request.engines,
                language=request.language,
                safe_search=request.safe_search,
                time_range=request.time_range,
            )

            if not response or not response.results:
                return []

            return [
                RouterSearchResult(
                    source=SearchBackend.SEARXNG,
                    url=r.url,
                    title=r.title,
                    content=r.content,
                    score=r.score if r.score else 0.5,
                    engine=r.engine,
                    metadata={
                        "category": r.category,
                        "published_date": r.published_date,
                    },
                )
                for r in response.results
            ]
        except Exception as e:
            logger.error(f"SearXNG fallback search failed: {e}")
            return []

    async def _convert_aggregated_to_ranked(
        self,
        aggregated: list[AggregatedResult],
        universal_intent: UniversalIntent | None,
        request: UnifiedSearchRequest,
    ) -> list[RankedSearchResult]:
        """Convert AggregatedResult to RankedSearchResult"""
        ranked_results = []

        for idx, agg_result in enumerate(aggregated):
            # Create ranked result
            ranked_result = RankedSearchResult(
                url=agg_result.url,
                title=agg_result.title,
                content=agg_result.content,
                engine=agg_result.metadata.get("source_details", {})
                .keys()
                .__iter__()
                .__next__()
                if agg_result.metadata.get("source_details")
                else "aggregated",
                original_score=agg_result.best_score,
                ranked_score=agg_result.best_score,  # Will be updated by ranker if enabled
                rank=idx + 1,
                category=agg_result.metadata.get("category", "general"),
                thumbnail=None,
                published_date=agg_result.metadata.get("published_date"),
                price=agg_result.metadata.get("price"),
                currency=agg_result.metadata.get("currency"),
                intent_goal=(
                    universal_intent.declared.goal.value
                    if universal_intent
                    and universal_intent.declared
                    and universal_intent.declared.goal
                    else None
                ),
                match_reasons=self._generate_match_reasons_from_aggregated(
                    agg_result, universal_intent
                ),
                privacy_score=None,  # Will be calculated if enabled
                ethical_alignment=None,
            )
            ranked_results.append(ranked_result)

        # Step 5: Enrich with dynamic data if needed (PURCHASE intent)
        if (
            universal_intent
            and universal_intent.declared
            and universal_intent.declared.goal
        ):
            goal_value = (
                universal_intent.declared.goal.value
                if hasattr(universal_intent.declared.goal, "value")
                else str(universal_intent.declared.goal)
            )
            if goal_value == "purchase":
                await self._enrich_with_dynamic_data(ranked_results)

        # Apply intent-based ranking if enabled (Optimized with Top-K)
        if request.rank_results and universal_intent and ranked_results:
            try:
                # Top-K Optimization: Only rank the top 40 candidates to improve P99 latency
                candidates_to_rank = ranked_results[:40]
                urls_to_rank = [r.url for r in candidates_to_rank]
                titles_to_rank = [r.title for r in candidates_to_rank]
                contents_to_rank = [r.content for r in candidates_to_rank]

                ranking_request = URLRankingRequest(
                    query=request.query,
                    urls=urls_to_rank,
                    titles=titles_to_rank,
                    contents=contents_to_rank,
                    intent=universal_intent,
                    options={
                        "weights": request.weights,
                        "min_privacy_score": request.min_privacy_score,
                        "exclude_big_tech": request.exclude_big_tech,
                    },
                )

                ranking_response = await rank_urls(ranking_request)

                if ranking_response:
                    # Update scores from ranking response
                    score_map = {
                        r.url: r.final_score for r in ranking_response.ranked_urls
                    }
                    for ranked_result in candidates_to_rank:
                        if ranked_result.url in score_map:
                            ranked_result.ranked_score = score_map[ranked_result.url]
                        else:
                            # Keep original score for those not ranked (though should not happen)
                            pass

                    # Keep the rest with their original scores but lower than ranked ones
                    # or just re-sort the whole list

                    # Re-sort by ranked score
                    ranked_results.sort(key=lambda r: r.ranked_score, reverse=True)

                    # Re-number ranks
                    for idx, result in enumerate(ranked_results):
                        result.rank = idx + 1

            except Exception as e:
                logger.warning(f"Intent ranking failed: {e}")
                # Continue with original scores

        return ranked_results

    def _generate_match_reasons_from_aggregated(
        self, agg_result: AggregatedResult, universal_intent: UniversalIntent | None
    ) -> list[str]:
        """Generate match reasons from aggregated result"""
        reasons = []

        if not universal_intent:
            return reasons

        declared = universal_intent.declared if universal_intent.declared else None
        inferred = universal_intent.inferred if universal_intent.inferred else None

        # Intent goal match
        if declared and declared.goal:
            reasons.append(f"Matches {declared.goal.value} intent")

        # Multiple sources (indicates consensus)
        if len(agg_result.sources) > 1:
            reasons.append(f"Found in {len(agg_result.sources)} sources")

        # Use case match
        if inferred and inferred.useCases:
            reasons.append(f"Suitable for {inferred.useCases[0].value}")

        return reasons[:3]

    async def _convert_aggregated_to_ranked_enhanced(
        self,
        aggregated_results: list[AggregatedResult],
        universal_intent: UniversalIntent | None,
        request: UnifiedSearchRequest,
    ) -> list[RankedSearchResult]:
        """
        Convert aggregated results to ranked results using enhanced multi-factor ranking.

        This is the enhanced version with:
        1. Multi-factor scoring (semantic + authority + freshness + quality)
        2. Content filtering (trusted sources, low-quality filtering)
        3. Intent fallback for null goals
        4. Better null safety

        Args:
            aggregated_results: Aggregated search results
            universal_intent: User intent (may be None)
            request: Original search request

        Returns:
            List of ranked search results
        """
        from app.ranking.enhanced_ranker import EnhancedRanker

        # Apply intent fallback if needed
        if (
            universal_intent is None
            or not universal_intent.declared
            or not universal_intent.declared.goal
        ):
            from app.extraction.intent_fallback import enhance_intent_with_fallback

            universal_intent = enhance_intent_with_fallback(
                universal_intent, request.query
            )
            logger.info(
                f"Applied intent fallback: goal={universal_intent.declared.goal.value if universal_intent.declared.goal else 'unknown'}"
            )

        # Convert aggregated results to dict format for enhanced ranker
        candidates = []
        for agg in aggregated_results:
            candidate = {
                "id": hashlib.md5(agg.url.encode()).hexdigest(),
                "title": agg.title,
                "content": agg.content,
                "url": agg.url,
                "platform": agg.source.value if agg.source else "unknown",
                "qualityScore": agg.best_score,
                "tags": agg.metadata.get("tags", []),
                "publishedDate": agg.metadata.get("published_date"),
            }
            candidates.append(candidate)

        # Use enhanced ranker
        ranker = EnhancedRanker(
            config={
                "weights": request.weights
                if hasattr(request, "weights") and request.weights
                else None,
                "filtering": {
                    "enable_domain_filter": True,
                    "enable_quality_filter": True,
                    "min_quality_threshold": 0.3,
                    "remove_duplicates": True,
                },
            }
        )

        ranked = await ranker.rank_with_filters(
            candidates,
            universal_intent,
            request.options if hasattr(request, "options") else None,
        )

        # Convert back to RankedSearchResult format
        ranked_results = []
        for idx, r in enumerate(ranked):
            ranked_result = RankedSearchResult(
                url=r.result.url,
                title=r.result.title,
                content=r.result.description,
                url_final=r.result.url,
                engine=r.result.platform or "unknown",
                score=r.finalScore,
                original_score=r.result.qualityScore,
                ranked_score=r.finalScore,
                rank=idx + 1,
                category="general",
                thumbnail=None,
                published_date=r.result.published_date,
                price=r.result.price,
                currency=None,
                intent_goal=universal_intent.declared.goal.value
                if universal_intent.declared and universal_intent.declared.goal
                else None,
                match_reasons=r.matchReasons,
                privacy_score=None,
                ethical_alignment=None,
            )
            ranked_results.append(ranked_result)

        logger.info(
            f"Enhanced ranking: {len(ranked_results)} results with multi-factor scoring"
        )
        return ranked_results

    def _count_backend_distribution(
        self, results: list[RouterSearchResult]
    ) -> dict[str, int]:
        """Count results per backend"""
        distribution: dict[str, int] = {}
        for result in results:
            source = result.source.value
            distribution[source] = distribution.get(source, 0) + 1
        return distribution

    async def _enrich_with_dynamic_data(self, ranked_results: list[RankedSearchResult]):
        """
        Enrich search results with dynamic data (price, etc.) from Redis.
        If data is missing, enqueue a background task to scrape it.

        Optimization: Uses persistent Redis cache and ARQ pool.
        """
        try:
            from app.config.redis_cache import cache
            from app.config.arq_pool import get_arq_pool

            # Get shared ARQ pool
            arq_pool = await get_arq_pool()

            # Dynamic domains that definitely need Playwright
            dynamic_domains = ["amazon.", "flipkart.", "ebay.", "walmart.", "bestbuy."]

            for result in ranked_results[:10]:  # Only enrich top 10 for performance
                url = result.url
                domain = url.split("/")[2].lower() if "/" in url else url.lower()

                # 1. Check if we already have dynamic data in Redis using persistent cache
                key = f"dynamic_scrape:{url}"
                cached_data = await cache.get(key)

                if cached_data:
                    result.price = cached_data.get("price")
                    result.currency = cached_data.get("currency")

                    if "match_reasons" in cached_data:
                        result.match_reasons.extend(cached_data["match_reasons"])

                    logger.debug(f"Applied cached dynamic data for {url[:30]}...")
                elif any(d in domain for d in dynamic_domains):
                    # 2. Enqueue background scrape if missing and dynamic domain
                    await arq_pool.enqueue_job("scrape_dynamic_url", url)
                    logger.debug(f"Enqueued background scrape for {url[:30]}...")

        except Exception as e:
            logger.warning(f"Dynamic enrichment failed: {e}")


# Singleton instance
_unified_search_service: UnifiedSearchService | None = None


def get_unified_search_service() -> UnifiedSearchService:
    """Get or create unified search service singleton."""
    global _unified_search_service

    if _unified_search_service is None:
        _unified_search_service = UnifiedSearchService()

    return _unified_search_service


# Module-level cache for intent extraction results
# L1 Cache: In-memory LRU cache for ultra-fast access (<1ms)
# Cache up to 2000 recent intent extractions (doubled for better hit rate)
@lru_cache(maxsize=2000)
def _cached_extract_intent(query_hash: str, query: str, query_length: int):
    """
    Cached version of intent extraction.

    Args:
        query_hash: MD5 hash of normalized query (for cache key)
        query: Original query string
        query_length: Length of query (for better cache discrimination)

    Returns:
        Intent extraction result or None if failed

    Performance:
        - Cache hit: <1ms (memory access only)
        - Cache miss: 30-50ms (ML inference)
        - Hit rate target: >80% for common queries
    """
    try:
        intent_request = IntentExtractionRequest(
            product="search",
            input={"text": query},
            context={
                "sessionId": f"search_cached_{datetime.utcnow().timestamp()}",
                "userLocale": "en-US",
            },
        )
        return extract_intent(intent_request)
    except Exception as e:
        logger.warning(f"Cached intent extraction failed: {e}")
        return None


def normalize_query(query: str) -> str:
    """
    Normalize query for consistent caching and better hit rates.

    Normalization steps:
    1. Lowercase
    2. Strip whitespace
    3. Remove extra spaces
    4. Remove punctuation (except essential)
    5. Sort common query patterns

    Examples:
        "Best laptop for programming" -> "best laptop programming"
        "How to learn Python?" -> "learn python"
        "Python vs Java comparison" -> "python java comparison"
    """
    import re

    # Lowercase and strip
    normalized = query.lower().strip()

    # Remove extra whitespace
    normalized = " ".join(normalized.split())

    # Remove common stop words that don't affect intent
    stop_words = {
        "how",
        "to",
        "what",
        "is",
        "are",
        "the",
        "a",
        "an",
        "for",
        "in",
        "on",
        "at",
        "with",
        "by",
    }
    words = [w for w in normalized.split() if w not in stop_words]

    # Remove punctuation except hyphens and underscores
    normalized = " ".join(words)
    normalized = re.sub(r"[^\w\s\-_]", "", normalized)

    # Remove double spaces
    normalized = " ".join(normalized.split())

    return normalized


def extract_intent_cached(query: str) -> Any:
    """
    Extract intent with multi-level caching for optimal performance.

    Caching Strategy:
    1. L1 Cache: In-memory LRU (2000 entries, <1ms access)
    2. L2 Cache: Redis (optional, for distributed caching)

    Performance Targets:
    - L1 hit: <1ms
    - L2 hit: 5-10ms
    - Miss: 30-50ms (ML inference)
    - Overall P95: <10ms with 80%+ hit rate

    Args:
        query: Search query string

    Returns:
        Intent extraction result or None
    """
    # Normalize query for consistent caching
    normalized_query = normalize_query(query)

    # Generate cache key components
    query_hash = hashlib.md5(normalized_query.encode()).hexdigest()
    query_length = len(normalized_query)

    # L1 Cache lookup (ultra-fast)
    result = _cached_extract_intent(query_hash, normalized_query, query_length)

    if result:
        logger.debug(
            f"Intent cache hit for: '{query[:50]}' (normalized: '{normalized_query[:50]}')"
        )

    return result


# ============================================================================
# Search Result Caching (Redis-backed)
# ============================================================================


async def _get_cached_search_response(
    self, cache_key: str
) -> UnifiedSearchResponse | None:
    """
    Get cached search response from Redis using global cache.

    Args:
        cache_key: Unique cache key for the search query

    Returns:
        Cached UnifiedSearchResponse or None
    """
    try:
        from app.config.redis_cache import cache

        cached_data = await cache.get(cache_key)

        if cached_data:
            # Convert dict back to UnifiedSearchResponse
            return UnifiedSearchResponse(**cached_data)

        return None
    except Exception as e:
        logger.debug(f"Cache retrieval failed: {e}")
        return None


async def _cache_search_response(
    self, cache_key: str, response: UnifiedSearchResponse, ttl: int = 3600
):
    """
    Cache search response in Redis using global cache.

    Args:
        cache_key: Unique cache key for the search query
        response: UnifiedSearchResponse to cache
        ttl: Cache TTL in seconds (default: 1 hour)
    """
    try:
        from app.config.redis_cache import cache

        # Convert response to dict (Pydantic v2 compatible)
        response_dict = response.model_dump()

        # Store in Redis with TTL (using background task for performance)
        await cache.set(cache_key, response_dict, ttl=ttl, background=True)

        logger.debug(f"Cached search response for: {response.query[:50]} (TTL={ttl}s)")
    except Exception as e:
        logger.debug(f"Cache storage failed: {e}")


# Add the methods to the class
UnifiedSearchService._get_cached_search_response = _get_cached_search_response
UnifiedSearchService._cache_search_response = _cache_search_response
