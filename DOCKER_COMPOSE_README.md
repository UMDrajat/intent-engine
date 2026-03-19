# Intent Engine - Docker Compose Setup Guide

> **Complete Multi-Container Deployment** - All services working together in Docker Compose

**Version:** v2.3.2 | **Last Updated:** March 19, 2026

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Service Profiles](#service-profiles)
- [Configuration](#configuration)
- [Service Details](#service-details)
- [Networking](#networking)
- [Data Persistence](#data-persistence)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

---

## 🎯 Overview

This Docker Compose setup orchestrates the **complete Intent Engine stack** with all services working together:

### Core Services
- **PostgreSQL 15** - Primary relational database
- **Redis/Valkey 8** - Cache, session management, and rate limiting
- **Qdrant** - Vector database for semantic search
- **SearXNG** - Privacy-focused search backend

### Application Services
- **Intent Engine API** - Main FastAPI application (port 8000)
- **ARQ Worker** - Background task processor (optional profile)
- **Vector Indexer** - Indexes content into Qdrant (optional profile)

### Go Services (Optional Profile: `go-services`)
- **Go Search API** - Bleve-based search engine (port 8081)
- **Go Crawler** - Distributed web crawler
- **Go Indexer** - Content indexer for Bleve
- **Go Unified Search API** - Unified search with intent ranking (port 8082)

### Monitoring & Observability (Optional Profile: `monitoring`)
- **Prometheus** - Metrics collection (port 9090)
- **Grafana** - Visualization dashboards (port 3000)

### Infrastructure (Optional Profile: `pgbouncer`)
- **PgBouncer** - Database connection pooling (port 6543)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │  API Server  │  │  ARQ Worker  │  │   Vector     │   │   │
│  │  │  (FastAPI)   │  │  (Background)│  │   Indexer    │   │   │
│  │  │  Port: 8000  │  │              │  │              │   │   │
│  │  └──────┬───────┘  └──────────────┘  └──────────────┘   │   │
│  │         │                                                 │   │
│  │  ┌──────┴──────────────────────────────────────────┐     │   │
│  │  │           Go Services (Optional)                 │     │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │     │   │
│  │  │  │  Search  │  │ Crawler  │  │   Unified    │  │     │   │
│  │  │  │   API    │  │          │  │    Search    │  │     │   │
│  │  │  │ :8080    │  │          │  │    :8082     │  │     │   │
│  │  │  └──────────┘  └──────────┘  └──────────────┘  │     │   │
│  │  └──────────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Data Layer                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │   │
│  │  │PostgreSQL│  │  Redis   │  │ Qdrant   │  │SearXNG  │  │   │
│  │  │  :5432   │  │  :6379   │  │  :6333   │  │ :8080   │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Monitoring (Optional)                       │   │
│  │  ┌──────────────┐         ┌──────────────┐              │   │
│  │  │  Prometheus  │────────▶│   Grafana    │              │   │
│  │  │   :9090      │         │    :3000     │              │   │
│  │  └──────────────┘         └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │   Load Balancer   │
                    │    (Optional)     │
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Users / Clients │
                    └───────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **8GB+ RAM** (16GB recommended for full stack)
- **10GB+ disk space**
- **Python 3.11+** (optional, for scripts)

### Installation (60 seconds)

#### **Linux/Mac**

```bash
# Clone repository (if not already done)
git clone git@github.com-work:itxLikhith/intent-engine.git
cd intent-engine

# Make script executable
chmod +x docker-start.sh

# Start all core services
./docker-start.sh start

# Wait for initialization (~60 seconds)
sleep 60

# Verify installation
./docker-start.sh health
```

#### **Windows PowerShell**

```powershell
# Navigate to project directory
cd C:\Users\Likhith\Documents\projects\intent-engine

# Start all core services
.\docker-start.ps1 start

# Wait for initialization (~60 seconds)
Start-Sleep -Seconds 60

# Verify installation
.\docker-start.ps1 health
```

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Extract intent from a query
curl -X POST http://localhost:8000/extract-intent \
  -H "Content-Type: application/json" \
  -d '{
    "product": "search",
    "input": {"text": "best laptop for programming under 50000 rupees"},
    "context": {"sessionId": "test-123", "userLocale": "en-US"}
  }' | jq

# Unified search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "best python tutorials for beginners"}' | jq
```

---

## 📦 Service Profiles

Docker Compose profiles allow you to start different service combinations:

### Core Services (Default)

```bash
# Start core services only
docker-compose up -d

# Services: API, PostgreSQL, Redis, Qdrant, SearXNG, Migrations
```

### With Go Services

```bash
# Enable Go services
export ENABLE_GO_SERVICES=true  # Linux/Mac
$env:ENABLE_GO_SERVICES="true"  # Windows PowerShell

# Start with Go services
docker-compose --profile go-services up -d

# Or use the script
./docker-start.sh start-full        # Linux/Mac
.\docker-start.ps1 start-full       # Windows
```

### With Monitoring

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Or use the script
./docker-start.sh start-monitoring  # Linux/Mac
.\docker-start.ps1 start-monitoring # Windows
```

### All Services

```bash
# Start everything
export ENABLE_GO_SERVICES=true
docker-compose --profile go-services --profile monitoring up -d

# Or use the script
./docker-start.sh start-all         # Linux/Mac
.\docker-start.ps1 start-all        # Windows
```

### Profile Summary

| Profile | Services | Use Case |
|---------|----------|----------|
| (none) | API, DB, Redis, Qdrant, SearXNG | Development, basic search |
| `go-services` | + Go Crawler, Indexer, Search APIs | Full search engine |
| `monitoring` | + Prometheus, Grafana | Production monitoring |
| `worker` | + ARQ Worker | Background tasks |
| `vector-indexer` | + Vector Indexer | Semantic search indexing |
| `pgbouncer` | + PgBouncer | High-traffic databases |

---

## ⚙️ Configuration

### Environment Variables

Copy the template and customize:

```bash
cp .env.docker .env
```

**Key Configuration Options:**

```bash
# Application
ENVIRONMENT=development          # development, staging, production
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
WORKERS=2                        # Number of API workers
API_PORT_EXTERNAL=8000           # External API port

# Database
POSTGRES_USER=intent_user
POSTGRES_PASSWORD=change_this_in_production
POSTGRES_DB=intent_engine
POSTGRES_PORT_EXTERNAL=5432

# Security (IMPORTANT: Change in production!)
SECRET_KEY=generate-secure-random-key-here

# Redis
REDIS_MAX_CONNECTIONS=50

# Qdrant
QDRANT_PORT_EXTERNAL=6333

# SearXNG
SEARXNG_PORT_EXTERNAL=8080
SEARXNG_SECRET_KEY=generate-with-openssl-rand-hex-32

# Go Services
ENABLE_GO_SERVICES=false
GO_SEARCH_API_PORT_EXTERNAL=8081
GO_UNIFIED_SEARCH_API_PORT_EXTERNAL=8082

# Monitoring
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_this_grafana_password
```

### Generate Secure Keys

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# SEARXNG_SECRET_KEY
openssl rand -hex 32

# ANONYMIZATION_SALT
python -c "import secrets; print(secrets.token_hex(16))"
```

---

## 🔍 Service Details

### Intent Engine API (Port 8000)

**Main application service**

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# View logs
docker-compose logs -f intent-engine-api
```

**Key Endpoints:**
- `GET /` - Liveness probe
- `GET /health` - Comprehensive health check
- `POST /extract-intent` - Extract structured intent
- `POST /search` - Unified search
- `POST /rank-results` - Rank results
- `POST /recommend-services` - Service recommendations
- `POST /match-ads` - Ad matching

### PostgreSQL (Port 5432)

**Primary database**

```bash
# Connect to database
docker exec -it intent-engine-postgres psql -U intent_user -d intent_engine

# View logs
docker-compose logs -f intent-engine-postgres

# Backup
docker exec intent-engine-postgres pg_dump -U intent_user intent_engine > backup.sql

# Restore
docker exec -i intent-engine-postgres psql -U intent_user intent_engine < backup.sql
```

### Redis/Valkey (Port 6379)

**Cache and rate limiting**

```bash
# Connect to Redis
docker exec -it intent-engine-redis valkey-cli

# View logs
docker-compose logs -f intent-engine-redis

# Check crawl queue
docker exec intent-engine-redis valkey-cli ZCARD crawl_queue
```

### Qdrant (Port 6333)

**Vector database**

```bash
# Web UI
open http://localhost:6333/dashboard

# API
curl http://localhost:6333/

# View logs
docker-compose logs -f intent-engine-qdrant
```

### SearXNG (Port 8080)

**Privacy-focused search**

```bash
# Web interface
open http://localhost:8080

# Health check
curl http://localhost:8080/healthz

# View logs
docker-compose logs -f intent-engine-searxng
```

### Go Search API (Port 8081)

**Bleve-based search** (requires `go-services` profile)

```bash
# Health check
curl http://localhost:8081/health

# Search
curl "http://localhost:8081/search?q=python+tutorial"

# View logs
docker-compose logs -f intent-go-search-api
```

### Go Unified Search API (Port 8082)

**Unified search with intent ranking** (requires `go-services` profile)

```bash
# Health check
curl http://localhost:8082/health

# Unified search
curl -X POST http://localhost:8082/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python tutorial", "intent": {"goal": "LEARN"}}'

# View logs
docker-compose logs -f intent-unified-search-api
```

### Prometheus (Port 9090)

**Metrics collection** (requires `monitoring` profile)

```bash
# Web UI
open http://localhost:9090

# Metrics
curl http://localhost:9090/metrics

# View logs
docker-compose logs -f intent-engine-prometheus
```

### Grafana (Port 3000)

**Visualization dashboards** (requires `monitoring` profile)

```bash
# Web UI (admin / grafana_secure_password_change_in_prod)
open http://localhost:3000

# View logs
docker-compose logs -f intent-engine-grafana
```

---

## 🌐 Networking

### Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    intent-network                        │
│  (172.28.0.0/16)                                        │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │   API    │  │PostgreSQL│  │  Redis   │  │ Qdrant  │ │
│  │  :8000   │  │  :5432   │  │  :6379   │  │ :6333   │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │Go Search │  │ Unified  │  │ SearXNG  │              │
│  │   API    │  │  Search  │  │          │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      searxng-network                     │
│  (Isolated network for SearXNG privacy)                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ SearXNG  │  │  Redis   │  │   API    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| API | 8000 | 8000 | HTTP |
| PostgreSQL | 5432 | 5432 | TCP |
| Redis | 6379 | - | TCP |
| Qdrant | 6333 | 6333 | HTTP |
| Qdrant gRPC | 6334 | 6334 | gRPC |
| SearXNG | 8080 | 8080 | HTTP |
| Go Search API | 8080 | 8081 | HTTP |
| Go Unified Search | 8082 | 8082 | HTTP |
| Prometheus | 9090 | 9090 | HTTP |
| Grafana | 3000 | 3000 | HTTP |
| PgBouncer | 6543 | 6543 | TCP |

---

## 💾 Data Persistence

### Named Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| `postgres_data` | PostgreSQL | Database files |
| `redis_data` | Redis | Cache persistence |
| `qdrant_data` | Qdrant | Vector index |
| `go-search-data` | Go Search API | Bleve index |
| `go-crawler-data` | Go Crawler | Crawler data |
| `go-indexer-data` | Go Indexer | Indexer data |
| `prometheus_data` | Prometheus | Metrics data |
| `grafana_data` | Grafana | Dashboards & config |
| `app_data` | API | Application data |
| `app_logs` | API | Application logs |

### Backup & Restore

```bash
# Backup PostgreSQL
docker exec intent-engine-postgres pg_dump -U intent_user intent_engine > backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
docker exec -i intent-engine-postgres psql -U intent_user intent_engine < backup_20260319.sql

# Backup Redis
docker exec intent-engine-redis valkey-cli SAVE
cp $(docker volume inspect intent-engine-redis_data | jq -r '.[0].Mountpoint')/dump.rdb redis_backup_$(date +%Y%m%d).rdb

# Backup Qdrant
tar -czf qdrant_backup_$(date +%Y%m%d).tar.gz $(docker volume inspect intent-engine-qdrant_data | jq -r '.[0].Mountpoint')
```

---

## 📊 Monitoring

### Prometheus Metrics

Access metrics at: `http://localhost:9090/metrics`

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `intent_extraction_duration_seconds` - Intent extraction time
- `search_duration_seconds` - Search latency
- `cache_hits_total` - Cache hit count
- `db_query_duration_seconds` - Database query time

### Grafana Dashboards

Access Grafana at: `http://localhost:3000`

**Default Credentials:**
- Username: `admin`
- Password: `grafana_secure_password_change_in_prod` (change in production!)

**Pre-configured Dashboards:**
- Intent Engine Overview
- API Performance
- Database Metrics
- Cache Performance
- Go Services Metrics

### Health Endpoints

```bash
# Basic health
curl http://localhost:8000/

# Detailed health
curl http://localhost:8000/health

# Readiness probe (Kubernetes)
curl http://localhost:8000/health/ready

# Liveness probe (Kubernetes)
curl http://localhost:8000/health/live
```

---

## 🐛 Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check logs
docker-compose logs intent-engine-api

# Check resource usage
docker stats

# Restart services
docker-compose restart intent-engine-api
```

#### Database Connection Errors

```bash
# Check PostgreSQL status
docker exec intent-engine-postgres pg_isready -U intent_user

# View PostgreSQL logs
docker-compose logs intent-engine-postgres

# Restart PostgreSQL
docker-compose restart intent-engine-postgres
```

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Reduce API workers
# Edit .env: WORKERS=1

# Restart API
docker-compose restart intent-engine-api
```

#### Cache Issues

```bash
# Clear Redis cache
docker exec intent-engine-redis valkey-cli FLUSHALL

# Check Redis memory
docker exec intent-engine-redis valkey-cli INFO memory
```

### Debug Mode

```bash
# Enable debug logging
# Edit .env: LOG_LEVEL=DEBUG

# Restart API
docker-compose restart intent-engine-api

# View debug logs
docker-compose logs -f intent-engine-api | grep DEBUG
```

### Clean Restart

```bash
# Stop all services
docker-compose down

# Remove volumes (⚠️ deletes all data!)
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache

# Start fresh
docker-compose up -d
```

---

## 🚀 Production Deployment

### Pre-Production Checklist

- [ ] Change all default passwords
- [ ] Generate secure random keys (SECRET_KEY, SEARXNG_SECRET_KEY, etc.)
- [ ] Configure CORS for your domain
- [ ] Set up SSL/TLS termination
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts
- [ ] Review resource limits
- [ ] Test disaster recovery

### Production Environment Variables

```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=WARNING
WORKERS=4

# Security
SECRET_KEY=<generate-secure-random-key>
CORS_ORIGINS=https://yourdomain.com

# Database
POSTGRES_PASSWORD=<secure-database-password>

# Redis
REDIS_PASSWORD=<secure-redis-password>

# Grafana
GRAFANA_ADMIN_PASSWORD=<secure-grafana-password>

# Monitoring
ENABLE_METRICS=true
HEALTH_CHECK_INTERVAL=30
```

### Scaling

```bash
# Scale API workers
docker-compose up -d --scale intent-engine-api=3

# Scale with specific profiles
docker-compose --profile go-services --profile monitoring up -d
```

### Load Balancing

For production, add a reverse proxy (nginx, traefik, etc.):

```nginx
# Example nginx configuration
upstream intent-engine {
    server intent-engine-api-1:8000;
    server intent-engine-api-2:8000;
    server intent-engine-api-3:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://intent-engine;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📚 Additional Resources

- [Main README](README.md) - Project overview
- [API Documentation](http://localhost:8000/docs) - Swagger UI
- [Grafana Dashboards](http://localhost:3000) - Monitoring
- [Prometheus Metrics](http://localhost:9090/metrics) - Raw metrics

---

**Maintained by:** Intent Engine Team  
**License:** Intent Engine Community License (IECL) v1.0  
**Version:** v2.3.2  
**Last Updated:** March 19, 2026
