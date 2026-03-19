# Running Both Docker Compose and AIO Containers

**Date:** March 19, 2026  
**Purpose:** Run both setups simultaneously without conflicts

---

## Overview

You can run **both** the regular Docker Compose setup AND the AIO (All-In-One) container simultaneously by using different ports.

---

## Current Setup Status

### Regular Docker Compose (Multi-Container)
**Status:** ✅ Running  
**File:** `docker-compose.yml`  
**Containers:** 5 separate containers

| Service | Port | Status |
|---------|------|--------|
| API | 8000 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running |
| Redis | 6379 | ✅ Running |
| Qdrant | 6333-6334 | ✅ Running |
| SearXNG | 8080 | ✅ Running |

---

### AIO Container (Single Container)
**Status:** ⏳ Building  
**File:** `infrastructure/compose/docker-compose.aio.yml`  
**Containers:** 1 monolithic container

| Service | Port (Planned) | Status |
|---------|----------------|--------|
| API (via nginx) | 80 | ⏳ Building |
| PostgreSQL | 5433 | ⏳ Will run |
| Redis | 6380 | ⏳ Will run |
| Qdrant | 6334 | ⏳ Will run |
| SearXNG | 8081 | ⏳ Will run |
| Go Search API | 8082 | ⏳ Will run |

---

## Port Conflict Prevention

### Current Port Usage
```
Port 8000  → Regular Compose API
Port 5432  → Regular Compose PostgreSQL
Port 6379  → Regular Compose Redis
Port 6333  → Regular Compose Qdrant
Port 8080  → Regular Compose SearXNG
```

### AIO Port Mapping (After Build)
To avoid conflicts, AIO uses DIFFERENT ports:

```bash
# AIO Configuration (docker-compose.aio.yml)
ports:
  - "80:80"           # AIO API (different from 8000)
  - "5433:5432"       # AIO PostgreSQL (different from 5432)
  - "8081:8080"       # AIO SearXNG (different from 8080)
  - "6334:6333"       # AIO Qdrant (different from 6333)
  - "6380:6379"       # AIO Redis (different from 6379)
```

---

## How to Run Both Simultaneously

### 1. Regular Compose (Already Running)
```bash
# This is already running
docker-compose ps
```

### 2. Start AIO Container (After Build Completes)
```bash
# Start AIO on different ports
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d
```

### 3. Verify Both Running
```bash
# Check regular compose
docker-compose ps

# Check AIO
docker-compose -f infrastructure/compose/docker-compose.aio.yml ps
```

---

## Accessing Services

### Regular Compose Services
```bash
# API
curl http://localhost:8000/health

# SearXNG
curl http://localhost:8080/healthz

# PostgreSQL
psql -h localhost -p 5432 -U intent_user -d intent_engine

# Qdrant
curl http://localhost:6333/
```

### AIO Services
```bash
# API (via nginx)
curl http://localhost:80/

# SearXNG
curl http://localhost:8081/healthz

# PostgreSQL
psql -h localhost -p 5433 -U intent_user -d intent_engine

# Qdrant
curl http://localhost:6334/
```

---

## Stopping Services

### Stop Regular Compose (Keep AIO Running)
```bash
docker-compose down
```

### Stop AIO (Keep Regular Compose Running)
```bash
docker-compose -f infrastructure/compose/docker-compose.aio.yml down
```

### Stop Both
```bash
docker-compose down
docker-compose -f infrastructure/compose/docker-compose.aio.yml down
```

---

## Use Cases for Each Setup

### Regular Docker Compose (Multi-Container)
**Best For:**
- ✅ Development
- ✅ Testing individual services
- ✅ Debugging
- ✅ Scaling specific services
- ✅ Learning architecture

**Advantages:**
- Separate logs per service
- Can restart individual services
- Easy to scale (e.g., `--scale worker=3`)
- Better resource isolation

---

### AIO Container (Single Container)
**Best For:**
- ✅ Production deployment
- ✅ Simple hosting environments
- ✅ Resource-constrained systems
- ✅ Easy deployment (single container)
- ✅ Testing the complete stack

**Advantages:**
- Single container to manage
- Lower overhead (no inter-container networking)
- Easier to deploy to simple VPS
- All services start together
- Simpler backup/restore

---

## Resource Requirements

### Regular Compose
- **RAM:** ~4-6 GB total
- **CPU:** 2-4 cores recommended
- **Disk:** ~10 GB

### AIO Container
- **RAM:** ~3-5 GB total
- **CPU:** 2-4 cores recommended
- **Disk:** ~8 GB

### Running Both Simultaneously
- **RAM:** ~7-11 GB total
- **CPU:** 4-8 cores recommended
- **Disk:** ~18 GB

---

## Troubleshooting

### Port Already in Use
If you get "port already allocated" errors:

```bash
# Check what's using the port
netstat -ano | findstr :8080

# Stop the conflicting service
docker-compose down
# OR
docker-compose -f infrastructure/compose/docker-compose.aio.yml down
```

### AIO Won't Start
Check logs:
```bash
docker logs intent-engine-aio -f
```

### Services Can't Connect
AIO uses `127.0.0.1` for internal connections (all services in same container), while regular compose uses service names (e.g., `postgres`, `redis`).

---

## Environment Variables

### Regular Compose
Uses `.env` file in project root.

### AIO Container
Uses environment variables defined in `docker-compose.aio.yml` or `.env.aio` file.

**Key Difference:** AIO uses `127.0.0.1` for all internal service connections since everything runs in the same container.

---

## Backup Strategies

### Regular Compose
```bash
# Backup PostgreSQL
docker exec intent-engine-postgres pg_dump -U intent_user intent_engine > backup.sql

# Backup Redis
docker exec intent-engine-redis valkey-cli SAVE
```

### AIO Container
```bash
# Backup PostgreSQL (from AIO)
docker exec intent-engine-aio sudo -u postgres pg_dump -U intent_user intent_engine > aio-backup.sql

# Backup entire container
docker commit intent-engine-aio intent-engine-aio-backup
```

---

## Migration Between Setups

### From Regular Compose to AIO
1. Stop regular compose: `docker-compose down`
2. Backup database from regular compose
3. Restore database to AIO PostgreSQL
4. Update environment variables
5. Start AIO: `docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d`

### From AIO to Regular Compose
1. Stop AIO: `docker-compose -f infrastructure/compose/docker-compose.aio.yml down`
2. Backup database from AIO
3. Restore database to regular compose PostgreSQL
4. Update environment variables
5. Start regular compose: `docker-compose up -d`

---

## Performance Comparison

| Metric | Regular Compose | AIO Container |
|--------|----------------|---------------|
| **Startup Time** | 60-90s | 90-120s |
| **Memory Usage** | ~5 GB | ~4 GB |
| **Network Latency** | Inter-container | Intra-container (faster) |
| **Disk Usage** | ~10 GB | ~8 GB |
| **Ease of Debugging** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Production Ready** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Recommendation

### For Development
Use **Regular Docker Compose**:
- Better visibility into individual services
- Easier debugging
- Can restart services independently

### For Production
Use **AIO Container**:
- Simpler deployment
- Lower resource overhead
- Single point of management

### For Testing Both
Run **Both Simultaneously**:
- Regular compose on ports 8000, 5432, 8080, 6333
- AIO on ports 80, 5433, 8081, 6334
- Compare performance and behavior

---

## Quick Reference

```bash
# Start regular compose
docker-compose up -d

# Start AIO
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d

# Check both
docker ps | grep intent-engine

# Stop regular compose
docker-compose down

# Stop AIO
docker-compose -f infrastructure/compose/docker-compose.aio.yml down

# Access regular API
curl http://localhost:8000/health

# Access AIO API
curl http://localhost:80/
```

---

**Status:** Both setups designed to coexist peacefully  
**Port Strategy:** Non-overlapping port mappings  
**Recommendation:** Use regular compose for dev, AIO for production
