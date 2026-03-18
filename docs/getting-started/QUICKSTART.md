# Intent Engine - Quick Start Guide

> **Get your privacy-first search engine running in 5 minutes**

**Version:** v2.3.0 - Configuration & Health Improvements  
**Last Updated:** March 18, 2026

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Starting Services](#starting-services)
5. [Testing the API](#testing-the-api)
6. [Health Checks](#health-checks) ⭐ NEW
7. [Common Tasks](#common-tasks)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** (version 20.10+)
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
  - Verify: `docker --version`

- **Docker Compose** (version 2.0+)
  - Included with Docker Desktop
  - Verify: `docker compose version`

### System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space
- **CPU**: 2+ cores
- **OS**: Windows 10/11, macOS 10.15+, or Linux

---

## Installation

### Step 1: Clone the Repository

```bash
git clone git@github.com-work:itxLikhith/intent-engine.git
cd intent-engine
```

### Step 2: Verify Docker Setup

```bash
# Check Docker is running
docker info

# Check Docker Compose
docker compose version
```

---

## Configuration

### Option 1: Default Configuration (Recommended for Testing)

Use the default settings - everything is pre-configured to work out of the box.

### Option 2: Custom Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and customize as needed:

```bash
# IMPORTANT: Change this in production!
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-secure-random-string-here

# Change database password
POSTGRES_PASSWORD=your-secure-password

# IMPORTANT: For production/multi-worker, use Redis-backed rate limiting
# Memory-based rate limiting doesn't work across multiple workers
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/0
```

### Configuration Validation (v2.3.0)

The system now validates critical settings at startup:
- SECRET_KEY must be set and secure (production)
- DATABASE_PASSWORD must not be default (production)
- Rate limiting should use Redis (multi-worker deployments)

If validation fails, you'll see clear error messages at startup.

# Update CORS origins for your domain
CORS_ORIGINS=https://yourdomain.com
```

### Generate Secure Keys

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Starting Services

### Method 1: Using Startup Script (Recommended)

**Linux/Mac:**

```bash
# Make script executable (first time only)
chmod +x scripts/production_start.sh

# Start all services
./scripts/production_start.sh start

# Wait for initialization (~60 seconds)
sleep 60
```

**Windows PowerShell:**

```powershell
# Start all services
.\scripts\production_start.ps1 start

# Wait for initialization
Start-Sleep -Seconds 60
```

### Method 2: Using Docker Compose Directly

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to initialize
sleep 60

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Verify Services Are Running

You should see 4 services running:

```
NAME                    STATUS         PORTS
intent-engine-api       Up (healthy)   0.0.0.0:8000->8000/tcp
searxng                 Up (healthy)   0.0.0.0:8080->8080/tcp
intent-engine-postgres  Up (healthy)   0.0.0.0:5432->5432/tcp
intent-redis            Up (healthy)   0.0.0.0:6379->6379/tcp
```

---

## Testing the API

### Quick Health Check

```bash
# Root endpoint
curl http://localhost:8000/

# Detailed health check
curl http://localhost:8000/health

# SearXNG health
curl http://localhost:8080/healthz
```

### Test Search Functionality

#### Basic Search

```bash
curl http://localhost:8000/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "weather today"}'
```

#### Search with Intent Extraction

```bash
curl http://localhost:8000/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "query": "best laptop for programming under $1000",
    "extract_intent": true,
    "rank_results": true
  }'
```

#### Privacy-Focused Search

```bash
curl http://localhost:8000/search \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "query": "encrypted messaging apps",
    "exclude_big_tech": true,
    "min_privacy_score": 0.7
  }'
```

### Using API Example Scripts

**Linux/Mac:**

```bash
chmod +x scripts/api_examples.sh

# Run all examples
./scripts/api_examples.sh all

# Run specific endpoint tests
./scripts/api_examples.sh health
./scripts/api_examples.sh search
./scripts/api_examples.sh intent
```

**Windows PowerShell:**

```powershell
# Run all examples
.\scripts\api_examples.ps1 all

# Run specific endpoint tests
.\scripts\api_examples.ps1 health
.\scripts\api_examples.ps1 search
.\scripts\api_examples.ps1 intent
```

### Interactive API Documentation

Once services are running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Health Checks ⭐ NEW (v2.3.0)

### Basic Health Check

```bash
# Simple liveness check
curl http://localhost:8000/

# Comprehensive health check
curl http://localhost:8000/health
```

### Detailed Health Status

Get detailed health information with response times:

```bash
curl http://localhost:8000/health/detailed | jq
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T12:00:00Z",
  "services": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 2.1
    },
    "searxng": {
      "status": "healthy",
      "response_time_ms": 45.3
    }
  },
  "uptime_seconds": 3600
}
```

### Kubernetes-Style Probes

**Readiness Probe** (is the service ready to accept traffic?):

```bash
curl -f http://localhost:8000/health/ready
# Returns 200 if ready, 503 if not ready
```

**Liveness Probe** (is the service alive?):

```bash
curl -f http://localhost:8000/health/live
# Returns 200 if alive, 503 if unhealthy
```

### Health Check in Docker

Docker Compose automatically checks service health:

```bash
# Check service health status
docker-compose -f docker-compose.prod.yml ps

# View health check logs
docker inspect --format='{{json .State.Health}}' intent-engine-api | jq
```

---

## Common Tasks

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f intent-engine-api
docker-compose -f docker-compose.prod.yml logs -f searxng
```

### Stop Services

```bash
# Using script
./scripts/production_start.sh stop

# Or using docker-compose
docker-compose -f docker-compose.prod.yml down
```

### Restart Services

```bash
# Using script
./scripts/production_start.sh restart

# Or using docker-compose
docker-compose -f docker-compose.prod.yml restart
```

### Check Service Health

```bash
# Using script
./scripts/production_start.sh health

# Manual checks
curl http://localhost:8000/
curl http://localhost:8080/healthz
```

### Scale API Workers

```bash
# Scale to 3 API instances
docker-compose -f docker-compose.prod.yml up -d --scale intent-engine-api=3
```

### Update to Latest Version

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### Backup Database

```bash
# Create backup
docker exec intent-engine-postgres pg_dump \
  -U intent_user \
  intent_engine \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker exec -i intent-engine-postgres psql \
  -U intent_user \
  intent_engine \
  < backup_20260314_120000.sql
```

---

## Troubleshooting

### Services Won't Start

**Problem**: Containers fail to start

**Solutions**:

```bash
# Check Docker is running
docker info

# View error logs
docker-compose -f docker-compose.prod.yml logs

# Rebuild containers
docker-compose -f docker-compose.prod.yml up -d --build

# Start with fresh volumes (WARNING: deletes all data)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### Port Already in Use

**Problem**: Port 8000 or 8080 is already in use

**Solution**: Change ports in `docker-compose.prod.yml`

```yaml
# Change API port
intent-engine-api:
  ports:
    - "8001:8000"  # Use 8001 instead of 8000

# Change SearXNG port
searxng:
  ports:
    - "8081:8080"  # Use 8081 instead of 8080
```

### High Memory Usage

**Problem**: Services using too much memory

**Solutions**:

1. Reduce API workers in `docker-compose.prod.yml`:
   ```yaml
   environment:
     - WORKERS=1
   ```

2. Limit Redis memory (already set to 512MB)

3. Limit PostgreSQL memory (already set to 1GB)

### Search Returns No Results

**Problem**: Search API returns empty results

**Solutions**:

1. Check SearXNG is running:
   ```bash
   curl http://localhost:8080/healthz
   ```

2. Test SearXNG directly:
   ```bash
   curl http://localhost:8080/search?q=test
   ```

3. Check SearXNG logs:
   ```bash
   docker logs searxng
   ```

4. Verify SearXNG configuration:
   ```bash
   docker exec searxng cat /etc/searxng/settings.yml
   ```

### Database Connection Errors

**Problem**: API can't connect to database

**Solutions**:

1. Check PostgreSQL is running:
   ```bash
   docker exec intent-engine-postgres pg_isready -U intent_user -d intent_engine
   ```

2. Check database logs:
   ```bash
   docker logs intent-engine-postgres
   ```

3. Reinitialize database:
   ```bash
   docker-compose -f docker-compose.prod.yml down -v
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Slow Performance

**Problem**: Search is slow

**Solutions**:

1. Check Redis caching is enabled:
   ```bash
   docker exec intent-redis valkey-cli ping
   ```

2. Monitor API response times:
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/search -X POST -H "Content-Type: application/json" -d '{"query":"test"}'
   ```

3. Scale API workers:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --scale intent-engine-api=3
   ```

### CORS Errors

**Problem**: Browser blocks API requests

**Solution**: Update CORS origins in `.env`:

```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,https://yourdomain.com
```

Then restart:
```bash
docker-compose -f docker-compose.prod.yml restart intent-engine-api
```

---

## Next Steps

### Learn More

- [Production README](README_PRODUCTION.md) - Detailed production guide
- [Main README](README.md) - Complete documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

### Customize

- Edit `searxng/settings.yml` to customize search engines
- Modify `.env` for environment-specific settings
- Adjust `docker-compose.prod.yml` for resource limits

### Monitor

- View Prometheus metrics: http://localhost:8000/metrics
- Check Grafana dashboards (if enabled): http://localhost:3000

### Deploy to Production

Before deploying:

1. ✅ Change all default passwords
2. ✅ Generate secure SECRET_KEY
3. ✅ Configure SSL/TLS
4. ✅ Set up proper monitoring
5. ✅ Configure backups
6. ✅ Review security settings

---

## Support

- **GitHub Issues**: https://github.com/itxLikhith/intent-engine/issues
- **Documentation**: See README.md files in the repository

---

**Happy Searching! 🔍**
