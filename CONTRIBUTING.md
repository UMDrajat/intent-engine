# Contributing to Intent Engine

Thank you for your interest in contributing to Intent Engine! This guide will help you get started and make your first contribution.

## 🚀 Quick Start: Your First PR in 10 Minutes

Want to make a quick contribution? Follow these steps:

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/intent-engine.git
cd intent-engine

# 2. Set up your development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

# 3. Find a good first issue
# Visit: https://github.com/itxLikhith/intent-engine/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22

# 4. Create a branch for your fix
git checkout -b fix/issue-123-short-description

# 5. Make your changes and run tests
pytest tests/ -v

# 6. Commit using conventional commits
python scripts/commit-gen.py

# 7. Push and create PR
git push origin fix/issue-123-short-description
```

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Docker Development Setup](#docker-development-setup)
- [Development Workflow](#development-workflow)
  - [Branch Strategy](#branch-strategy)
  - [Commit Messages](#commit-messages)
  - [Code Quality](#code-quality)
- [Testing](#testing)
  - [Running Tests](#running-tests)
  - [Test Coverage](#test-coverage)
  - [Load Testing](#load-testing)
- [Pull Requests](#pull-requests)
  - [PR Checklist](#pr-checklist)
  - [Review Process](#review-process)
- [Code Ownership](#code-ownership)
- [Getting Help](#getting-help)

---

## Code of Conduct

Please be respectful and constructive in your interactions. We're committed to providing a welcoming and inspiring community for all.

---

## Getting Started

### Prerequisites

**Required:**
- Python 3.11 or higher
- Git
- Docker & Docker Compose (for containerized development)
- 4GB+ RAM available
- 2GB+ disk space

**Recommended:**
- PostgreSQL 15+ (or use Docker)
- Redis/Valkey 8+ (or use Docker)
- Make (for convenience commands)

### Local Development Setup

#### 1. Clone the Repository

```bash
# Fork the repository first, then clone your fork
git clone https://github.com/YOUR_USERNAME/intent-engine.git
cd intent-engine
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install production dependencies
make install

# Install development dependencies (includes pre-commit hooks)
make dev
```

#### 4. Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Review and customize settings (optional for local dev)
# Most defaults work fine for local development
```

#### 5. Initialize Database

```bash
# Start PostgreSQL and Redis via Docker
docker-compose up -d postgres redis

# Wait for services to start
sleep 10

# Run database migrations
python scripts/init_db_standalone.py
```

#### 6. Start the API Server

```bash
# Development mode with hot reload
python -m uvicorn main_api:app --host 0.0.0.0 --port 8000 --reload

# Or use the Makefile
make docker-run  # Starts all services via Docker
```

#### 7. Verify Setup

```bash
# Test the API
curl http://localhost:8000/

# Run the test suite
make test
```

### Docker Development Setup

For a fully containerized development environment:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f intent-engine-api

# Run tests inside container
docker-compose exec intent-engine-api pytest tests/ -v

# Stop all services
docker-compose down
```

---

## Development Workflow

### Branch Strategy

We use a simplified branching model:

```
main
  └── feature/your-feature-name
  └── fix/issue-123-bug-description
  └── docs/update-readme
  └── refactor/improve-performance
```

**Branch Naming Conventions:**

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New features | `feature/add-vector-search` |
| `fix/` | Bug fixes | `fix/ranking-constraint-issue` |
| `docs/` | Documentation | `docs/update-api-examples` |
| `refactor/` | Code refactoring | `refactor/extract-search-service` |
| `perf/` | Performance improvements | `perf/optimize-embedding-cache` |
| `test/` | Test additions | `test/add-fraud-detection-tests` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |

**Workflow:**

1. **Create branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** in small, focused commits

3. **Keep branch updated** with main:
   ```bash
   git fetch origin main
   git rebase origin/main
   ```

4. **Push your branch:**
   ```bash
   git push -u origin feature/your-feature-name
   ```

### Commit Messages

We use **Conventional Commits** for clear, automated changelog generation.

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature (triggers MINOR version bump)
- `fix:` - Bug fix (triggers PATCH version bump)
- `docs:` - Documentation only
- `style:` - Formatting, no code change
- `refactor:` - Code restructuring
- `perf:` - Performance improvement
- `test:` - Adding tests
- `chore:` - Maintenance tasks
- `ci:` - CI configuration

**Examples:**
```bash
feat: add query router for federated search

Implemented intent-based backend selection with support for
Go Crawler, SearXNG, and Vector search backends.

Closes #45

fix(ranking): resolve constraint satisfaction issue

Fixed bug where range constraints (0-500) were not properly
parsed when price appeared before product name.

docs: update API documentation

Added examples for all endpoint responses.
Clarified authentication requirements.
```

**Tools:**
```bash
# Auto-generate commit message from changes
python scripts/commit-gen.py

# Interactive commit wizard
pip install commitizen
cz commit
```

### Code Quality

We maintain high code quality through automated checks:

**Pre-commit Hooks** (installed automatically):
- Commitizen (commit message validation)
- Ruff (linting + formatting + import sorting)
- Merge conflict checks
- File format validation (JSON, YAML, TOML)
- Security scans (Bandit, Safety)
- SQL linting (migrations)

**Manual Checks:**
```bash
# Run all checks
make check

# Linting only
make lint

# Format code
make format

# Security scans
make security
```

**Ruff Configuration** (in `pyproject.toml`):
- Line length: 120 characters
- Target version: Python 3.11
- Rules: E, W, F, I, UP, B, C4

---

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_extraction.py -v

# Run tests by marker
pytest -m "unit" tests/
pytest -m "integration" tests/
pytest -m "slow" tests/

# Run tests in parallel
pytest -n auto tests/

# Run tests on file changes
make test-watch
```

**Test Markers:**
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.slow` - Slow tests (skip with `-m "not slow"`)
- `@pytest.mark.e2e` - End-to-end tests

### Test Coverage

```bash
# Run with coverage report
make test-cov

# View HTML coverage report
open htmlcov/index.html  # Linux: xdg-open htmlcov/index.html

# Coverage target: >80%
```

**Coverage Configuration** (in `pyproject.toml`):
- Source: All project directories
- Omit: Tests, venv, migrations, `__init__.py`
- Target: >80% coverage

### Load Testing

```bash
# Install locust
pip install locust

# Start load testing
cd load_testing
locust -f locustfile.py

# Open web UI: http://localhost:8089
```

**Performance Targets:**
- Warm-up time: <100ms
- Processing time: <50ms per query
- Concurrent requests: 1000+/sec (with Redis)
- Cache hit rate: >80%

---

## Pull Requests

### PR Checklist

Before submitting your PR, ensure:

**Code Quality:**
- [ ] Code follows project style guidelines (Ruff)
- [ ] No linting errors (`make lint`)
- [ ] Code is formatted (`make format`)
- [ ] No security vulnerabilities (`make security`)

**Testing:**
- [ ] Tests added/updated for changes
- [ ] All tests pass (`make test`)
- [ ] Coverage maintained (>80%)
- [ ] Load tests considered (if performance-impacting)

**Documentation:**
- [ ] Docstrings added for public methods
- [ ] README updated (if user-facing change)
- [ ] API docs updated (if endpoint changed)
- [ ] Changelog entry added (if applicable)

**Commit Quality:**
- [ ] Commits follow Conventional Commits
- [ ] Commit messages are clear and descriptive
- [ ] Branch is rebased on main
- [ ] No merge conflicts

**Code Review:**
- [ ] Self-review completed
- [ ] Code is DRY (Don't Repeat Yourself)
- [ ] Error handling is appropriate
- [ ] Logging is adequate
- [ ] No hardcoded values (use settings)

### PR Template

When creating a PR, use this template:

```markdown
## Description
Brief description of changes (1-2 sentences)

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Related Issues
Closes #<issue_number>

## Testing Done
Describe testing performed:
- Unit tests added/updated
- Integration tests run
- Manual testing steps

## Checklist
- [ ] Code follows project guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Coverage maintained

## Screenshots (if applicable)
Add screenshots of UI changes or API response examples.

## Deployment Notes
Any special deployment considerations or migration steps.
```

### Review Process

1. **Automated Checks:**
   - CI/CD pipeline runs
   - Tests execute
   - Linting passes
   - Security scans complete

2. **Code Review:**
   - Maintainer reviews code
   - Feedback provided within 48 hours
   - Address review comments
   - Re-request review

3. **Approval:**
   - At least 1 maintainer approval required
   - All automated checks must pass
   - No unresolved comments

4. **Merge:**
   - Squash and merge (for feature branches)
   - Rebase and merge (for simple fixes)
   - Delete branch after merge

**Review Response Time:**
- Small PRs (<100 lines): 24-48 hours
- Medium PRs (100-500 lines): 48-72 hours
- Large PRs (>500 lines): Consider splitting

---

## Code Ownership

**Core Maintainers:**
- [@itxLikhith](https://github.com/itxLikhith) - Project Lead, Architecture
- [Contact: likhith.anony45@gmail.com]

**Module Owners:**
| Module | Owner | Backup |
|--------|-------|--------|
| Core API | @itxLikhith | TBD |
| Intent Extraction | TBD | TBD |
| Search & Ranking | TBD | TBD |
| Ad Matching | TBD | TBD |
| Privacy & Compliance | TBD | TBD |
| Infrastructure | @itxLikhith | TBD |

*Interested in owning a module? Reach out!*

---

## Getting Help

**Resources:**
- [Documentation](docs/)
- [Architecture Overview](docs/architecture/PROJECT_OVERVIEW.md)
- [API Documentation](http://localhost:8000/docs)
- [Existing Issues](https://github.com/itxLikhith/intent-engine/issues)

**Communication:**
- GitHub Issues: For bug reports and feature requests
- Email: likhith.anony45@gmail.com
- Discussions: [GitHub Discussions](https://github.com/itxLikhith/intent-engine/discussions)

**Good First Issues:**
Look for issues labeled:
- `good first issue` - Perfect for newcomers
- `help wanted` - Need community help
- `documentation` - Improve docs
- `tests` - Add test coverage

---

## License

By contributing, you agree that your contributions will be licensed under the [Intent Engine Community License (IECL) v1.0](LICENSE).

For commercial use, contact: anony45.omnipresent@proton.me

---

## Thank You!

Your contributions make Intent Engine better for everyone. We appreciate your time and effort!

**Happy coding! 🚀**
