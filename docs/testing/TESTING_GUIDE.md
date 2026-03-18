# Testing Guide

Quick reference for running tests in the Intent Engine project.

## Quick Start

```bash
# Run all tests
python -m pytest app/tests/

# Run all tests with verbose output
python -m pytest app/tests/ -v

# Run all tests with coverage report
python -m pytest app/tests/ --cov=app --cov-report=html
```

## Running Specific Tests

```bash
# Run specific test file
python -m pytest app/tests/test_extraction.py -v

# Run specific test class
python -m pytest app/tests/test_extraction.py::TestIntentExtractor -v
```

## Coverage Reports

```bash
# Generate HTML coverage report
python -m pytest app/tests/ --cov=app --cov-report=html

# Open coverage report
start docs/coverage/index.html  # Reorganized path
```

## Test Structure

Tests are located in `app/tests/` to align with the modular package structure.

```
app/tests/
├── __init__.py
├── api_integration_test.py
├── comprehensive_test.py
├── test_ads.py
├── test_advertising_api.py
├── test_extraction.py
├── test_ranking.py
├── test_services.py
├── test_url_ranking.py
└── test_url_ranking_api.py
```

## Using Makefile

The easiest way to run tests is via the provided Makefile:

```bash
make test        # Run all tests
make test-cov    # Run tests with coverage
```
