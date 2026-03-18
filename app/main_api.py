@app.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes-style readiness probe.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if not ready (e.g., models still loading).

    This endpoint is designed for load balancer health checks.
    """
    from fastapi.responses import JSONResponse
    from app.config.health_checks import health_checker

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
    """
    Kubernetes-style liveness probe.

    Returns 200 if the service is alive.
    Returns 503 if the service is deadlocked or unresponsive.

    This endpoint is designed for container orchestrators to detect
    when a container needs to be restarted.
    """
    from fastapi.responses import JSONResponse
    from app.config.health_checks import health_checker

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
