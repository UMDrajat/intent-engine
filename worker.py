import json

from arq import create_pool
from arq.connections import RedisSettings

from scrapers.dynamic_worker import scrape_dynamic_product

REDIS_HOST = "redis"
REDIS_PORT = 6379


async def startup(ctx):
    """
    Binds the redis connection pool to the context.
    """
    ctx["redis"] = await create_pool(RedisSettings(host=REDIS_HOST, port=REDIS_PORT))


async def shutdown(ctx):
    """
    Closes the redis connection pool.
    """
    await ctx["redis"].close()


async def scrape_dynamic_url(ctx, url: str):
    """
    Background task to scrape a URL using Playwright.
    Stores the result in Redis for retrieval by the API.
    """
    result = await scrape_dynamic_product(url)
    if result:
        # Store result in Redis with 1 hour TTL
        # Using a specific prefix for dynamic results
        key = f"dynamic_scrape:{url}"
        await ctx["redis"].setex(key, 3600, json.dumps(result))
    return result


async def placeholder_task(ctx):
    """
    Placeholder background task.
    Add actual background tasks here as needed.
    """
    pass


class WorkerSettings:
    """
    arq worker settings.
    """

    functions = [placeholder_task, scrape_dynamic_url]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)
    # Limit concurrency to save RAM
    job_timeout = 60
    max_jobs = 3
