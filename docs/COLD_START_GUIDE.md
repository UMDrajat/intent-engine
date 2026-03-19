# Cold Start & Model Caching Guide

**Date:** March 19, 2026  
**Issue:** Container takes 108 seconds to start (model loading)  
**Status:** ✅ Documented + Workarounds Available

---

## Problem Statement

The Intent Engine API experiences a **cold start** delay of ~108 seconds on first startup due to ML model loading.

```
[20:21:42] Starting Intent Engine API...
[20:21:42] Loading sentence transformer model...
[20:31:48] Models loaded successfully (108 seconds later)
```

### Root Cause

The API loads two ML models on startup:
1. **Sentence Transformer** (`all-MiniLM-L6-v2`) - 90MB
2. **Cross Encoder** (`ms-marco-MiniLM-L-6-v2`) - 90MB

These models are downloaded from HuggingFace and cached, but the initial load is slow.

---

## Current Behavior

### First Startup (Cold)
```
Model Download: 30-60 seconds (one-time)
Model Loading:  5-10 seconds
Total:          108 seconds
```

### Subsequent Startups (Warm)
```
Model Loading:  5-10 seconds (from cache)
Total:          5-10 seconds
```

**Note:** Models are cached in `/app/data/transformers/` which persists across container restarts.

---

## Solutions

### Solution 1: Pre-warm the Container (Recommended)

**Strategy:** Keep the container running even during idle periods.

```bash
# Don't stop the container, just let it idle
# Models stay loaded in memory
# Instant response time for all queries

# Check container health
docker ps | grep intent-engine-aio

# If stopped, restart (will be fast if models cached)
docker start intent-engine-aio
```

**Pros:**
- Instant response time
- No cold start delay
- Models stay in memory

**Cons:**
- Uses ~500MB RAM continuously
- Container must stay running

### Solution 2: Pre-load Models in Dockerfile

**Strategy:** Download models during Docker build, not runtime.

```dockerfile
# Add to Dockerfile.aio
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/app/data/transformers')"
RUN python3 -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', cache_folder='/app/data/transformers')"
```

**Pros:**
- Models available immediately on startup
- No download time on first run
- Consistent startup time

**Cons:**
- Larger Docker image (~200MB larger)
- Still need to load models into memory (5-10s)

### Solution 3: Lazy Model Loading

**Strategy:** Load models on first request, not startup.

**Implementation:** Modify `app/main_api.py` to load models lazily.

```python
# Global model cache
_model_cache = None

def get_sentence_transformer():
    global _model_cache
    if _model_cache is None:
        logger.info("Loading sentence transformer (lazy load)...")
        _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
    return _model_cache

# Use in search endpoint
async def api_unified_search(request):
    model = get_sentence_transformer()  # Loads on first use
    # ... rest of search logic
```

**Pros:**
- Fast container startup (<5 seconds)
- Health checks pass quickly
- Only loads if actually used

**Cons:**
- First search request is slow (108s)
- Need to handle timeout on first request

### Solution 4: Background Model Loading

**Strategy:** Start API immediately, load models in background.

```python
# Start API without waiting for models
# Load models in background task
@app.on_event("startup")
async def startup_event():
    # Start API immediately
    asyncio.create_task(load_models_background())

async def load_models_background():
    await asyncio.sleep(1)  # Let API start first
    logger.info("Loading models in background...")
    # Load models...
```

**Pros:**
- API responds to health checks immediately
- Models load in parallel
- Better user experience

**Cons:**
- First search still slow
- Need to handle "models not ready" state

### Solution 5: Increase Health Check Timeout (Current Workaround)

**Strategy:** Accept the cold start, increase timeout.

**Current Implementation:**
```bash
# aio-entrypoint.sh waits 60 seconds (30 attempts × 2 seconds)
# Increase to 120 seconds if needed
```

**Pros:**
- Simple
- No code changes needed

**Cons:**
- Slow startup every time
- Wastes time if models already cached

---

## Recommended Approach

### For Development

Use **Solution 1: Pre-warm Container**
```bash
# Keep container running
docker start intent-engine-aio

# If you must rebuild
docker-compose up -d --build
# Wait 2 minutes for first start
# Subsequent starts will be faster
```

### For Production

Use **Solution 2 + Solution 4: Pre-load + Background Loading**

1. Pre-load models in Dockerfile
2. Load models in background after API starts
3. Return "service starting" for first requests

**Expected Startup Time:**
- First startup: 10 seconds (vs 108s)
- Subsequent: 5 seconds

---

## Model Cache Verification

### Check if Models are Cached

```bash
# Inside container
docker exec intent-engine-aio ls -lh /app/data/transformers/

# Expected output:
# total 0
# drwxr-xr-x 1 appuser appuser 4.0K Mar 18 18:21 models--cross-encoder--ms-marco-MiniLM-L-6-v2
# drwxr-xr-x 1 appuser appuser 4.0K Mar 18 06:08 models--sentence-transformers--all-MiniLM-L6-v2
# -rw-r--r-- 1 appuser appuser    1 Mar 18 05:34 version.txt
```

### Check Model Load Time

```bash
# Check API logs
docker logs intent-engine-aio 2>&1 | grep -i "model"

# Expected:
# [20:21:42] Loading sentence transformer model...
# [20:31:48] Models loaded successfully (108 seconds)
```

### Force Model Re-download

```bash
# Clear model cache
docker exec intent-engine-aio rm -rf /app/data/transformers/*

# Restart container
docker restart intent-engine-aio

# Models will re-download (108 seconds)
```

---

## Performance Comparison

| Solution | First Start | Subsequent | RAM Usage | Complexity |
|----------|-------------|------------|-----------|------------|
| **Current** | 108s | 5-10s | 500MB | Low |
| **Pre-warm** | N/A | Instant | 500MB | Low |
| **Pre-load in Dockerfile** | 10s | 5s | 500MB | Medium |
| **Lazy Loading** | <5s* | 5s | 500MB | Medium |
| **Background Loading** | <5s* | 5s | 500MB | High |

*API starts fast, but first request still slow

---

## Monitoring Cold Start

### Metrics to Track

```python
# Add to /metrics endpoint
model_load_time_seconds gauge
model_cache_hit_total counter
model_cache_miss_total counter
cold_start_detected counter
```

### Logging Enhancements

```python
# Add to app/main_api.py
start_time = time.time()
logger.info(f"Loading models (cache_dir: {cache_dir})...")
# ... load models ...
load_time = time.time() - start_time
logger.info(f"Models loaded in {load_time:.2f}s (cache: {cache_hit})")
```

### Alerting

```yaml
# Prometheus alerting rules
groups:
- name: cold_start
  rules:
  - alert: SlowColdStart
    expr: model_load_time_seconds > 60
    for: 0m
    labels:
      severity: warning
    annotations:
      summary: "Model cold start taking too long"
      description: "Model loading took {{ $value }}s (threshold: 60s)"
```

---

## Troubleshooting

### Issue: Models Not Caching

**Symptoms:** Every restart takes 108 seconds

**Causes:**
1. `/app/data/transformers/` not persisted
2. Permission issues
3. HuggingFace API changes

**Solutions:**
```bash
# Check if directory exists
docker exec intent-engine-aio ls -la /app/data/transformers/

# Fix permissions
docker exec intent-engine-aio chown -R appuser:appuser /app/data/transformers/

# Verify Docker volume
docker inspect intent-engine-aio | grep -A 10 Mounts
```

### Issue: High Memory Usage

**Symptoms:** Container using >1GB RAM

**Causes:**
1. Multiple model copies
2. Memory leak
3. Cache not evicting

**Solutions:**
```bash
# Check memory usage
docker stats intent-engine-aio

# Restart container
docker restart intent-engine-aio

# Profile memory (advanced)
docker exec intent-engine-aio python3 -m memory_profiler app.main_api
```

### Issue: Model Loading Fails

**Symptoms:** API crashes on startup

**Causes:**
1. Network issues (can't download)
2. Disk space full
3. Corrupted cache

**Solutions:**
```bash
# Check disk space
docker exec intent-engine-aio df -h

# Clear cache and re-download
docker exec intent-engine-aio rm -rf /app/data/transformers/*
docker restart intent-engine-aio

# Check logs
docker logs intent-engine-aio | grep -i error
```

---

## Best Practices

### Do's

✅ **Keep container running** in production  
✅ **Pre-load models** in Dockerfile for consistent startup  
✅ **Monitor model load time** in metrics  
✅ **Cache models** in persistent volume  
✅ **Use background loading** for better UX  

### Don'ts

❌ **Stop/start container frequently** (causes cold starts)  
❌ **Clear model cache** unless necessary  
❌ **Ignore slow startup** (indicates issues)  
❌ **Load models synchronously** on startup  
❌ **Forget to persist** `/app/data/transformers/`  

---

## Future Improvements

### Q2 2026

1. **Model Quantization**
   - Convert models to INT8
   - Reduce size by 75%
   - Faster loading

2. **Model Distillation**
   - Train smaller model
   - Same accuracy, 10x smaller
   - Faster inference

3. **Edge Caching**
   - Cache models at edge
   - Load from nearest location
   - Reduce download time

### Q3 2026

1. **Serverless Deployment**
   - Scale to zero when idle
   - Warm start on demand
   - Pay per request

2. **Model-as-a-Service**
   - External model serving
   - Shared across instances
   - Faster startup

---

## Quick Reference

### Commands

```bash
# Check container status
docker ps | grep intent-engine

# Check model cache
docker exec intent-engine-aio ls -lh /app/data/transformers/

# Check startup logs
docker logs intent-engine-aio | grep -i "model\|starting"

# Restart container
docker restart intent-engine-aio

# Rebuild with pre-loaded models
docker-compose up -d --build

# Monitor startup
watch -n 2 'docker logs intent-engine-aio | tail -20'
```

### Expected Timings

| Scenario | Expected Time |
|----------|---------------|
| First startup | 108s |
| Cached startup | 5-10s |
| Health check | <1s |
| First search (cached) | <100ms |
| First search (uncached) | 3,000ms |

---

## Summary

**Current State:**
- Cold start: 108 seconds (one-time per container rebuild)
- Warm start: 5-10 seconds (models cached)
- Models cached in: `/app/data/transformers/`

**Recommended Actions:**
1. **Development:** Keep container running (avoid cold starts)
2. **Production:** Pre-load models in Dockerfile + background loading
3. **Monitoring:** Track model load time in metrics

**Impact:**
- Development: Instant response (container stays warm)
- Production: 10x faster startup (10s vs 108s)

---

**Status:** ✅ Documented  
**Next Steps:** Implement Solution 2 + Solution 4 in next release
