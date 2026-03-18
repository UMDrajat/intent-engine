# Intent Engine - Production Deployment Checklist

Use this checklist to ensure your Intent Engine search backend is properly configured for production deployment.

**Version:** v2.3.0 - Configuration & Health Improvements  
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
  - [ ] Update `docker-compose.yml` with same key
  - [ ] **v2.3.0:** Key is validated at startup (min 32 chars)

- [ ] **Change Database Password**
  ```bash
  # Generate secure password
  python -c "import secrets; print(secrets.token_urlsafe(16))"
  ```
  - [ ] Update `.env`: `POSTGRES_PASSWORD=<your-secure-password>`
  - [ ] Update `docker-compose.yml` with same password
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

- [ ] **Update Environment**
  - [ ] Set `CORS_ORIGINS` to HTTPS URLs
  - [ ] Configure any HTTPS-specific settings

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
  - [ ] Consider PgBouncer for high traffic
  - [ ] Configure `DATABASE_POOL_SIZE` appropriately

- [ ] **Backup Strategy**
  - [ ] Set up automated daily backups
  - [ ] Test restore procedure
  - [ ] Configure point-in-time recovery (if needed)

- [ ] **Monitoring**
  - [ ] Set up database monitoring
  - [ ] Configure alerting for slow queries
  - [ ] Monitor connection pool usage

### 4. Redis Configuration

- [ ] **Enable Authentication**
  ```yaml
  # In docker-compose.prod.yml
  command: valkey-server --requirepass your-redis-password
  ```
  - [ ] Set strong password
  - [ ] Update `REDIS_URL` with password

- [ ] **Memory Management**
  - [ ] Verify `maxmemory` is set (default: 512MB)
  - [ ] Configure eviction policy (default: allkeys-lru)

- [ ] **Persistence**
  - [ ] Enable RDB snapshots (default: enabled)
  - [ ] Consider AOF for durability

### 5. SearXNG Configuration

- [ ] **Customize Search Engines**
  - [ ] Edit `searxng/settings.yml`
  - [ ] Enable/disable engines based on needs
  - [ ] Configure API keys if needed

- [ ] **Rate Limiting**
  - [ ] Configure SearXNG rate limits
  - [ ] Set `SEARXNG_LIMITER=false` if using external rate limiting

- [ ] **Caching**
  - [ ] Verify Redis caching is enabled
  - [ ] Adjust `cache_time` as needed

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
  - [ ] Docker daemon configured for production

- [ ] **Network Configuration**
  - [ ] Firewall rules configured
  - [ ] Only necessary ports exposed (80, 443)
  - [ ] Internal services not publicly accessible

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
  docker-compose -f docker-compose.prod.yml up -d
  ```

- [ ] **Verify Deployment**
  ```bash
  # Check all services are running
  docker-compose -f docker-compose.prod.yml ps

  # Run verification script
  ./scripts/verify_setup.sh

  # Test health endpoints
  curl https://your-domain.com/
  curl https://your-domain.com/health
  ```

### 8. Testing

- [ ] **Functional Tests**
  - [ ] Basic search works
  - [ ] Intent extraction works
  - [ ] URL ranking works
  - [ ] Privacy filters work

- [ ] **Performance Tests**
  - [ ] Response time < 500ms
  - [ ] Concurrent request handling
  - [ ] Memory usage within limits

- [ ] **Security Tests**
  - [ ] CORS configured correctly
  - [ ] Rate limiting working
  - [ ] No sensitive data exposed

---

## Post-Deployment

### 9. Monitoring & Observability

- [ ] **Application Monitoring**
  - [ ] Prometheus metrics accessible
  - [ ] Key metrics tracked:
    - Request rate
    - Response time
    - Error rate
    - Memory usage

- [ ] **Logging**
  - [ ] Centralized logging configured
  - [ ] Log rotation enabled
  - [ ] Log levels appropriate (INFO for production)

- [ ] **Alerting**
  - [ ] Service downtime alerts
  - [ ] High error rate alerts
  - [ ] Resource usage alerts
  - [ ] Slow response time alerts

- [ ] **Health Checks** ⭐ v2.3.0 Enhanced
  - [ ] **Liveness Probe:** `GET /health/live` - Container orchestrator checks
  - [ ] **Readiness Probe:** `GET /health/ready` - Load balancer checks
  - [ ] **Detailed Health:** `GET /health/detailed` - Full service diagnostics
  - [ ] Docker Compose health checks configured (see `docker-compose.yml`)
  - [ ] Kubernetes probes configured (if using K8s)
  - [ ] Health check alerts configured
  
  **Health Check Endpoints:**
  ```bash
  # Basic health
  curl http://localhost:8000/health
  
  # Detailed health with response times
  curl http://localhost:8000/health/detailed | jq
  
  # Readiness (200=ready, 503=not ready)
  curl -f http://localhost:8000/health/ready
  
  # Liveness (200=alive, 503=unhealthy)
  curl -f http://localhost:8000/health/live
  ```
  
  **Monitored Services (v2.3.0):**
  - Database (PostgreSQL)
  - Redis/Valkey
  - SearXNG
  - Go Crawler
  - Go Indexer
  - Go Search API
  - Unified Search API
  - Qdrant Vector DB
  - ML Models

### 10. Maintenance

- [ ] **Regular Updates**
  - [ ] Security patches applied
  - [ ] Dependency updates reviewed
  - [ ] Docker images updated

- [ ] **Backup Verification**
  - [ ] Test restore quarterly
  - [ ] Verify backup integrity
  - [ ] Document restore procedure

- [ ] **Performance Review**
  - [ ] Monthly performance review
  - [ ] Identify bottlenecks
  - [ ] Optimize as needed

- [ ] **Security Audit**
  - [ ] Quarterly security review
  - [ ] Penetration testing
  - [ ] Vulnerability scanning

---

## Scaling

### 11. Horizontal Scaling

- [ ] **API Scaling**
  ```bash
  # Scale API workers
  docker-compose -f docker-compose.prod.yml up -d --scale intent-engine-api=3
  ```
  - [ ] Load balancer configured
  - [ ] Session affinity (if needed)
  - [ ] Health checks for all instances

- [ ] **Database Scaling**
  - [ ] Read replicas configured (if needed)
  - [ ] Connection pooling tuned
  - [ ] Query optimization reviewed

- [ ] **Cache Scaling**
  - [ ] Redis cluster (if needed)
  - [ ] Cache hit rate monitoring
  - [ ] Memory optimization

### 12. Performance Optimization

- [ ] **Caching Strategy**
  - [ ] Query result caching
  - [ ] Model caching
  - [ ] API response caching

- [ ] **Database Optimization**
  - [ ] Indexes on frequently queried columns
  - [ ] Query optimization
  - [ ] Connection pool tuning

- [ ] **Application Optimization**
  - [ ] Profile slow endpoints
  - [ ] Optimize ML model inference
  - [ ] Reduce memory footprint

---

## Compliance & Privacy

### 13. GDPR Compliance

- [ ] **Data Protection**
  - [ ] No user tracking implemented
  - [ ] Local processing verified
  - [ ] Data minimization practiced

- [ ] **User Rights**
  - [ ] Data deletion mechanism
  - [ ] Data export capability
  - [ ] Consent management

- [ ] **Documentation**
  - [ ] Privacy policy updated
  - [ ] Data processing records
  - [ ] DPIA completed (if required)

### 14. Security Best Practices

- [ ] **Access Control**
  - [ ] Principle of least privilege
  - [ ] Role-based access control
  - [ ] API authentication (if needed)

- [ ] **Data Security**
  - [ ] Encryption at rest
  - [ ] Encryption in transit (TLS)
  - [ ] Secure key management

- [ ] **Network Security**
  - [ ] Firewall configured
  - [ ] DDoS protection
  - [ ] Intrusion detection

---

## Disaster Recovery

### 15. Business Continuity

- [ ] **Backup Strategy**
  - [ ] Daily automated backups
  - [ ] Off-site backup storage
  - [ ] Backup encryption

- [ ] **Recovery Plan**
  - [ ] RTO (Recovery Time Objective) defined
  - [ ] RPO (Recovery Point Objective) defined
  - [ ] Documented recovery procedures

- [ ] **Testing**
  - [ ] Regular DR drills
  - [ ] Backup restore tests
  - [ ] Failover testing

---

## Final Verification

### 16. Go-Live Checklist

- [ ] All security configurations complete
- [ ] Monitoring and alerting active
- [ ] Backups configured and tested
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Rollback plan prepared
- [ ] Stakeholders notified

### 17. Post Go-Live

- [ ] Monitor closely for 24-48 hours
- [ ] Review error logs
- [ ] Check performance metrics
- [ ] Gather user feedback
- [ ] Address any issues promptly

---

## Quick Reference

### Important Commands

```bash
# Start services
docker-compose -f docker-compose.prod.yml up -d

# Stop services
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale API
docker-compose -f docker-compose.prod.yml up -d --scale intent-engine-api=3

# Backup database
docker exec intent-engine-postgres pg_dump -U intent_user intent_engine > backup.sql

# Restore database
docker exec -i intent-engine-postgres psql -U intent_user intent_engine < backup.sql

# Health checks
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8080/healthz
```

### Important Files

- `.env` - Environment configuration
- `docker-compose.prod.yml` - Production Docker configuration
- `searxng/settings.yml` - SearXNG search configuration
- `scripts/production_start.sh` - Startup script
- `scripts/verify_setup.sh` - Verification script

---

**Deployment Date:** _______________

**Deployed By:** _______________

**Verified By:** _______________

**Notes:**

_________________________________

_________________________________

_________________________________
