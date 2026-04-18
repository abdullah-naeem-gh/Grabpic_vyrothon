# GrabPic Test Commands Cheatsheet

Quick reference for running the pytest test suite.

## Prerequisites

```bash
# Ensure Docker containers are running
docker compose up -d

# Install test dependencies in container (first time only)
docker exec grabpic_app pip install pytest pytest-asyncio httpx==0.25.2 pillow
```

## Run All Tests

```bash
# Run complete test suite
docker exec grabpic_app python -m pytest tests/ -v

# Run with less verbose output
docker exec grabpic_app python -m pytest tests/

# Run with test summary
docker exec grabpic_app python -m pytest tests/ -v --tb=short
```

## Run by Test File

```bash
# Ingestion tests (6 tests)
docker exec grabpic_app python -m pytest tests/test_ingest.py -v

# Authentication tests (9 tests)
docker exec grabpic_app python -m pytest tests/test_auth.py -v

# Image retrieval tests (8 tests)
docker exec grabpic_app python -m pytest tests/test_images.py -v
```

## Run Individual Tests

### Ingestion
```bash
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_empty_directory -v
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_valid_photos -v
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_idempotent -v
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_no_face_image -v
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_mixed_valid_invalid -v
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_default_photo_dir -v
```

### Authentication
```bash
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_no_face -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_multiple_faces -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_valid_selfie -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_unknown_face -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_wrong_format -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_no_file -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_large_file -v
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_after_multiple_ingests -v
```

### Images
```bash
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_valid -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_invalid_uuid -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_not_found -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_ordering -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_multiple_users -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_download_endpoint_exists -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_with_special_characters_in_uuid -v
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_case_sensitivity -v
```

## Run Multiple Specific Tests

```bash
# Run two tests
docker exec grabpic_app python -m pytest \
  tests/test_ingest.py::test_ingest_empty_directory \
  tests/test_auth.py::test_auth_wrong_format \
  -v

# Run all tests matching pattern
docker exec grabpic_app python -m pytest tests/ -k "invalid" -v
docker exec grabpic_app python -m pytest tests/ -k "auth" -v
docker exec grabpic_app python -m pytest tests/ -k "valid" -v
```

## Debugging

```bash
# Show print statements
docker exec grabpic_app python -m pytest tests/test_auth.py -v -s

# Show local variables on failure
docker exec grabpic_app python -m pytest tests/ -v -l

# Stop on first failure
docker exec grabpic_app python -m pytest tests/ -v -x

# Run last failed tests only
docker exec grabpic_app python -m pytest tests/ -v --lf

# Show full traceback
docker exec grabpic_app python -m pytest tests/ -v --tb=long
```

## Memory Management

If tests crash with exit code 137 (OOM):

```bash
# Restart container between test files
docker compose restart app
sleep 3
docker exec grabpic_app pip install -q pytest pytest-asyncio httpx==0.25.2 pillow
docker exec grabpic_app python -m pytest tests/test_ingest.py -v

docker compose restart app
sleep 3
docker exec grabpic_app pip install -q pytest pytest-asyncio httpx==0.25.2 pillow
docker exec grabpic_app python -m pytest tests/test_auth.py -v

# Or use the automated script
./run_tests.sh
```

## Test Statistics

```bash
# Show test durations
docker exec grabpic_app python -m pytest tests/ -v --durations=10

# Count tests
docker exec grabpic_app python -m pytest tests/ --collect-only

# Show coverage (if pytest-cov installed)
docker exec grabpic_app python -m pytest tests/ --cov=app --cov-report=term
```

## Running Locally (Outside Docker)

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests (uses .env.test with localhost)
pytest tests/ -v

# Specific test
pytest tests/test_ingest.py::test_ingest_empty_directory -v
```

## Continuous Integration

```bash
# One-liner for CI
docker compose up -d && \
docker exec grabpic_app pip install -q pytest pytest-asyncio httpx==0.25.2 pillow && \
docker exec grabpic_app python -m pytest tests/ -v --tb=short
```

## Quick Verification

Run these key tests to verify setup:

```bash
# Test 1: Basic ingestion
docker exec grabpic_app python -m pytest tests/test_ingest.py::test_ingest_empty_directory -v

# Test 2: Error handling
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_wrong_format -v

# Test 3: UUID validation
docker exec grabpic_app python -m pytest tests/test_images.py::test_get_images_invalid_uuid -v
```

All three should PASS ✓

## Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"
```bash
docker exec grabpic_app pip install pytest pytest-asyncio httpx==0.25.2 pillow
```

### "Could not connect to database"
```bash
docker compose up -d db
docker compose ps  # Verify db is healthy
```

### Container killed (exit 137)
```bash
# Increase Docker memory limit (Docker Desktop → Settings → Resources)
# Or run test files separately
```

### Tests hanging
```bash
# Ctrl+C to stop, then restart container
docker compose restart app
```

## Summary

**Most common commands:**

```bash
# Full test suite
docker exec grabpic_app python -m pytest tests/ -v

# Single file
docker exec grabpic_app python -m pytest tests/test_auth.py -v

# Single test
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_valid_selfie -v
```

**Test count:** 23 tests total
- test_ingest.py: 6 tests
- test_auth.py: 9 tests  
- test_images.py: 8 tests

Run `pytest tests/ -v` to execute all!
