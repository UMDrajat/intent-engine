"""
Comprehensive Health Check Service for Intent Engine.

This module provides authoritative health checks for all services and dependencies,
with proper readiness and liveness probes.

Usage:
    from app.config.health_checks import HealthCheckService

    checker = HealthCheckService()
    status = await checker.check_all()
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class HealthStatus(StrEnum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceType(StrEnum):
    """Service types for health checks."""

    DATABASE = "database"
    REDIS = "redis"
    SEARXNG = "searxng"
    GO_CRAWLER = "go_crawler"
    GO_INDEXER = "go_indexer"
    GO_SEARCH_API = "go_search_api"
    UNIFIED_SEARCH = "unified_search"
    QDRANT = "qdrant"
    MODELS = "models"
    CACHE = "cache"


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    service: ServiceType
    status: HealthStatus
    response_time_ms: float | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "service": self.service.value,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "error": self.error,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SystemHealth:
    """Overall system health status."""

    status: HealthStatus
    timestamp: datetime
    services: dict[ServiceType, ServiceHealth]
    version: str
    environment: str
    uptime_seconds: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "services": {
                service.value: health.to_dict()
                for service, health in self.services.items()
            },
            "version": self.version,
            "environment": self.environment,
            "uptime_seconds": self.uptime_seconds,
        }


class HealthCheckService:
    """
    Centralized health check service for Intent Engine.

    Provides authoritative health checks for all services with:
    - Liveness probes (is the service running?)
    - Readiness probes (is the service ready to accept traffic?)
    - Detailed error reporting
    - Response time metrics
    """

    START_TIME = time.time()

    def __init__(
        self,
        database_url: str | None = None,
        redis_url: str | None = None,
        searxng_url: str | None = None,
        go_crawler_url: str | None = None,
        go_indexer_url: str | None = None,
        go_search_api_url: str | None = None,
        unified_search_url: str | None = None,
        qdrant_url: str | None = None,
    ):
        """Initialize health check service with service URLs."""
        import os

        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.searxng_url = searxng_url or os.getenv(
            "SEARXNG_BASE_URL", "http://searxng:8080"
        )
        self.go_crawler_url = go_crawler_url or os.getenv(
            "GO_CRAWLER_URL", "http://go-crawler:8080"
        )
        self.go_indexer_url = go_indexer_url or os.getenv(
            "GO_INDEXER_URL", "http://go-indexer:8080"
        )
        self.go_search_api_url = go_search_api_url or os.getenv(
            "GO_SEARCH_API_URL", "http://127.0.0.1:8081"
        )
        self.unified_search_url = unified_search_url or os.getenv(
            "UNIFIED_SEARCH_URL", "http://127.0.0.1:8082"
        )
        qdrant_host = os.getenv("QDRANT_HOST", "127.0.0.1")
        qdrant_port = os.getenv("QDRANT_PORT", "6333")
        self.qdrant_url = qdrant_url or f"http://{qdrant_host}:{qdrant_port}"

        self._models_loaded = False
        self._model_load_start = time.time()
        self._model_load_timeout = 120  # 2 minutes

    def mark_models_loaded(self) -> None:
        """Mark models as loaded."""
        self._models_loaded = True
        load_time = time.time() - self._model_load_start
        logger.info(f"Models loaded in {load_time:.2f}s")

    def _get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.START_TIME

    async def check_database(self) -> ServiceHealth:
        """Check database connectivity using synchronous driver."""
        start = time.time()
        try:
            if not self.database_url:
                return ServiceHealth(
                    service=ServiceType.DATABASE,
                    status=HealthStatus.UNHEALTHY,
                    error="DATABASE_URL not configured",
                )

            # Run synchronous database check in a thread to avoid blocking
            def _check():
                from sqlalchemy import create_engine, text

                # Use a very short timeout for health checks
                # If it's a postgres URL, ensure we don't try to use asyncpg here
                url = self.database_url
                if url.startswith("postgresql+asyncpg://"):
                    url = url.replace("postgresql+asyncpg://", "postgresql://")

                # connect_timeout is supported by psycopg2 but not sqlite3
                connect_args = {}
                if "postgresql" in url:
                    connect_args["connect_timeout"] = 5

                engine = create_engine(url, connect_args=connect_args)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
                return True

            await asyncio.get_event_loop().run_in_executor(None, _check)
            response_time = (time.time() - start) * 1000

            return ServiceHealth(
                service=ServiceType.DATABASE,
                status=HealthStatus.HEALTHY,
                response_time_ms=round(response_time, 2),
                details={
                    "url": self._sanitize_url(self.database_url),
                    "driver": "sync",
                },
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.error(f"Database health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.DATABASE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
            )

    async def check_redis(self) -> ServiceHealth:
        """Check Redis connectivity."""
        start = time.time()
        try:
            if not self.redis_url:
                return ServiceHealth(
                    service=ServiceType.REDIS,
                    status=HealthStatus.HEALTHY,
                    details={"status": "not configured"},
                )

            import redis.asyncio as redis

            client = redis.from_url(self.redis_url, socket_timeout=5)
            await client.ping()

            # Get Redis info
            info = await client.info("server")
            redis_version = info.get("redis_version", "unknown")

            response_time = (time.time() - start) * 1000
            await client.close()

            return ServiceHealth(
                service=ServiceType.REDIS,
                status=HealthStatus.HEALTHY,
                response_time_ms=round(response_time, 2),
                details={
                    "version": redis_version,
                    "url": self._sanitize_url(self.redis_url),
                },
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"Redis health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.REDIS,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
            )

    async def check_searxng(self) -> ServiceHealth:
        """
        Check SearXNG connectivity with authoritative health check.

        Uses the /healthz endpoint and validates response.
        Handles both JSON and HTML/text responses.
        """
        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Try health endpoint
                url = f"{self.searxng_url.rstrip('/')}/healthz"
                async with session.get(url) as response:
                    response_time = (time.time() - start) * 1000

                    if response.status == 200:
                        content_type = response.headers.get("Content-Type", "")
                        details = {"url": url, "content_type": content_type}

                        # Handle plain text response (like "OK")
                        if "text/plain" in content_type:
                            text = await response.text()
                            details["response"] = text.strip()
                            return ServiceHealth(
                                service=ServiceType.SEARXNG,
                                status=HealthStatus.HEALTHY,
                                response_time_ms=round(response_time, 2),
                                details=details,
                            )
                        elif "application/json" in content_type:
                            try:
                                details["response"] = await response.json()
                            except Exception:
                                details["response_text"] = await response.text()
                        else:
                            # If it's HTML but status is 200, we consider it healthy
                            details["note"] = "Received HTML response, status OK"
                            # Limit text to avoid bloating health check
                            text = await response.text()
                            details["response_preview"] = (
                                text[:100] + "..." if len(text) > 100 else text
                            )

                        return ServiceHealth(
                            service=ServiceType.SEARXNG,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=round(response_time, 2),
                            details=details,
                        )
                    else:
                        # Try alternative endpoint
                        async with session.get(
                            f"{self.searxng_url.rstrip('/')}/stats"
                        ) as alt_response:
                            if alt_response.status == 200:
                                response_time = (time.time() - start) * 1000
                                return ServiceHealth(
                                    service=ServiceType.SEARXNG,
                                    status=HealthStatus.HEALTHY,
                                    response_time_ms=round(response_time, 2),
                                    details={
                                        "url": f"{self.searxng_url}/stats",
                                        "fallback": True,
                                    },
                                )

                        raise Exception(f"Status {response.status}")

        except (TimeoutError, aiohttp.ClientConnectorError) as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"SearXNG health check failed (Connection Error): {e}")
            return ServiceHealth(
                service=ServiceType.SEARXNG,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=f"Connection failed: {type(e).__name__}",
                details={"url": self.searxng_url},
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"SearXNG health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.SEARXNG,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
                details={"url": self.searxng_url},
            )

    async def check_go_crawler(self) -> ServiceHealth:
        """
        Check Go Crawler service status.

        The Go crawler is a worker-only process and doesn't have a built-in health endpoint.
        We mark it as HEALTHY if we can't connect but know it's a worker-only service,
        or we can check if it's running via other means if needed.
        """
        # For now, we assume it's running if we're in the same network
        # or we just report it as a background worker.
        return ServiceHealth(
            service=ServiceType.GO_CRAWLER,
            status=HealthStatus.HEALTHY,
            details={
                "type": "background_worker",
                "note": "No HTTP endpoint (worker-only process)",
                "url": self.go_crawler_url,
            },
        )

    async def check_go_indexer(self) -> ServiceHealth:
        """
        Check Go Indexer service status.

        The Go indexer is a worker-only process and doesn't have a built-in health endpoint.
        """
        return ServiceHealth(
            service=ServiceType.GO_INDEXER,
            status=HealthStatus.HEALTHY,
            details={
                "type": "background_worker",
                "note": "No HTTP endpoint (worker-only process)",
                "url": self.go_indexer_url,
            },
        )

    async def check_go_search_api(self) -> ServiceHealth:
        """Check Go Search API health."""
        start = time.time()

        # Check if Go services are enabled
        if os.getenv("ENABLE_GO_SERVICES", "false").lower() != "true":
            return ServiceHealth(
                service=ServiceType.GO_SEARCH_API,
                status=HealthStatus.HEALTHY,
                details={
                    "status": "not_enabled",
                    "note": "Set ENABLE_GO_SERVICES=true to enable",
                },
            )

        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.go_search_api_url.rstrip('/')}/health"
                async with session.get(url) as response:
                    response_time = (time.time() - start) * 1000

                    if response.status == 200:
                        data = await response.json()
                        return ServiceHealth(
                            service=ServiceType.GO_SEARCH_API,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=round(response_time, 2),
                            details={"url": url, "response": data},
                        )
                    else:
                        raise Exception(f"Status {response.status}")

        except TimeoutError:
            response_time = (time.time() - start) * 1000
            logger.warning("Go Search API health check timeout")
            return ServiceHealth(
                service=ServiceType.GO_SEARCH_API,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error="Connection timeout",
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"Go Search API health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.GO_SEARCH_API,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
                details={"url": self.go_search_api_url},
            )

    async def check_unified_search(self) -> ServiceHealth:
        """Check Unified Search API health."""
        start = time.time()

        # Check if Go services are enabled
        if os.getenv("ENABLE_GO_SERVICES", "false").lower() != "true":
            return ServiceHealth(
                service=ServiceType.UNIFIED_SEARCH,
                status=HealthStatus.HEALTHY,
                details={
                    "status": "not_enabled",
                    "note": "Set ENABLE_GO_SERVICES=true to enable",
                },
            )

        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.unified_search_url.rstrip('/')}/health"
                async with session.get(url) as response:
                    response_time = (time.time() - start) * 1000

                    if response.status == 200:
                        return ServiceHealth(
                            service=ServiceType.UNIFIED_SEARCH,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=round(response_time, 2),
                            details={"url": url},
                        )
                    else:
                        raise Exception(f"Status {response.status}")

        except TimeoutError:
            response_time = (time.time() - start) * 1000
            logger.warning("Unified Search health check timeout")
            return ServiceHealth(
                service=ServiceType.UNIFIED_SEARCH,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error="Connection timeout",
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"Unified Search health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.UNIFIED_SEARCH,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
                details={"url": self.unified_search_url},
            )

    async def check_qdrant(self) -> ServiceHealth:
        """Check Qdrant vector database health."""
        start = time.time()

        # Check if Qdrant is enabled
        if os.getenv("ENABLE_QDRANT", "false").lower() != "true":
            return ServiceHealth(
                service=ServiceType.QDRANT,
                status=HealthStatus.HEALTHY,
                details={
                    "status": "not_enabled",
                    "note": "Set ENABLE_QDRANT=true to enable",
                },
            )

        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Try root endpoint first (most reliable across versions)
                url = f"{self.qdrant_url.rstrip('/')}/"
                async with session.get(url) as response:
                    response_time = (time.time() - start) * 1000

                    if response.status == 200:
                        data = await response.json()
                        return ServiceHealth(
                            service=ServiceType.QDRANT,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=round(response_time, 2),
                            details={
                                "url": url,
                                "version": data.get("version", "unknown"),
                            },
                        )
                    else:
                        raise Exception(f"Status {response.status}")

        except TimeoutError:
            response_time = (time.time() - start) * 1000
            logger.warning("Qdrant health check timeout")
            return ServiceHealth(
                service=ServiceType.QDRANT,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error="Connection timeout",
            )
        except Exception as e:
            response_time = (time.time() - start) * 1000
            logger.warning(f"Qdrant health check failed: {e}")
            return ServiceHealth(
                service=ServiceType.QDRANT,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=round(response_time, 2),
                error=str(e),
                details={"url": self.qdrant_url},
            )

    def check_models(self) -> ServiceHealth:
        """Check if ML models are loaded."""
        try:
            # Check if models directory exists and has files
            import os
            from pathlib import Path

            model_cache = Path(os.getenv("MODEL_CACHE_DIR", "./model_cache"))
            models_loaded = model_cache.exists() and any(model_cache.iterdir())

            if models_loaded or self._models_loaded:
                load_time = time.time() - self._model_load_start
                return ServiceHealth(
                    service=ServiceType.MODELS,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=round(load_time * 1000, 2),
                    details={
                        "loaded": True,
                        "cache_dir": str(model_cache),
                        "load_time_seconds": round(load_time, 2),
                    },
                )
            else:
                # Models not loaded yet, but that's OK during startup
                return ServiceHealth(
                    service=ServiceType.MODELS,
                    status=HealthStatus.HEALTHY,
                    details={
                        "loaded": False,
                        "note": "Models not yet loaded (normal during startup)",
                        "cache_dir": str(model_cache),
                    },
                )
        except Exception as e:
            logger.warning(f"Model check failed: {e}")
            return ServiceHealth(
                service=ServiceType.MODELS,
                status=HealthStatus.DEGRADED,
                error=str(e),
            )

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for logging (remove passwords)."""
        import re

        # Remove password from URL
        return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)

    async def check_all(self, include_optional: bool = True) -> SystemHealth:
        """
        Run comprehensive health checks on all services.

        Args:
            include_optional: Include optional services (SearXNG, Go services, Qdrant)

        Returns:
            SystemHealth object with status of all services
        """
        import os

        # Use individual awaitable tasks
        tasks = [
            self.check_database(),
            self.check_redis(),
        ]

        if include_optional:
            tasks.extend(
                [
                    self.check_searxng(),
                    self.check_go_crawler(),
                    self.check_go_indexer(),
                    self.check_go_search_api(),
                    self.check_unified_search(),
                    self.check_qdrant(),
                ]
            )

        # Execute all async health checks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        services: dict[ServiceType, ServiceHealth] = {}
        for result in results:
            if isinstance(result, ServiceHealth):
                services[result.service] = result
            elif isinstance(result, Exception):
                logger.error(f"Health check task failed: {result}")

        # Add models check (synchronous but wrapped in executor for consistency if needed,
        # or just run it directly as it's fast)
        services[ServiceType.MODELS] = self.check_models()

        # Determine overall status
        # Only certain services mark the entire system as unhealthy
        critical_services = [ServiceType.DATABASE, ServiceType.REDIS]

        overall_status = HealthStatus.HEALTHY

        for service_type, health in services.items():
            if health.status == HealthStatus.UNHEALTHY:
                if service_type in critical_services:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                else:
                    overall_status = HealthStatus.DEGRADED
            elif (
                health.status == HealthStatus.DEGRADED
                and overall_status == HealthStatus.HEALTHY
            ):
                overall_status = HealthStatus.DEGRADED

        # Get version
        try:
            from app.__version__ import __version__

            version = __version__
        except ImportError:
            version = "unknown"

        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now(UTC),
            services=services,
            version=version,
            environment=os.getenv("ENVIRONMENT", "development"),
            uptime_seconds=round(self._get_uptime(), 2),
        )

    async def check_readiness(self) -> bool:
        """
        Check if the service is ready to accept traffic.

        Returns:
            True if ready, False otherwise
        """
        health = await self.check_all(include_optional=False)

        # Critical services must be healthy
        critical = [ServiceType.DATABASE, ServiceType.REDIS]
        for service in critical:
            if service in health.services:
                if health.services[service].status != HealthStatus.HEALTHY:
                    return False

        # Models should be loaded
        if ServiceType.MODELS in health.services:
            details = health.services[ServiceType.MODELS].details
            if not details.get("loaded", False) and not self._models_loaded:
                # Check if we're still within load timeout
                if time.time() - self._model_load_start > self._model_load_timeout:
                    logger.warning("Models not loaded within timeout")
                    return False

        return True

    async def check_liveness(self) -> bool:
        """
        Check if the service is alive (basic process check).

        Returns:
            True if alive, False otherwise
        """
        # Simple check - if we can execute this method, we're alive
        return True


# Global health check service instance
health_checker = HealthCheckService()
