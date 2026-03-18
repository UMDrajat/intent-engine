import json
import logging
import os
import sys

from arq import create_pool
from arq.connections import RedisSettings

# Add current directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.embedding_service import get_embedding_service
from app.core.schema import IntentExtractionRequest
from app.extraction.extractor import extract_intent
from app.scrapers.dynamic_worker import scrape_dynamic_product

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


async def startup(ctx):
    """
    Binds the redis connection pool and services to the context.
    """
    ctx["redis"] = await create_pool(RedisSettings(host=REDIS_HOST, port=REDIS_PORT))
    ctx["embedding_service"] = get_embedding_service()
    logger.info("Worker started: services initialized")


async def shutdown(ctx):
    """
    Closes the redis connection pool.
    """
    await ctx["redis"].close()
    logger.info("Worker shutting down")


async def scrape_dynamic_url(ctx, url: str):
    """
    Background task to scrape a URL using Playwright.
    """
    result = await scrape_dynamic_product(url)
    if result:
        key = f"dynamic_scrape:{url}"
        await ctx["redis"].setex(key, 3600, json.dumps(result))
    return result


async def enrich_document_intent(ctx, page_id: int, url: str, title: str, content: str):
    """
    Asynchronously extracts intent and generates embeddings for a crawled page.
    This is called by the Go indexer to offload heavy NLP work.
    """
    logger.info(f"Enriching intent for page {page_id}: {url}")

    try:
        # 1. Extract Intent using rule-based + semantic hybrid
        # Construct a request that fits our extractor
        request = IntentExtractionRequest(
            product="generic_web",
            input={"text": f"{title}\n{content[:2000]}"},
            context={"session_id": f"worker_{page_id}"},
        )

        # Use our existing intent extraction logic
        extraction_res = extract_intent(request)

        # 2. Generate Embedding
        embedding_service = ctx["embedding_service"]
        embedding = embedding_service.encode_text(f"{title} {content[:1000]}")

        # 3. Update database or cache with results
        # For now, we'll store in Redis so the Go indexer can pick it up,
        # or we could write directly to PostgreSQL/Qdrant.

        enrichment_data = {
            "page_id": page_id,
            "url": url,
            "intent": {
                "goal": extraction_res.universal_intent.goal if extraction_res.universal_intent else "information",
                "topics": extraction_res.universal_intent.use_cases if extraction_res.universal_intent else [],
                "complexity": extraction_res.universal_intent.skill_level
                if extraction_res.universal_intent
                else "beginner",
            },
            "embedding": embedding.tolist() if embedding is not None else [],
        }

        # Store in Redis for the indexer to complete the indexing process
        key = f"intent_enrichment:{page_id}"
        await ctx["redis"].setex(key, 3600, json.dumps(enrichment_data))

        logger.info(f"Successfully enriched intent for page {page_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to enrich intent for page {page_id}: {str(e)}")
        return False


class WorkerSettings:
    """
    arq worker settings.
    """

    functions = [scrape_dynamic_url, enrich_document_intent]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)
    job_timeout = 120  # Increased for NLP tasks
    max_jobs = 2  # Keep low to manage memory/CPU during embedding
