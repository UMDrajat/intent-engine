# Test Script for Docker Compose Fixes

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Intent Engine - Docker Compose Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check container status
Write-Host "1. Checking container status..." -ForegroundColor Yellow
docker-compose ps
Write-Host ""

# Test 2: Test core services
Write-Host "2. Testing core services..." -ForegroundColor Yellow

# Test Redis
Write-Host "   Testing Redis..." -NoNewline
$redisTest = docker exec intent-engine-redis valkey-cli ping 2>$null
if ($redisTest -eq "PONG") {
    Write-Host " ✓ PASS" -ForegroundColor Green
} else {
    Write-Host " ✗ FAIL" -ForegroundColor Red
}

# Test PostgreSQL
Write-Host "   Testing PostgreSQL..." -NoNewline
$dbTest = docker exec intent-engine-postgres pg_isready -U intent_user -d intent_engine 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✓ PASS" -ForegroundColor Green
} else {
    Write-Host " ✗ FAIL" -ForegroundColor Red
}

# Test Qdrant
Write-Host "   Testing Qdrant..." -NoNewline
$qdrantTest = curl -s http://localhost:6333/ | Select-String -Pattern "qdrant"
if ($qdrantTest) {
    Write-Host " ✓ PASS" -ForegroundColor Green
} else {
    Write-Host " ✗ FAIL" -ForegroundColor Red
}

# Test SearXNG
Write-Host "   Testing SearXNG..." -NoNewline
$searxngTest = curl -s http://localhost:8080/healthz
if ($searxngTest -eq "OK") {
    Write-Host " ✓ PASS" -ForegroundColor Green
} else {
    Write-Host " ✗ FAIL (Response: $searxngTest)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Test API endpoints
Write-Host "3. Testing API endpoints..." -ForegroundColor Yellow

# Test API health
Write-Host "   Testing API health..." -NoNewline
$apiHealth = curl -s http://localhost:8000/health
if ($apiHealth -match '"status"') {
    Write-Host " ✓ PASS" -ForegroundColor Green
    Write-Host "      Response: $apiHealth" -ForegroundColor Gray
} else {
    Write-Host " ✗ FAIL" -ForegroundColor Red
}

# Test API liveness
Write-Host "   Testing API liveness..." -NoNewline
$apiLive = curl -s http://localhost:8000/health/live
if ($apiLive -match '"status":"alive"') {
    Write-Host " ✓ PASS" -ForegroundColor Green
} else {
    Write-Host " ✗ FAIL" -ForegroundColor Red
}

Write-Host ""

# Test 4: Test search functionality
Write-Host "4. Testing search functionality..." -ForegroundColor Yellow

Write-Host "   Testing search endpoint (cached query)..." -NoNewline
$startTime = Get-Date
$searchResult = curl -s -X POST "http://localhost:8000/search" `
    -H "Content-Type: application/json" `
    -d '{"query": "how to install python", "max_results": 5}' `
    -TimeoutSec 30
$endTime = Get-Date
$duration = ($endTime - $startTime).TotalMilliseconds

if ($searchResult -match '"results"') {
    Write-Host " ✓ PASS (${duration}ms)" -ForegroundColor Green
    # Extract result count
    $resultCount = ($searchResult | ConvertFrom-Json).results.Count
    Write-Host "      Results: $resultCount items" -ForegroundColor Gray
} else {
    Write-Host " ✗ FAIL or TIMEOUT" -ForegroundColor Red
    if ($searchResult) {
        Write-Host "      Response: $searchResult" -ForegroundColor Gray
    }
}

Write-Host ""

# Test 5: Test embedding cache (repeat query should be faster)
Write-Host "5. Testing embedding cache (repeat query)..." -ForegroundColor Yellow

Write-Host "   First query (cache miss)..." -NoNewline
$startTime = Get-Date
$searchResult1 = curl -s -X POST "http://localhost:8000/search" `
    -H "Content-Type: application/json" `
    -d '{"query": "python tutorial for beginners", "max_results": 3}' `
    -TimeoutSec 30
$endTime = Get-Date
$duration1 = ($endTime - $startTime).TotalMilliseconds
Write-Host "${duration1}ms" -ForegroundColor Cyan

Write-Host "   Second query (cache hit)..." -NoNewline
$startTime = Get-Date
$searchResult2 = curl -s -X POST "http://localhost:8000/search" `
    -H "Content-Type: application/json" `
    -d '{"query": "python tutorial for beginners", "max_results": 3}' `
    -TimeoutSec 30
$endTime = Get-Date
$duration2 = ($endTime - $startTime).TotalMilliseconds
Write-Host "${duration2}ms" -ForegroundColor Green

if ($duration2 -lt $duration1) {
    $improvement = [math]::Round((($duration1 - $duration2) / $duration1) * 100, 1)
    Write-Host "   Cache improvement: ${improvement}% faster" -ForegroundColor Green
}

Write-Host ""

# Test 6: Check API logs for embedding cache warmup
Write-Host "6. Checking embedding cache warmup..." -ForegroundColor Yellow
$cacheLogs = docker logs intent-engine-api 2>&1 | Select-String -Pattern "embedding|cache" -CaseSensitive:$false | Select-Object -Last 5
if ($cacheLogs) {
    Write-Host "   Found cache-related logs:" -ForegroundColor Green
    $cacheLogs | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
} else {
    Write-Host "   No cache logs found (may be normal)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
