"""
Intent Engine - Main API Service

This module implements the FastAPI service with all required endpoints for the Intent Engine.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from sentence_transformers import CrossEncoder
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.ads.matcher import match_ads
from app.analytics.realtime import handle_analytics_websocket
from app.audit.audit_trail import AuditEventType, get_audit_trail_manager
from app.core.schema import UniversalIntent
from app.database import Ad as DbAd
from app.database import AdGroup as DbAdGroup
from app.database import AdMetric as DbAdMetric
from app.database import Advertiser as DbAdvertiser
from app.database import Base, db_manager, engine
from app.database import Campaign as DbCampaign
from app.database import ClickTracking as DbClickTracking
from app.database import ConversionTracking as DbConversionTracking
from app.database import CreativeAsset as DbCreativeAsset
from app.database import FraudDetection as DbFraudDetection
from app.extraction.extractor import extract_intent
from app.models import (
    ABTestCreate,
    ABTestResponse,
    ABTestResultsResponse,
    ABTestVariantCreate,
    ABTestVariantResponse,
    Ad,
    AdCreate,
    AdGroup,
    AdGroupCreate,
    AdGroupUpdate,
    AdMatchingRequest,
    AdMatchingResponse,
    AdMatchingWithCampaignRequest,
    AdUpdate,
    Advertiser,
    AdvertiserCreate,
    AttributionResultResponse,
    AuditEvent,
    AuditStats,
    Campaign,
    CampaignCreate,
    CampaignPerformanceReport,
    CampaignROIResponse,
    CampaignUpdate,
    ClickTracking,
    ClickTrackingCreate,
    ConsentRecord,
    ConsentSummary,
    ConversionTracking,
    ConversionTrackingCreate,
    CreativeAsset,
    CreativeAssetCreate,
    CreativeAssetUpdate,
    DataRetentionPolicy,
    FraudAnalysisResponse,
    FraudDetection,
    FraudDetectionCreate,
    FraudScanSummary,
    HealthCheckResponse,
    IntentExtractionRequest,
    PrivacyComplianceReport,
    RankingRequest,
    RankingResponse,
    ServiceRecommendationRequest,
    ServiceRecommendationResponse,
    StatusResponse,
    TrendAnalysisResponse,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    URLRankedResult,
    URLRankingAPIRequest,
    URLRankingAPIResponse,
)
from app.privacy.consent_manager import ConsentType, get_consent_manager
from app.privacy.enhanced_privacy import DataRetentionPeriod, get_enhanced_privacy_controls
from app.privacy_core import (
    anonymize_intent_data,
    is_intent_expired,
    validate_advertiser_constraints,
)
from app.ranking.optimized_ranker import rank_results
from app.searxng.unified_search import get_unified_search_service
from app.services.recommender import recommend_services

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Define v1 router
v1_router = APIRouter(prefix="/v1")

# Initialize metrics
http_requests_total = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
request_latency = Histogram("request_latency_seconds", "Request latency", ["method", "endpoint"])
fairness_violations = Counter("fairness_violations_total", "Total fairness constraint violations detected")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    # Startup: Initialize DB, load models, etc.
    logger.info("Starting Intent Engine API...")
    Base.metadata.create_all(bind=engine)
    
    # Mark models as loaded (in a real app, this would happen after loading)
    from app.config.health_checks import health_checker
    health_checker.mark_models_loaded()
    
    yield
    # Shutdown: Clean up resources
    logger.info("Shutting down Intent Engine API...")

app = FastAPI(
    title="Intent Engine API",
    description="Privacy-first, intent-driven search and advertising platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MAX_PAGINATION_LIMIT = 1000  # Maximum number of items that can be returned
DEFAULT_PAGINATION_LIMIT = 100  # Default limit for pagination


# Create the database dependency
def get_db():
    db = next(db_manager.get_db())
    try:
        yield db
    finally:
        db.close()


# Helper function to convert dict to UniversalIntent
def convert_dict_to_universal_intent(intent_dict: dict[str, Any]) -> UniversalIntent:
    """
    Convert intent dictionary to UniversalIntent dataclass.
    Reusable helper for /rank-results and /match-ads endpoints.
    """
    from app.core.schema import (
        Complexity,
        Constraint,
        ConstraintType,
        DeclaredIntent,
        EthicalDimension,
        EthicalSignal,
        Frequency,
        InferredIntent,
        IntentGoal,
        Recency,
        ResultType,
        SessionFeedback,
        SkillLevel,
        TemporalHorizon,
        TemporalIntent,
        UniversalIntent,
        Urgency,
        UseCase,
    )

    # Convert constraints
    constraints = []
    for c in intent_dict.get("declared", {}).get("constraints", []):
        if isinstance(c, dict):
            constraint_type = c.get("type")
            if isinstance(constraint_type, str) and constraint_type in [ct.value for ct in ConstraintType]:
                constraint_type = ConstraintType(constraint_type)
            constraints.append(
                Constraint(
                    type=constraint_type,
                    dimension=c.get("dimension", "") or "",
                    value=c.get("value", "") or "",
                    hardFilter=c.get("hardFilter", True),
                )
            )

    # Convert declared intent
    declared_dict = intent_dict.get("declared", {}) or {}
    goal = declared_dict.get("goal")
    # Convert goal if it's a string or has a .value attribute
    if goal is not None and not isinstance(goal, IntentGoal):
        goal_value = goal.value if hasattr(goal, "value") else str(goal)
        if goal_value in [g.value for g in IntentGoal]:
            goal = IntentGoal(goal_value)
        else:
            # Try to find a matching goal by case-insensitive comparison
            goal_lower = goal_value.lower().replace("_", "").replace("-", "")
            for g in IntentGoal:
                g_normalized = g.value.lower().replace("_", "").replace("-", "")
                if goal_lower == g_normalized:
                    goal = g
                    break
    urgency = declared_dict.get("urgency", "FLEXIBLE")
    if isinstance(urgency, str) and urgency in [u.value for u in Urgency]:
        urgency = Urgency(urgency)
    skill_level = declared_dict.get("skillLevel", "INTERMEDIATE")
    if isinstance(skill_level, str) and skill_level in [s.value for s in SkillLevel]:
        skill_level = SkillLevel(skill_level)

    declared = DeclaredIntent(
        query=declared_dict.get("query"),
        goal=goal,
        constraints=constraints,
        negativePreferences=declared_dict.get("negativePreferences", []) or [],
        urgency=urgency if isinstance(urgency, Urgency) else Urgency.FLEXIBLE,
        budget=declared_dict.get("budget"),
        skillLevel=(skill_level if isinstance(skill_level, SkillLevel) else SkillLevel.INTERMEDIATE),
    )

    # Convert inferred intent
    inferred_dict = intent_dict.get("inferred", {}) or {}
    use_cases = []
    for uc in inferred_dict.get("useCases", []) or []:
        # Handle both string and enum values
        if isinstance(uc, UseCase):
            use_cases.append(uc)
        elif hasattr(uc, "value"):
            uc_value = uc.value
            if uc_value in [u.value for u in UseCase]:
                use_cases.append(UseCase(uc_value))
        elif isinstance(uc, str):
            # Direct string match
            if uc in [u.value for u in UseCase]:
                use_cases.append(UseCase(uc))
            else:
                # Try to find a matching use case by case-insensitive comparison
                uc_lower = uc.lower().replace("_", "").replace("-", "")
                for u in UseCase:
                    u_normalized = u.value.lower().replace("_", "").replace("-", "")
                    if uc_lower == u_normalized:
                        use_cases.append(u)
                        break

    result_type = inferred_dict.get("resultType")
    if isinstance(result_type, str) and result_type in [r.value for r in ResultType]:
        result_type = ResultType(result_type)

    complexity = inferred_dict.get("complexity", "MODERATE")
    if isinstance(complexity, str) and complexity in [c.value for c in Complexity]:
        complexity = Complexity(complexity)

    ethical_signals = []
    for s in inferred_dict.get("ethicalSignals", []) or []:
        dimension = s.get("dimension")
        if isinstance(dimension, str) and dimension in [d.value for d in EthicalDimension]:
            dimension = EthicalDimension(dimension)
        ethical_signals.append(
            EthicalSignal(
                dimension=dimension,
                score=s.get("score", 0.0),
                evidence=s.get("evidence", ""),
            )
        )

    temporal_dict = inferred_dict.get("temporalIntent", {}) or {}
    horizon = temporal_dict.get("horizon")
    if isinstance(horizon, str) and horizon in [h.value for h in TemporalHorizon]:
        horizon = TemporalHorizon(horizon)
    frequency = temporal_dict.get("frequency")
    if isinstance(frequency, str) and frequency in [f.value for f in Frequency]:
        frequency = Frequency(frequency)
    recency = temporal_dict.get("recency")
    if isinstance(recency, str) and recency in [r.value for r in Recency]:
        recency = Recency(recency)

    temporal = TemporalIntent(
        horizon=horizon,
        frequency=frequency,
        recency=recency,
        specificDate=temporal_dict.get("specificDate"),
    )

    inferred = InferredIntent(
        useCases=use_cases,
        resultType=result_type,
        ethicalSignals=ethical_signals,
        complexity=complexity,
        temporalIntent=temporal,
    )

    feedback_dict = intent_dict.get("feedback", {}) or {}
    feedback = SessionFeedback(
        relevanceScore=feedback_dict.get("relevanceScore"),
        satisfied=feedback_dict.get("satisfied"),
        corrections=feedback_dict.get("corrections", []) or [],
    )

    return UniversalIntent(
        id=intent_dict.get("id", ""),
        timestamp=intent_dict.get("timestamp", datetime.now(UTC).isoformat()),
        declared=declared,
        inferred=inferred,
        feedback=feedback,
    )


# Basic Endpoints
@app.get("/", response_model=dict[str, Any])
async def root():
    """Root endpoint for API discovery."""
    return {
        "status": "healthy",
        "message": "Welcome to Intent Engine API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }


@app.get("/health", response_model=dict[str, Any])
async def health_check():
    """Authoritative health check endpoint."""
    from app.config.health_checks import health_checker
    
    system_health = await health_checker.check_all()
    return system_health.to_dict()


@app.get("/health/ready")
async def readiness_probe():
    """Kubernetes-style readiness probe."""
    from app.config.health_checks import health_checker
    from fastapi.responses import JSONResponse

    is_ready = await health_checker.check_readiness()

    if is_ready:
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "timestamp": datetime.now(UTC).isoformat()},
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": "Models not loaded or critical services unavailable",
            },
        )


@app.get("/health/live")
async def liveness_probe():
    """Kubernetes-style liveness probe."""
    from app.config.health_checks import health_checker
    from fastapi.responses import JSONResponse

    is_alive = await health_checker.check_liveness()

    if is_alive:
        return JSONResponse(
            status_code=200,
            content={"status": "alive", "timestamp": datetime.now(UTC).isoformat()},
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


# Core Intent Engine Endpoints
@app.post("/extract-intent", response_model=UniversalIntent)
@limiter.limit("10/minute")
async def api_extract_intent(request: Request, extraction_request: IntentExtractionRequest, response: Response):
    """
    Extract structured intent from a natural language query.
    """
    try:
        result = extract_intent(extraction_request)
        # Return the intent from the response
        return result.intent
    except Exception as e:
        logger.error(f"Intent extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rank-results", response_model=RankingResponse)
async def api_rank_results(request: RankingRequest):
    """
    Rank a list of candidates based on an extracted intent.
    """
    try:
        # Convert dict to UniversalIntent if necessary
        intent = request.intent
        if isinstance(intent, dict):
            intent = convert_dict_to_universal_intent(intent)

        ranked_results = rank_results(intent, request.candidates)
        return RankingResponse(results=ranked_results)
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend-services", response_model=ServiceRecommendationResponse)
async def api_recommend_services(request: ServiceRecommendationRequest):
    """
    Recommend internal services based on an extracted intent.
    """
    try:
        intent = request.intent
        if isinstance(intent, dict):
            intent = convert_dict_to_universal_intent(intent)

        recommendations = recommend_services(intent)
        return ServiceRecommendationResponse(recommendations=recommendations)
    except Exception as e:
        logger.error(f"Service recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search Endpoints
@app.post("/search", response_model=UnifiedSearchResponse)
async def api_unified_search(request: UnifiedSearchRequest):
    """
    Privacy-first unified search across Go indexer, SearXNG, and Vector DB.
    """
    try:
        search_service = get_unified_search_service()
        results = await search_service.search(request.query, limit=request.limit)
        return results
    except Exception as e:
        logger.error(f"Unified search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Ad Matching Endpoints
@app.post("/match-ads", response_model=AdMatchingResponse)
async def api_match_ads(request: AdMatchingRequest):
    """
    Match eligible ads based on an extracted intent.
    """
    try:
        intent = request.intent
        if isinstance(intent, dict):
            intent = convert_dict_to_universal_intent(intent)

        matched_ads = match_ads(intent, request.adInventory)
        return AdMatchingResponse(matched_ads=matched_ads)
    except Exception as e:
        logger.error(f"Ad matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/advanced-ad-matching", response_model=AdMatchingResponse)
async def advanced_ad_matching(
    request: AdMatchingWithCampaignRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Authoritative ad matching with campaign retrieval and privacy validation.
    """
    try:
        # 1. Anonymize intent for ad delivery
        intent = request.intent
        if isinstance(intent, dict):
            intent = convert_dict_to_universal_intent(intent)

        anonymized_intent = anonymize_intent_data(intent)

        # 2. Get eligible ads from database
        query = db.query(DbAd).join(DbCampaign).join(DbAdvertiser)

        # Filter by campaign if specified
        if request.campaign_id:
            query = query.filter(DbAd.campaign_id == request.campaign_id)

        # Apply basic budget constraints from DB if possible
        if intent.declared.budget:
            try:
                query = query.filter(DbCampaign.budget_limit >= intent.declared.budget)
            except Exception as e:
                logger.error(f"Budget constraint query failed: {str(e)}")
                pass

        # Get eligible ads from active campaigns
        db_ads = query.filter(
            DbCampaign.status == "active",
            DbAd.status == "active",
            DbAd.approval_status == "approved",
        ).all()

        from app.ads.matcher import AdMetadata

        ad_inventory = []
        for db_ad in db_ads:
            ad_metadata = AdMetadata(
                id=str(db_ad.id),
                title=db_ad.title,
                description=db_ad.description,
                targetingConstraints=db_ad.targeting_constraints or {},
                forbiddenDimensions=[],
                qualityScore=db_ad.quality_score,
                ethicalTags=db_ad.ethical_tags or [],
                advertiser=f"advertiser_{db_ad.advertiser_id}",
                creative_format=db_ad.creative_format,
            )

            compliance_report = validate_advertiser_constraints(ad_metadata)
            if not compliance_report["is_compliant"]:
                logger.warning(f"Ad {db_ad.id} has compliance violations: {compliance_report['violations']}")
                fairness_violations.inc(len(compliance_report["violations"]))

            ad_inventory.append(ad_metadata)

        # Match ads
        response = match_ads(anonymized_intent, ad_inventory)

        # Log metrics in background
        background_tasks.add_task(log_ad_metrics, anonymized_intent, response.matchedAds)

        return response

    except Exception as e:
        logger.error(f"Advanced ad matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def log_ad_metrics(intent: UniversalIntent, matched_ads: list[Any]):
    """Background task to log ad metrics."""
    db = next(db_manager.get_db())
    try:
        for matched_ad in matched_ads:
            metric = DbAdMetric(
                ad_id=int(matched_ad.ad.id) if matched_ad.ad.id.isdigit() else 0,
                date=datetime.now(UTC).date(),
                intent_goal=intent.declared.goal.value if intent.declared.goal else None,
                intent_use_case=intent.inferred.useCases[0].value if intent.inferred.useCases else None,
                impression_count=1,
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            db.add(metric)
        db.commit()
    except Exception as e:
        logger.error(f"Error logging ad metrics: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/metrics")
def get_metrics():
    """Endpoint to expose Prometheus metrics."""
    return Response(generate_latest(), media_type="text/plain")


# Analytics WebSocket
@app.websocket("/ws/analytics")
async def websocket_analytics(websocket: WebSocket):
    """WebSocket endpoint for real-time analytics."""
    db = next(db_manager.get_db())
    try:
        await handle_analytics_websocket(websocket, db)
    except Exception as e:
        logger.error(f"WebSocket analytics error: {e}")
    finally:
        db.close()


# Application Status
@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get service status."""
    return StatusResponse(
        service="Intent Engine API",
        version="1.0.0",
        uptime="N/A",
        status="running",
    )


# URL Ranking Endpoints
@app.post("/rank-urls", response_model=URLRankingAPIResponse)
async def api_rank_urls(request: URLRankingAPIRequest):
    """
    Rank a list of URLs based on privacy and content.
    """
    try:
        from app.ranking.optimized_url_ranker import rank_urls, URLRankingRequest
        ranking_request = URLRankingRequest(
            query=request.query,
            urls=request.urls,
            intent=request.intent,
            options=request.options,
        )
        ranking_response = await rank_urls(ranking_request)
        
        # Convert URLRankingResponse to URLRankingAPIResponse
        ranked_results = [
            URLRankedResult(
                url=result.url,
                title=result.title,
                description=result.description,
                domain=result.domain,
                privacy_score=result.privacy_score,
                tracker_count=result.tracker_count,
                encryption_enabled=result.encryption_enabled,
                content_type=result.content_type,
                is_open_source=result.is_open_source,
                is_non_profit=result.is_non_profit,
                relevance_score=result.relevance_score,
                final_score=result.final_score,
            )
            for result in ranking_response.ranked_urls
        ]
        return URLRankingAPIResponse(
            query=ranking_response.query,
            ranked_urls=ranked_results,
            processing_time_ms=ranking_response.processing_time_ms,
            total_urls=ranking_response.total_urls,
            filtered_count=ranking_response.filtered_count,
        )
    except Exception as e:
        logger.error(f"URL ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Advertising Management Endpoints
@app.get("/campaigns", response_model=list[Campaign])
async def get_campaigns(db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get all campaigns."""
    try:
        campaigns = db.query(DbCampaign).all()
        return campaigns
    except Exception as e:
        logger.error(f"Error getting campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: int, db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get a specific campaign by ID."""
    try:
        campaign = db.query(DbCampaign).filter(DbCampaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/adgroups", response_model=list[AdGroup])
async def get_ad_groups(db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get all ad groups."""
    try:
        ad_groups = db.query(DbAdGroup).all()
        return ad_groups
    except Exception as e:
        logger.error(f"Error getting ad groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/adgroups/{adgroup_id}", response_model=AdGroup)
async def get_ad_group(adgroup_id: int, db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get a specific ad group by ID."""
    try:
        ad_group = db.query(DbAdGroup).filter(DbAdGroup.id == adgroup_id).first()
        if not ad_group:
            raise HTTPException(status_code=404, detail="Ad group not found")
        return ad_group
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ad group: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/creatives/{creative_id}", response_model=CreativeAsset)
async def get_creative(creative_id: int, db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get a specific creative asset by ID."""
    try:
        creative = db.query(DbCreativeAsset).filter(DbCreativeAsset.id == creative_id).first()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        return creative
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting creative: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/campaign-performance", response_model=list[CampaignPerformanceReport])
async def get_campaign_performance(db: Session = Depends(lambda: next(db_manager.get_db()))):
    """Get campaign performance reports."""
    try:
        from app.analytics.advanced import AdvancedAnalytics
        analytics = AdvancedAnalytics(db)
        
        # Get all campaigns with their performance
        campaigns = db.query(DbCampaign).all()
        reports = []
        for campaign in campaigns:
            roi_data = analytics.calculate_campaign_roi(campaign.id)
            reports.append(CampaignPerformanceReport(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                impressions=roi_data.total_impressions if roi_data else 0,
                clicks=roi_data.total_clicks if roi_data else 0,
                conversions=roi_data.total_conversions if roi_data else 0,
                spend=roi_data.total_spend if roi_data else campaign.budget,
                revenue=roi_data.revenue if roi_data else 0.0,
                roi=roi_data.roi_percentage if roi_data else 0.0,
            ))
        return reports
    except Exception as e:
        logger.error(f"Error getting campaign performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
