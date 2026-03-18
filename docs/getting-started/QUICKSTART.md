# Intent Engine - Quick Start Guide

> **Get your privacy-first search engine running in 5 minutes**

**Version:** v2.3.1 - Configuration & Health Improvements  
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
docker-compose -f infrastructure/compose/docker-compose.yml up -d

# Wait for services to initialize
sleep 60

# Check service status
docker-compose -f infrastructure/compose/docker-compose.yml ps
```

### Verify Services Are Running

You should see critical services running:

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

### Using API Example Scripts

**Linux/Mac:**

```bash
chmod +x scripts/api_examples.sh

# Run all examples
./scripts/api_examples.sh all
```

**Windows PowerShell:**

```powershell
# Run all examples
.\scripts\api_examples.ps1 all
```

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
curl http://localhost:8000/health/detailed
```

---

## Common Tasks

### View Logs

```bash
# All services
docker-compose -f infrastructure/compose/docker-compose.yml logs -f
```

### Stop Services

```bash
# Using script
./scripts/production_start.sh stop

# Or using docker-compose
docker-compose -f infrastructure/compose/docker-compose.yml down
```

---

## Next Steps

### Learn More

- [Production README](README_PRODUCTION.md) - Detailed production guide
- [Main README](../../README.md) - Complete documentation
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

---

**Happy Searching! 🔍**
