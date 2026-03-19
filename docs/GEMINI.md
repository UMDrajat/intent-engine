# GEMINI.md - Intent Engine Project Context

## Project Overview
**Intent Engine** is a privacy-first, intent-driven search and advertising platform. It focuses on extracting structured user intent from natural language queries to provide relevant search results, service recommendations, and ethical ad matching without tracking or discriminatory targeting.

### Main Technologies
- **Core Backend:** Python 3.11+ (FastAPI, Pydantic, SQLAlchemy)
- **Machine Learning/NLP:** Transformers, Sentence-Transformers, PyTorch
- **Crawler & Indexer:** Go (Bleve search engine, BadgerDB, Colly)
- **Data Stores:** PostgreSQL (Main DB), Redis (Caching/Queues), Qdrant (Vector DB)
- **Infrastructure:** Docker, Docker Compose, PgBouncer, Nginx, Prometheus, Grafana
- **Background Tasks:** ARQ (Redis-based worker)

### Key Architectural Phases
1.  **Intent Extraction:** Converts free-form queries into structured `UniversalIntent` objects.
2.  **Constraint Satisfaction & Ranking:** Filters and ranks results based on user-defined constraints and semantic alignment.
3.  **Service Recommendation:** Matches intent to the most appropriate service providers.
4.  **Ad Matching:** Performs ethical, non-tracking ad matching with fairness validation.

---

## v3.0.0 - Advanced Optimizations & AI Re-ranking

### 1. Advanced Deduplication
- **Near-Duplicate Detection:** Implemented **SimHash** (64-bit fingerprints) with Hamming Distance thresholding to identify and filter visually similar results.
- **Content-Addressable Storage (CAS):** Raw HTML is now stored using SHA-256 content hashes. Multiple URLs pointing to the same content are stored only once on disk.

### 2. Asynchronous Intent Enrichment
- **Background Workers:** Moved heavy NLP intent extraction and embedding generation to an asynchronous Python **ARQ worker**.
- **Go-Python Bridge:** The Go indexer enqueues NLP tasks via Redis, which the Python worker processes and returns enriched metadata.

### 3. Semantic Re-ranking
- **Cross-Encoders:** Integrated `cross-encoder/ms-marco-MiniLM-L-6-v2` into the search pipeline.
- **Dynamic Sorting:** Top results from all sources (Go index, SearXNG, Vector) are re-scored by the Cross-Encoder for maximum relevance.

### 4. Dynamic JS Rendering
- **Playwright Integration:** Added background tasks to handle Single Page Applications (SPAs).
- **Hybrid Crawling:** Static crawler enqueues low-content pages for dynamic rendering by the Playwright worker.

---

## Getting Started (v3.0.0)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Go 1.24+ (for crawler development)

### Quick Start (Docker)
```bash
# Start all services
./scripts/production_start.sh start

# Verify API
curl http://localhost:8000/
```

### Local Development Setup
```bash
# Install Python dependencies
make dev

# Initialize Database
python scripts/init_db.py
python scripts/seed_data.py

# Run FastAPI Server
python -m uvicorn main_api:app --reload
```

---

## Development Commands

### Python (Backend)
- **Test:** `make test` or `pytest tests/`
- **Lint:** `make lint` (uses Ruff)
- **Format:** `make format` (uses Ruff)
- **Security Scan:** `make security` (uses Bandit and Safety)
- **Database Migrations:** `make migrations`

### Go (Crawler)
- **Build:** `cd go-crawler && make build`
- **Test:** `cd go-crawler && make test`
- **Lint:** `cd go-crawler && make lint`

### Docker Orchestration
- **Build & Start:** `make docker-run`
- **Stop:** `make docker-stop`
- **Clean:** `make docker-clean`

---

## Project Structure & Conventions

### Key Directories
- `core/`: Shared schemas (`UniversalIntent`) and utilities.
- `extraction/`: Intent extraction logic and programming error detection.
- `ranking/`: Constraint satisfaction and semantic ranking implementation.
- `go-crawler/`: Independent Go-based web crawling and indexing service.
- `searxng/`: Integration with SearXNG for privacy-preserving meta-search.
- `scripts/`: Extensive utility scripts for setup, seeding, and maintenance.

### Development Conventions
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/). Use `python commit-gen.py` for automated message generation.
- **Code Style:** PEP 8 compliant, enforced by **Ruff**. Line length is set to 120.
- **Testing:** Comprehensive test suite in `tests/`. New features must include tests.
- **Privacy:** Adhere to the privacy-first mandate—no persistent user tracking or PII storage in search logs.
- **Self-Improving Loop:** Search results are automatically fed back into the Go crawler queue for continuous indexing.

### Documentation Hub
- `INDEX.md`: Main entry point for all documentation.
- `docs/architecture/`: Detailed system design and whitepapers.
- `docs/getting-started/`: Comprehensive installation and production guides.
