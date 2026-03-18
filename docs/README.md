# Intent Engine Documentation

Welcome to the Intent Engine documentation hub. This directory contains comprehensive guides, reports, and technical documentation.

---

## 📚 Documentation Categories

### 🚀 Getting Started

- **[README.md](../README.md)** - Main project overview and quick start guide
- **[INDEX.md](../INDEX.md)** - Project index and navigation
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

---

### 📊 Test Reports

| Document | Description | Date |
|----------|-------------|------|
| **[AIO_FINAL_TEST_REPORT.md](AIO_FINAL_TEST_REPORT.md)** | Complete AIO container test results with automatic crawler | March 19, 2026 |
| **[FINAL_API_TEST_REPORT.md](FINAL_API_TEST_REPORT.md)** | API endpoint test results (100% passing) | March 19, 2026 |
| **[BENCHMARK_REPORT_MARCH_19.md](BENCHMARK_REPORT_MARCH_19.md)** | Load testing and performance benchmarks | March 19, 2026 |
| **[FINAL_TEST_RESULTS.md](FINAL_TEST_RESULTS.md)** | Initial comprehensive test results | March 19, 2026 |

---

### 🐛 Bug Fixes & Issues

| Document | Description | Date |
|----------|-------------|------|
| **[BUGFIXES_MARCH_19.md](BUGFIXES_MARCH_19.md)** | Summary of all bug fixes implemented | March 19, 2026 |
| **[FINDINGS_AND_FIX.md](FINDINGS_AND_FIX.md)** | Root cause analysis and solutions | March 19, 2026 |

---

### ⚡ Performance Optimization

| Document | Description | Date |
|----------|-------------|------|
| **[SEARCH_LATENCY_OPTIMIZATION.md](SEARCH_LATENCY_OPTIMIZATION.md)** | Comprehensive latency optimization guide | March 19, 2026 |
| **[LATENCY_OPTIMIZATION_SUMMARY.md](LATENCY_OPTIMIZATION_SUMMARY.md)** | Implementation summary and results | March 19, 2026 |
| **[COLD_START_GUIDE.md](COLD_START_GUIDE.md)** | Cold start troubleshooting and solutions | March 19, 2026 |

---

### 🔧 Configuration & Deployment

| Document | Description | Date |
|----------|-------------|------|
| **[AIO_OPTIONAL_SERVICES.md](AIO_OPTIONAL_SERVICES.md)** | AIO container optional services configuration | March 19, 2026 |

---

## 📋 Quick Reference

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check endpoint |
| `POST /search` | Unified search with intent extraction |
| `POST /extract-intent` | Extract intent from text |
| `POST /rank-results` | Rank search results by intent |
| `POST /recommend-services` | Service recommendations |
| `POST /match-ads` | Ad matching based on intent |

### Common Commands

```bash
# Start AIO container
docker-compose -f infrastructure/compose/docker-compose.aio.yml up -d

# View container logs
docker logs -f intent-engine-aio

# Check crawler status
docker exec intent-engine-aio psql -U intent_user -d intent_engine -c "SELECT COUNT(*) FROM crawled_pages;"

# Run test suite
python test_api_benchmark.py
```

### Default Ports

| Service | Port |
|---------|------|
| API (nginx) | 80 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| SearXNG | 8080 |
| Go Search API | 8081 |
| Go Unified Search | 8082 |
| Qdrant | 6333 |

---

## 🔗 External Resources

- [Python Documentation](https://docs.python.org/)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SearXNG Documentation](https://docs.searxng.org/)

---

## 📞 Support

For issues and questions:
- **GitHub Issues:** [Create an issue](https://github.com/your-org/intent-engine/issues)
- **Documentation:** Check this docs directory first
- **API Reference:** See [README.md](../README.md#api-endpoints)

---

**Last Updated:** March 19, 2026  
**Documentation Status:** ✅ Complete
