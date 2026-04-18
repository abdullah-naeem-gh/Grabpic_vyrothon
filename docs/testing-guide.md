# GrabPic Testing Guide

Complete guide for running the pytest test suite for GrabPic.

## Overview

The test suite provides comprehensive coverage of all API endpoints:
- **test_ingest.py**: Tests for image ingestion from directories
- **test_auth.py**: Tests for selfie authentication
- **test_images.py**: Tests for image retrieval by grab_id

## Quick Start

### Run all tests (recommended method)

```bash
# Inside Docker container (recommended)
docker exec grabpic_app python -m pytest tests/ -v

# Or use the test runner script
chmod +x run_tests.sh
./run_tests.sh
```

### Run specific test files

```bash
# Test ingestion
docker exec grabpic_app python -m pytest tests/test_ingest.py -v

# Test authentication
docker exec grabpic_app python -m pytest tests/test_auth.py -v

# Test image retrieval
docker exec grabpic_app python -m pytest tests/test_images.py -v
```

### Run individual tests

```bash
docker exec grabpic_app python -m pytest tests/test_auth.py::test_auth_valid_selfie -v
```

## Prerequisites

### 1. Database Running

Ensure PostgreSQL with pgvector is running:

```bash
docker compose up -d db
```

Verify database is healthy:

```bash
docker compose ps
```

### 2. Application Container

Start the application container:

```bash
docker compose up -d app
```

### 3. Test Dependencies

Install test dependencies in the container:

```bash
docker exec grabpic_app pip install pytest pytest-asyncio httpx==0.25.2 pillow
```

**Note**: These dependencies are already specified in `requirements.txt` and will be installed automatically if you rebuild the container.

## Test Structure

### Fixtures (tests/conftest.py)

The test suite uses pytest fixtures for setup and teardown:

- **test_client**: FastAPI TestClient for making HTTP requests
- **sample_image_path**: Path to real test image (person1.jpg or similar)
- **sample_image_path_2**: Path to second test image (for multi-user tests)
- **clean_db**: Truncates all database tables before each test
- **temp_empty_dir**: Temporary empty directory for testing
- **photos_dir**: Path to the photos/ directory

### Test Data

Tests use **real images** from the `photos/` directory:
- `person1.jpg`, `person2.jpg`, `person5.jpg`, `person6.jpg`: Real face photos
- The test suite automatically identifies valid images (> 1KB)
- Some files in photos/ may be placeholder text files and are skipped

## Test Coverage

### tests/test_ingest.py (6 tests)

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_ingest_empty_directory` | Ingest empty directory | 200, processed=0 |
| `test_ingest_valid_photos` | Ingest real photos | 200, faces_found > 0 |
| `test_ingest_idempotent` | Run ingestion twice | Second run: skipped = first run processed |
| `test_ingest_no_face_image` | Ingest image with no face | 200, no 500 error |
| `test_ingest_mixed_valid_invalid` | Mix of valid/invalid files | 200, handles gracefully |
| `test_ingest_default_photo_dir` | Use default config dir | 200, uses PHOTO_DIR from config |

### tests/test_auth.py (9 tests)

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_auth_no_face` | Upload blank image | 400 Bad Request |
| `test_auth_multiple_faces` | Upload group photo | 400 Bad Request |
| `test_auth_valid_selfie` | Full auth flow | 200, valid grab_id |
| `test_auth_unknown_face` | Face not in DB | 401 Unauthorized |
| `test_auth_wrong_format` | Upload text file | 415 Unsupported Media Type |
| `test_auth_no_file` | Missing file | 422 Validation Error |
| `test_auth_large_file` | File > 10MB | 413 Payload Too Large |
| `test_auth_after_multiple_ingests` | Auth after 2x ingest | 200, still works |

### tests/test_images.py (8 tests)

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_get_images_valid` | Full flow: ingest → auth → fetch | 200, images list |
| `test_get_images_invalid_uuid` | Invalid UUID format | 400 Bad Request |
| `test_get_images_not_found` | Random valid UUID | 404 Not Found |
| `test_get_images_ordering` | Images ordered by confidence | 200, proper ordering |
| `test_get_images_multiple_users` | User isolation | Each user sees only their images |
| `test_get_images_download_endpoint_exists` | Download ZIP endpoint | 200 or 404 |
| `test_get_images_with_special_characters_in_uuid` | Security check | 400 Bad Request |
| `test_get_images_case_sensitivity` | UUID case handling | Works with upper/lower |

## Memory Considerations

DeepFace loads large neural network models which can consume significant memory. If tests fail with exit code 137 (OOM killed):

### Solutions:

1. **Run test files separately** (recommended):
   ```bash
   docker exec grabpic_app python -m pytest tests/test_ingest.py -v
   docker compose restart app
   docker exec grabpic_app python -m pytest tests/test_auth.py -v
   docker compose restart app
   docker exec grabpic_app python -m pytest tests/test_images.py -v
   ```

2. **Increase Docker memory limit**:
   - Docker Desktop → Settings → Resources → Memory
   - Increase to 8GB or more

3. **Use the test runner script** which handles restarts automatically:
   ```bash
   ./run_tests.sh
   ```

## Running Tests Locally (Outside Docker)

If you prefer to run tests on your local machine:

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Update `.env.test` to use `localhost` instead of `db`:
   ```bash
   DATABASE_URL=postgresql://postgres:password@localhost:5432/grabpic
   PHOTO_DIR=/Users/your_username/Projects/GrabPic_Vyrothon/photos
   ```

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

**Note**: The conftest.py automatically detects whether tests are running inside Docker or locally and adjusts the database connection accordingly.

## Troubleshooting

### Issue: "Could not connect to database"

**Solution**: Ensure PostgreSQL container is running:
```bash
docker compose up -d db
docker compose ps
```

### Issue: "ModuleNotFoundError: No module named 'pytest'"

**Solution**: Install test dependencies:
```bash
docker exec grabpic_app pip install pytest pytest-asyncio httpx==0.25.2 pillow
```

### Issue: Container killed (exit code 137)

**Solution**: Out of memory. Run tests one file at a time or increase Docker memory limit.

### Issue: "DeepFace model download errors"

**Solution**: 
- Ensure internet connectivity
- First run may take time to download models (~500MB)
- Models are cached after first download

### Issue: "httpx version conflict"

**Solution**: Use httpx 0.25.2 specifically:
```bash
docker exec grabpic_app pip install "httpx==0.25.2"
```

## CI/CD Integration

For automated testing in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    docker compose up -d
    docker exec grabpic_app pip install pytest pytest-asyncio httpx==0.25.2 pillow
    docker exec grabpic_app python -m pytest tests/ -v
```

## Best Practices

1. **Always use `clean_db` fixture** for tests that modify the database
2. **Use real test images** from photos/ directory for authentic testing
3. **Test error cases** as well as happy paths
4. **Verify response structure** (keys, types, values)
5. **Test edge cases** (empty, invalid, malformed inputs)
6. **Keep tests independent** - each test should work in isolation

## Adding New Tests

To add new tests:

1. Create test function in appropriate file (test_*.py)
2. Use `test_client` fixture for HTTP requests
3. Use `clean_db` fixture if modifying database
4. Follow naming convention: `test_<feature>_<scenario>`
5. Add docstring explaining what the test verifies
6. Use appropriate assertions for status codes and response data

Example:

```python
def test_new_feature(test_client, clean_db):
    """
    Test description of what this verifies.
    """
    response = test_client.post("/endpoint", json={"data": "value"})
    
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

## Test Metrics

- **Total tests**: 23
- **Test files**: 3
- **Coverage areas**: Ingestion, Authentication, Image Retrieval
- **Test types**: Unit, Integration, Edge Cases, Security

## Performance

- Simple tests (no DeepFace): < 1 second
- Tests with face detection: 5-30 seconds
- Full test suite: 2-5 minutes (depending on memory/CPU)

## Summary

The test suite provides comprehensive coverage of:
- ✅ Happy path flows (ingest → auth → fetch images)
- ✅ Error handling (400, 401, 404, 413, 415, 422, 500)
- ✅ Edge cases (empty dirs, no faces, unknown faces)
- ✅ Security (SQL injection, XSS attempts, malformed UUIDs)
- ✅ Idempotency (repeated operations)
- ✅ Data isolation (multi-user scenarios)

Run `pytest tests/ -v` to execute the full suite!
