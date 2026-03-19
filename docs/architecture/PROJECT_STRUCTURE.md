# Project Structure - Intent Engine

This document describes the professional, enterprise-grade project structure for the Intent Engine.

## Directory Layout

```
intent-engine/
├── app/                        # Python Core (Application Source)
│   ├── abtesting/              # A/B testing module
│   ├── ads/                    # Ad matching module
│   ├── analytics/              # Real-time analytics module
│   ├── audit/                  # Audit trail module
│   ├── config/                 # Configuration and Health checks
│   ├── core/                   # Core shared components (Schemas)
│   ├── demos/                  # Functional demos
│   ├── extraction/             # Intent extraction logic (NLP)
│   ├── fraud/                  # Fraud detection module
│   ├── privacy/                # Privacy compliance module
│   ├── ranking/                # Ranking and Scoring engines
│   ├── services/               # Service recommendation module
│   ├── tests/                  # Unified testing suite
│   ├── main_api.py             # FastAPI server implementation
│   ├── main.py                 # CLI entry point
│   ├── models.py               # Pydantic models for API
│   ├── database.py             # Database layer
│   └── worker.py               # ARQ worker entry point
├── go-crawler/                 # Go-based web crawler and indexer
├── infrastructure/             # Infrastructure & DevOps configuration
│   ├── compose/                # Docker Compose variants
│   ├── docker/                 # Dockerfiles and entrypoints
│   ├── database/               # SQL migrations and DB init
│   ├── monitoring/             # Prometheus & Grafana configs
│   ├── proxy/                  # PgBouncer & Nginx configs
│   └── lint/                   # Linting and pre-commit configs
├── scripts/                    # Maintenance and utility scripts
├── docs/                       # Comprehensive documentation
├── data/                       # Local data directory (git-ignored)
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── pyproject.toml              # Build system and tool configuration
├── Makefile                    # Development task automation
├── run.py                      # Main entry point (API/CLI/Worker)
└── README.md                   # Project entry point
```

## Module Descriptions (Python app/)

| Module | Description |
|--------|-------------|
| `app/core/` | Shared schemas (`UniversalIntent`), enums, and utilities |
| `app/extraction/` | Intent extraction from user queries using NLP models |
| `app/ranking/` | Constraint satisfaction and intent-aligned ranking |
| `app/services/` | Service recommendation based on intent matching |
| `app/ads/` | Ethical ad matching with fairness validation |
| `app/privacy/` | Consent management and privacy controls (GDPR) |
| `app/config/` | Type-safe Pydantic settings and Health check service |

## Infrastructure Layout

| Directory | Description |
|-----------|-------------|
| `infrastructure/compose/` | Docker Compose files for prod, dev, and CI |
| `infrastructure/docker/` | Production and AIO (All-In-One) Dockerfiles |
| `infrastructure/database/` | SQL migration files and initialization scripts |
| `infrastructure/monitoring/` | Prometheus, Grafana dashboards and provisioning |

## Getting Started

### Local Development

```bash
# Clone the repository
git clone git@github.com-work:itxLikhith/intent-engine.git
cd intent-engine

# Install dependencies
pip install -r requirements.txt

# Run the API locally via the wrapper
python run.py api
```

### Running with Docker

```bash
# Start all services using the centralized compose file
docker-compose -f infrastructure/compose/docker-compose.yml up -d

# View API logs
docker-compose -f infrastructure/compose/docker-compose.yml logs -f intent-engine-api
```

### Using Makefile

```bash
# Install dependencies
make install

# Run tests (points to app/tests)
make test

# Format code (uses Ruff)
make format

# Build and run Docker
make docker-run
```

## Architecture Overview

The Intent Engine follows a modular architecture with four main phases:

1. **Intent Extraction** - Converts free-form queries into structured intent objects
2. **Constraint Satisfaction & Ranking** - Filters and ranks results based on user intent
3. **Service Recommendation** - Routes users to the most appropriate service
4. **Ad Matching** - Matches ads without discriminatory targeting

## Conventions

- **Application Code**: Located in `app/`. All absolute imports use the `app.` prefix.
- **Entry Point**: Use `run.py` for all local execution tasks.
- **Configuration**: Managed via `app/config/settings.py` (Pydantic BaseSettings).
- **Health Checks**: Centralized in `app/config/health_checks.py`.
- **Infrastructure**: All DevOps/Ops files are in `infrastructure/`.
