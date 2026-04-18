# GrabPic Test Suite

Comprehensive test suite for GrabPic facial recognition backend using pytest and real test images.

## Setup

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure PostgreSQL database is running:
```bash
docker-compose up -d postgres
```

3. Set up environment variables (copy from `.env.example`):
```bash
cp .env.example .env
```

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_ingest.py -v
pytest tests/test_auth.py -v
pytest tests/test_images.py -v
```

### Run specific test
```bash
pytest tests/test_auth.py::test_auth_valid_selfie -v
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html -v
```

### Run in parallel (faster)
```bash
pytest tests/ -v -n auto
```

## Test Structure

### `tests/conftest.py`
Contains shared fixtures:
- `test_client`: FastAPI TestClient instance
- `sample_image_path`: Path to real test image from photos/ directory
- `sample_image_path_2`: Path to second test image (different person)
- `clean_db`: Truncates all database tables before each test
- `temp_empty_dir`: Temporary empty directory for testing
- `photos_dir`: Path to photos/ directory

### `tests/test_ingest.py`
Tests for the `/ingest` endpoint:
- `test_ingest_empty_directory`: Ingesting empty directory returns processed=0
- `test_ingest_valid_photos`: Successfully processes photos and finds faces
- `test_ingest_idempotent`: Second run skips already processed images
- `test_ingest_no_face_image`: Handles images without faces gracefully
- `test_ingest_mixed_valid_invalid`: Handles mix of valid/invalid files
- `test_ingest_default_photo_dir`: Uses default config directory

### `tests/test_auth.py`
Tests for the `/auth/selfie` endpoint:
- `test_auth_no_face`: Blank image returns 400
- `test_auth_multiple_faces`: Group photo returns 400
- `test_auth_valid_selfie`: Successful authentication flow returns 200
- `test_auth_unknown_face`: Unknown face returns 401
- `test_auth_wrong_format`: Text file returns 415
- `test_auth_no_file`: Missing file returns 422
- `test_auth_large_file`: File > 10MB returns 413
- `test_auth_after_multiple_ingests`: Works after idempotent ingestions

### `tests/test_images.py`
Tests for the `/images/{grab_id}` endpoint:
- `test_get_images_valid`: Full flow returns 200 with images list
- `test_get_images_invalid_uuid`: Invalid UUID format returns 400
- `test_get_images_not_found`: Non-existent UUID returns 404
- `test_get_images_ordering`: Images ordered by confidence
- `test_get_images_multiple_users`: User isolation verified
- `test_get_images_download_endpoint_exists`: Download endpoint works
- `test_get_images_with_special_characters_in_uuid`: Security check
- `test_get_images_case_sensitivity`: UUID case handling

## Test Data

Tests use real images from the `photos/` directory:
- `person1.jpg`, `person2.jpg`, `person5.jpg`, `person6.jpg`: Real face images
- Other files may be dummy/placeholder files (small ASCII text files)

The test suite automatically identifies valid JPEG images (> 1KB) for testing.

## Database State

Each test that modifies the database uses the `clean_db` fixture, which:
1. Truncates all tables before the test runs
2. Ensures clean state for isolated testing
3. Optionally cleans up after the test

## Notes

- Tests require a running PostgreSQL database with pgvector extension
- DeepFace model downloads may occur on first run (can be slow)
- Some tests generate synthetic images using PIL for edge cases
- Tests use FastAPI's TestClient for synchronous HTTP testing
- All tests are independent and can run in any order

## Troubleshooting

### Database connection errors
Ensure PostgreSQL is running and DATABASE_URL is set correctly in `.env`.

### DeepFace model errors
First run may download models. Ensure internet connectivity and sufficient disk space.

### Import errors
Verify all dependencies are installed: `pip install -r requirements.txt`

### Slow tests
Use `-n auto` for parallel execution: `pytest tests/ -v -n auto`
