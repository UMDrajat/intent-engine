# Version References - Intent Engine

**Last Updated:** March 18, 2026  
**Current Version:** v2.3.0

This document tracks all locations where the version number appears in the codebase.

---

## Primary Version Files

### `__version__.py`
```python
__version__ = "2.3.0"
__version_info__ = (2, 0, 0)
__version_description__ = "Configuration & Health Improvements"
```

### `pyproject.toml`
```toml
[project]
name = "intent-engine"
version = "2.3.0"
```

---

## Documentation Files

### Root Documentation
- `README.md` - Version badge and "Latest Release" section
- `INDEX.md` - Header with version and date
- `CHANGELOG.md` - Version history (created v2.3.0)
- `IMPROVEMENTS.md` - v2.3.0 summary document
- `CONTRIBUTING.md` - References current version

### Architecture Documentation
- `docs/architecture/PROJECT_OVERVIEW.md` - Version header
- `docs/architecture/PROJECT_STRUCTURE.md` - Version references
- `docs/architecture/SELF_IMPROVING_LOOP.md` - Version context
- `docs/architecture/Intent-Engine-Whitepaper.md` - Version info

### Getting Started Documentation
- `docs/getting-started/QUICKSTART.md` - Version header
- `docs/getting-started/README_PRODUCTION.md` - Version references
- `docs/getting-started/README_PRODUCTION_FULL.md` - Version info
- `docs/getting-started/QUICK_REFERENCE.md` - Version context
- `docs/getting-started/PHASE1_README.md` - Historical version

### Deployment Documentation
- `docs/deployment/DEPLOYMENT_CHECKLIST.md` - Version header
- `docs/deployment/PERFORMANCE_OPTIMIZATION_PLAN.md` - Version context
- `docs/deployment/IMPLEMENTATION_GUIDE.md` - Version references
- `docs/deployment/CI_IMPROVEMENTS.md` - Version info
- `docs/deployment/RELEASE_AUTOMATION.md` - Version automation

### Go Crawler Documentation
- `docs/go-crawler/README.md` - Version references
- `docs/go-crawler/QUICKSTART.md` - Version info
- `docs/go-crawler/GO_CRAWLER_SETUP_GUIDE.md` - Version context
- `docs/go-crawler/README_PRODUCTION.md` - Version references

### Reference Documentation
- `docs/reference/VERSIONING_AND_RELEASES.md` - Version policy
- `docs/reference/VERSIONING.md` - Version management
- `docs/reference/Intent-Engine-Tech-Reference.md` - Version info
- `docs/reference/Intent-Engine-Visual-Guide.md` - Version context
- `docs/reference/CONFIGURATION_CHANGES.md` - Version changes

### Testing Documentation
- `docs/testing/TESTING_GUIDE.md` - Version references
- `docs/testing/TESTING_PLAN.md` - Version context
- `docs/testing/STRESS_TEST_ANALYSIS.md` - Version info

---

## Update Checklist for New Versions

### Before Release

- [ ] Update `__version__.py`:
  - `__version__` string
  - `__version_info__` tuple
  - `__version_description__`

- [ ] Update `pyproject.toml`:
  - `version` field

- [ ] Update `CHANGELOG.md`:
  - Add new version section
  - Document all changes
  - Update version history

- [ ] Update `README.md`:
  - Version badge
  - "Latest Release" section
  - "What's New" section

### Documentation Updates

- [ ] Update `INDEX.md`:
  - Version header
  - "What's New" section

- [ ] Update `docs/architecture/PROJECT_OVERVIEW.md`:
  - Version header
  - Key features section

- [ ] Update `docs/getting-started/QUICKSTART.md`:
  - Version header
  - Any version-specific instructions

- [ ] Update `docs/deployment/DEPLOYMENT_CHECKLIST.md`:
  - Version header
  - Version-specific deployment notes

### Automated Updates

The following files are automatically updated by Commitizen during release:
- `pyproject.toml` (version field)
- `__version__.py` (via version_files in pyproject.toml)
- `README.md` (version badges)
- `CHANGELOG.md` (auto-generated)

### Manual Updates Required

These files require manual updates:
- `INDEX.md`
- `docs/architecture/PROJECT_OVERVIEW.md`
- `docs/getting-started/QUICKSTART.md`
- `docs/deployment/DEPLOYMENT_CHECKLIST.md`
- `IMPROVEMENTS.md` (for major releases)

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2.3.0 | 2026-03-18 | Configuration & Health Improvements |
| 2.2.2 | 2026-03-16 | Integration Test Fixes |
| 2.2.1 | 2026-03-15 | Linting and Test Improvements |
| 2.2.0 | 2026-03-14 | Hybrid Scraping Pipeline |
| 2.1.2 | 2026-03-13 | Performance Optimizations |
| 2.1.1 | 2026-03-12 | Self-Improving Search Loop |
| 2.1.0 | 2026-03-10 | Query Router Implementation |
| 2.0.0 | 2026-03-08 | Federated Search (Go Crawler) |
| 1.5.0 | 2026-03-05 | SearXNG Integration |
| 1.0.0 | 2026-03-01 | Initial Release |

---

## Version Numbering Policy

The Intent Engine uses **Semantic Versioning** (SemVer):

**Format:** `MAJOR.MINOR.PATCH`

- **MAJOR** version for incompatible changes
- **MINOR** version for backwards-compatible features
- **PATCH** version for backwards-compatible bug fixes

**Examples:**
- `2.3.0` → `2.3.1` (patch: bug fix)
- `2.3.0` → `2.4.0` (minor: new feature)
- `2.3.0` → `3.0.0` (major: breaking change)

---

## Docker Image Tags

Docker images are tagged with version numbers:

```bash
# Latest version
docker pull anony45/intent-engine-api:latest

# Specific version
docker pull anony45/intent-engine-api:2.3.0

# Major version
docker pull anony45/intent-engine-api:2
```

---

## API Versioning

API endpoints use versioning for breaking changes:

```python
# Current API version (v1)
@app.post("/v1/search")
async def search_v1():
    pass

# Legacy endpoints (no version prefix)
@app.post("/search")
async def search_legacy():
    pass
```

**Current API Version:** v1 (implicit)

---

## Checking Version

### From Python
```python
from __version__ import __version__
print(f"Intent Engine version: {__version__}")
```

### From API
```bash
curl http://localhost:8000/status | jq .version
```

### From Docker
```bash
docker run anony45/intent-engine-api:latest python -c "from __version__ import __version__; print(__version__)"
```

### From Git
```bash
git describe --tags --always
# Output: v2.3.0
```
