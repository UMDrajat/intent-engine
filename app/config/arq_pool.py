"""
Intent Engine - ARQ Pool Module

Provides a shared connection pool for enqueuing background tasks with arq.
"""

import logging
import os
import asyncio
from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

logger = logging.getLogger(__name__)

# ARQ connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

_arq_pool: Optional[ArqRedis] = None
_arq_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    """
    Get or create a shared ARQ connection pool.

    Returns:
        ArqRedis connection pool
    """
    global _arq_pool
    if _arq_pool is None:
        async with _arq_lock:
            if _arq_pool is None:
                try:
                    logger.info(f"Creating ARQ pool: {REDIS_HOST}:{REDIS_PORT}")
                    _arq_pool = await create_pool(
                        RedisSettings(host=REDIS_HOST, port=REDIS_PORT)
                    )
                    logger.info("ARQ pool created successfully")
                except Exception as e:
                    logger.error(f"Failed to create ARQ pool: {e}")
                    raise
    return _arq_pool


async def close_arq_pool():
    """Close the shared ARQ connection pool"""
    global _arq_pool
    if _arq_pool is not None:
        async with _arq_lock:
            if _arq_pool is not None:
                await _arq_pool.close()
                _arq_pool = None
                logger.info("ARQ pool closed")
