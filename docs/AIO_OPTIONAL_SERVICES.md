# AIO Container - Optional Services Implementation

## Overview

Added optional Qdrant, Go Search API, and Go Unified Search API services to the AIO container, controllable via environment variables.

## Environment Variables

### Enable Qdrant
```bash
ENABLE_QDRANT=true
```

### Enable Go Services (Search API + Unified Search API)
```bash
ENABLE_GO_SERVICES=true
```

## Ports

| Service | Port | Requires |
|---------|------|----------|
| Main API | 80 | Always |
| PostgreSQL | 5432 | Always |
| Redis | 6379 | Always (internal) |
| SearXNG | 8080 | Always |
| **Qdrant** | **6333** | `ENABLE_QDRANT=true` |
| **Go Search API** | **8081** | `ENABLE_GO_SERVICES=true` |
| **Go Unified Search API** | **8082** | `ENABLE_GO_SERVICES=true` |
| Prometheus Metrics | 9090 | Always |

## Usage Examples

### Basic AIO (default - Qdrant and Go services disabled)
```bash
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d
```

### Full AIO (with all services enabled)
```bash
# Set environment variables
export ENABLE_QDRANT=true
export ENABLE_GO_SERVICES=true

# Start container
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d
```

### Via docker-compose override
```yaml
# docker-compose.override.yml
services:
  intent-engine-aio:
    environment:
      - ENABLE_QDRANT=true
      - ENABLE_GO_SERVICES=true
```

## Health Check Status

When services are **disabled**, health check returns:
```json
{
  "service": "qdrant",
  "status": "healthy",
  "details": {
    "status": "not_enabled",
    "note": "Set ENABLE_QDRANT=true to enable"
  }
}
```

When services are **enabled but failing**, health check returns:
```json
{
  "service": "qdrant",
  "status": "unhealthy",
  "error": "Connection refused"
}
```

When services are **enabled and working**, health check returns:
```json
{
  "service": "qdrant",
  "status": "healthy",
  "response_time_ms": 5.2,
  "details": {
    "url": "http://127.0.0.1:6333/ready"
  }
}
```

## Accessing Services

### Via nginx proxy (recommended)
- Go Search API: `http://localhost:80/go-search/`
- Go Unified Search API: `http://localhost:80/unified-search/`
- Qdrant: `http://localhost:80/qdrant/`
- SearXNG: `http://localhost:80/searxng/`

### Direct access
- Go Search API: `http://localhost:8081/`
- Go Unified Search API: `http://localhost:8082/`
- Qdrant: `http://localhost:6333/`
- SearXNG: `http://localhost:8080/`

## Resource Requirements

### With all services enabled:
- **CPU:** 8 cores recommended
- **Memory:** 8GB recommended
- **Disk:** 10GB+ (Qdrant storage + Go binaries + models)

### Basic AIO (default):
- **CPU:** 4 cores
- **Memory:** 4GB
- **Disk:** 5GB

## Files Modified

1. **Dockerfile.aio**
   - Added Go installation for building Go services
   - Added Qdrant download and installation
   - Built Go Search API and Unified Search API binaries
   - Added new exposed ports

2. **aio-entrypoint.sh**
   - Added `ENABLE_QDRANT` and `ENABLE_GO_SERVICES` configuration
   - Added `start_qdrant()` function
   - Added `start_go_search_api()` function
   - Added `start_go_unified_search()` function
   - Updated main() to conditionally start services

3. **docker-compose.aio.yml**
   - Added port mappings for new services
   - Added environment variables for enabling services
   - Added Qdrant volume for persistence
   - Increased resource limits (8 CPU, 8GB RAM)

4. **nginx-aio.conf**
   - Added proxy locations for Go Search API
   - Added proxy locations for Go Unified Search API
   - Added proxy location for Qdrant

5. **health_checks.py**
   - Updated to check `ENABLE_QDRANT` and `ENABLE_GO_SERVICES` env vars
   - Returns "not_enabled" status when services are disabled
   - Updated default URLs to localhost for AIO container

## Testing

### Test with services disabled (default)
```bash
curl http://localhost:80/health/detailed | python -m json.tool
# All optional services should show "status": "not_enabled"
```

### Test with services enabled
```bash
# Enable services
docker-compose -f infrastructure/compose/docker-compose.aio.yml down
export ENABLE_QDRANT=true
export ENABLE_GO_SERVICES=true
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d

# Wait 2 minutes for all services to start
sleep 120

# Check health
curl http://localhost:80/health/detailed | python -m json.tool
# All services should show "status": "healthy"
```

### Test individual services
```bash
# Qdrant
curl http://localhost:6333/ready

# Go Search API
curl http://localhost:8081/health

# Go Unified Search API
curl http://localhost:8082/health

# Via nginx proxy
curl http://localhost:80/go-search/health
curl http://localhost:80/unified-search/health
curl http://localhost:80/qdrant/ready
```

## Troubleshooting

### Services show "unhealthy" when enabled
1. Check container logs: `docker logs intent-engine-aio`
2. Verify environment variables are set correctly
3. Check individual service logs in `/app/data/`

### Qdrant fails to start
- Check if port 6333 is available
- Verify `/qdrant/storage` directory permissions
- Check Qdrant logs: `docker exec intent-engine-aio cat /app/data/qdrant.log`

### Go services fail to start
- Verify Go binaries exist: `docker exec intent-engine-aio ls -la /usr/local/bin/search-api /usr/local/bin/unified-search`
- Check environment variables are set
- Check service logs: `docker exec intent-engine-aio cat /app/data/go-search-api.log`

## Migration Notes

### Existing deployments
- Existing deployments will NOT be affected - services remain disabled by default
- To enable new services, set environment variables and restart
- Data volumes are preserved across restarts

### Breaking changes
- None - all changes are backward compatible
- New ports are only used when services are explicitly enabled

---

**Implementation Date:** March 18, 2026  
**Version:** AIO v2.4.0 (with optional services)
