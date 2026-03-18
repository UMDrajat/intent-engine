# Intent Engine - Production Deployment Checklist

Use this checklist to ensure your Intent Engine search backend is properly configured for production deployment.

**Version:** v2.3.1 - Professional Organization Update  
**Last Updated:** March 18, 2026

---

## Pre-Deployment

### 1. Security Configuration

- [ ] **Change SECRET_KEY**
  ```bash
  # Generate secure key
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  - [ ] Update `.env`: `SECRET_KEY=<your-generated-key>`
  - [ ] Update `infrastructure/compose/docker-compose.yml` with same key
  - [ ] **v2.3.0:** Key is validated at startup (min 32 chars)

- [ ] **Change Database Password**
  ```bash
  # Generate secure password
  python -c "import secrets; print(secrets.token_urlsafe(16))"
  ```
  - [ ] Update `.env`: `POSTGRES_PASSWORD=<your-secure-password>`
  - [ ] Update `infrastructure/compose/docker-compose.yml` with same password
  - [ ] Update `DATABASE_URL` with new password
  - [ ] **v2.3.0:** Password validated at startup (not default)

- [ ] **Configure CORS**
  - [ ] Update `.env`: `CORS_ORIGINS=https://yourdomain.com`
  - [ ] Remove localhost origins in production

- [ ] **Rate Limiting Configuration** ⭐ v2.3.0
  - [ ] **CRITICAL:** Use Redis-backed rate limiting for multi-worker
  - [ ] Update `.env`: `RATE_LIMIT_STORAGE_URL=redis://redis:6379/0`
  - [ ] **DO NOT USE** `memory://` in production (doesn't work across workers)
  - [ ] Verify `RATE_LIMIT_ENABLED=true`
  - [ ] Adjust limits based on expected traffic

### 2. SSL/TLS Configuration

- [ ] **Obtain SSL Certificate**
  - [ ] Use Let's Encrypt or commercial CA
  - [ ] Certificate for your domain

- [ ] **Configure Reverse Proxy** (Nginx example)
  ```nginx
  server {
      listen 443 ssl;
      server_name your-domain.com;

      ssl_certificate /path/to/cert.pem;
      ssl_certificate_key /path/to/key.pem;

      location / {
          proxy_pass http://localhost:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
      }
  }
  ```

### 3. Database Configuration

- [ ] **PostgreSQL Tuning**
  ```bash
  # Recommended production settings
  shared_buffers = 256MB
  effective_cache_size = 1GB
  work_mem = 16MB
  maintenance_work_mem = 128MB
  ```

- [ ] **Enable Connection Pooling**
  - [ ] Use PgBouncer for high traffic (profiles: ["pgbouncer"])
  - [ ] Configure `DATABASE_POOL_SIZE` appropriately

- [ ] **Backup Strategy**
  - [ ] Set up automated daily backups
  - [ ] Test restore procedure

### 4. Redis Configuration

- [ ] **Enable Authentication**
  ```yaml
  # In infrastructure/compose/docker-compose.yml
  command: valkey-server --requirepass your-redis-password
  ```
  - [ ] Set strong password
  - [ ] Update `REDIS_URL` with password

### 5. SearXNG Configuration

- [ ] **Customize Search Engines**
  - [ ] Edit `app/searxng/settings.yml`
  - [ ] Enable/disable engines based on needs

---

## Deployment

### 6. Infrastructure Setup

- [ ] **Server Requirements**
  - [ ] Minimum 4GB RAM (8GB recommended)
  - [ ] 2+ CPU cores
  - [ ] 20GB+ disk space (SSD recommended)

- [ ] **Docker Setup**
  - [ ] Docker 20.10+ installed
  - [ ] Docker Compose 2.0+ installed

### 7. Deploy Application

- [ ] **Clone Repository**
  ```bash
  git clone git@github.com-work:itxLikhith/intent-engine.git
  cd intent-engine
  ```

- [ ] **Configure Environment**
  ```bash
  cp .env.example .env
  # Edit .env with production values
  ```

- [ ] **Start Services**
  ```bash
  docker-compose -f infrastructure/compose/docker-compose.yml up -d
  ```

- [ ] **Verify Deployment**
  ```bash
  # Check all services are running
  docker-compose -f infrastructure/compose/docker-compose.yml ps

  # Run verification script
  ./scripts/production_start.sh status

  # Test health endpoints
  curl https://your-domain.com/health/detailed
  ```

---

## Post-Deployment

### 8. Monitoring & Observability

- [ ] **Application Monitoring**
  - [ ] Prometheus metrics accessible (port 9090)
  - [ ] Grafana dashboards accessible (port 3000)

- [ ] **Health Checks** ⭐ v2.3.0 Enhanced
  - [ ] **Liveness Probe:** `GET /health/live`
  - [ ] **Readiness Probe:** `GET /health/ready`
  - [ ] **Detailed Health:** `GET /health/detailed`
  
  **Monitored Services:**
  - Database, Redis, SearXNG, Go Crawler, Go Indexer, Go Search API, Unified Search, Qdrant, ML Models

---

## Quick Reference

### Important Commands

```bash
# Start services
docker-compose -f infrastructure/compose/docker-compose.yml up -d

# Stop services
docker-compose -f infrastructure/compose/docker-compose.yml down

# View logs
docker-compose -f infrastructure/compose/docker-compose.yml logs -f

# Scale API
docker-compose -f infrastructure/compose/docker-compose.yml up -d --scale intent-engine-api=3

# Backup database
docker exec intent-engine-postgres pg_dump -U intent_user intent_engine > backup.sql

# Health checks
curl http://localhost:8000/health/detailed | jq
```

### Important Files

- `.env` - Environment configuration
- `infrastructure/compose/docker-compose.yml` - Centralized Docker configuration
- `app/searxng/settings.yml` - SearXNG search configuration
- `scripts/production_start.sh` - Startup script
- `run.py` - Main entry point wrapper

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Verified By:** _______________
