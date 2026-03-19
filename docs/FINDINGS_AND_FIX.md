# Intent Engine API - Critical Findings & Fix Instructions

**Date:** March 19, 2026  
**Severity:** CRITICAL - Search Non-Functional  

---

## Root Cause Analysis: Zero Search Results

### Problem
All search queries return **ZERO results** despite SearXNG working correctly.

### Root Cause Confirmed
**The Go crawler has NOT INDEXED ANY CONTENT.**

### Evidence

1. **Crawl Queue Has URLs (27 URLs waiting):**
   ```bash
   docker exec intent-engine-aio redis-cli ZCARD crawl_queue
   # Output: 27
   ```

2. **NO URLs Have Been Crawled:**
   ```bash
   docker exec intent-engine-aio redis-cli ZRANGE crawled_urls 0 5
   # Output: (empty)
   ```

3. **Go Crawler Search Returns Empty:**
   ```bash
   docker exec intent-engine-aio curl -s "http://127.0.0.1:8081/api/v1/search?q=python&limit=5"
   # Output: (empty)
   ```

4. **But SearXNG Works Fine:**
   ```bash
   docker exec intent-engine-aio curl -s "http://127.0.0.1:8080/search?q=test&format=json"
   # Output: 91,500 results
   ```

### Diagnosis

The Go crawler **background worker is not running** or not processing the crawl queue. The AIO (All-in-One) container appears to only run the API server and nginx, but not the crawler worker process.

---

## Immediate Fix Instructions

### Option 1: Trigger Manual Crawl (Quick Fix)

Run this command inside the container to manually trigger crawling:

```bash
docker exec -it intent-engine-aio bash
# Inside container:
python -c "
from app.searxng.crawler_trigger import trigger_crawler
import asyncio
asyncio.run(trigger_crawler(batch_size=10))
"
```

**Note:** If the `crawler_trigger` module doesn't exist, you'll need to check the Go crawler documentation for the correct trigger mechanism.

### Option 2: Check if Go Crawler Process is Running

```bash
docker exec intent-engine-aio ps aux | grep -i go
docker exec intent-engine-aio ps aux | grep -i crawler
```

If no crawler process is found, the Go crawler needs to be started.

### Option 3: Start Go Crawler Worker

Check the container's entrypoint script to see if the crawler worker should be started:

```bash
docker exec intent-engine-aio cat /entrypoint.sh
# or
docker exec intent-engine-aio cat /start.sh
```

Look for crawler worker startup commands and ensure they're running.

### Option 4: Use Separate Go Crawler Container (Recommended)

The AIO container may not include the Go crawler worker. Check if you need to run the Go crawler as a separate service:

```bash
# Check docker-compose configuration
docker-compose -f infrastructure/compose/docker-compose.aio.yml config

# Look for missing crawler service
```

If the crawler is missing, you may need to:
1. Add the Go crawler service to the compose file, OR
2. Run the Go crawler separately using the `go-crawler/docker-compose.yml`

---

## Workaround: Use SearXNG-Only Search

While the crawler issue is being fixed, you can use SearXNG directly:

```bash
# Direct SearXNG search (works correctly)
curl "http://localhost:8080/search?q=python+tutorial&format=json"

# Or through the API with intent extraction disabled
curl -X POST http://localhost:80/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python tutorial",
    "extract_intent": false,
    "rank_results": false,
    "max_results": 10
  }'
```

---

## Additional Issues Found

### Issue #2: Ranking Endpoint Schema Mismatch

**Problem:** HTTP 422 error on `/rank-results`

**Fix:** Use correct schema with `candidates` field instead of `results`:

```json
{
  "intent": {
    "declared": {
      "query": "test",
      "goal": "LEARN",
      "constraints": []
    }
  },
  "candidates": [
    {"title": "Result 1", "url": "http://example.com", "content": "..."}
  ],
  "options": {}
}
```

---

## Performance Benchmarks

### Current Performance (With Zero Results Issue)

| Endpoint | Avg Time | Status |
|----------|----------|--------|
| `/health` | 32ms | ✅ OK |
| `/extract-intent` | 50ms | ✅ OK |
| `/search` | 5726ms | ❌ Zero Results |
| `/match-ads` | 8755ms | ⚠️ No Ads in DB |

### Expected Performance (After Fix)

| Endpoint | Target Time | Notes |
|----------|-------------|-------|
| `/health` | <50ms | Already meeting target |
| `/extract-intent` | <50ms | Already meeting target |
| `/search` (cache miss) | <500ms | Needs crawler fix |
| `/search` (cache hit) | <100ms | Enable Redis caching |
| `/match-ads` | <200ms | Add ads to database |

---

## Verification Steps After Fix

1. **Check Crawler is Running:**
   ```bash
   docker exec intent-engine-aio ps aux | grep -i crawler
   ```

2. **Verify URLs Are Being Crawled:**
   ```bash
   docker exec intent-engine-aio redis-cli ZCARD crawled_urls
   # Should show increasing count
   ```

3. **Test Go Crawler Search:**
   ```bash
   docker exec intent-engine-aio curl -s "http://127.0.0.1:8081/api/v1/search?q=python&limit=3"
   # Should return results
   ```

4. **Test Unified Search:**
   ```bash
   curl -X POST http://localhost:80/search \
     -H "Content-Type: application/json" \
     -d '{"query":"python tutorial","extract_intent":true,"max_results":5}'
   # Should return ranked results
   ```

---

## Long-term Recommendations

1. **Fix Crawler Worker**
   - Ensure Go crawler worker is running in AIO container
   - Or deploy separate crawler service

2. **Enable Search Result Caching**
   - Configure Redis caching with 1-hour TTL
   - Implement cache invalidation

3. **Add Monitoring**
   - Set up Grafana dashboard for crawl queue metrics
   - Alert when crawl queue is empty or not being processed

4. **Seed Initial Content**
   - Add 100-1000 high-quality URLs to crawl queue
   - Run initial crawl before production use

5. **Optimize Search Latency**
   - Current: 5.7 seconds (unacceptable)
   - Target: <500ms
   - Enable caching, reduce timeouts, implement streaming

---

## Contact & Support

- **Repository:** https://github.com/itxLikhith/intent-engine
- **Issues:** https://github.com/itxLikhith/intent-engine/issues
- **Email:** likhith.anony45@gmail.com

---

**Next Steps:**
1. ✅ Fix Go crawler worker (CRITICAL)
2. ✅ Verify crawling is happening
3. ✅ Test search returns results
4. ⚠️ Enable Redis caching for performance
5. ⚠️ Add monitoring and alerting
