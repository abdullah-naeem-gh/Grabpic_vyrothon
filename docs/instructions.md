# Grabpic — Build Instructions & Phase Prompts

## Prerequisites
- Docker + Docker Compose installed
- Python 3.11+
- Git

## Quick Start
```bash
git clone <repo>
cd grabpic
cp .env.example .env
docker-compose up -d
# Wait ~10s for postgres to start
curl http://localhost:8000/health
```

---

## Phase Prompts (copy-paste into your LLM)

### INITIAL PROMPT (Project Bootstrap)
```
You are building "Grabpic" — a facial recognition backend for large-scale events.

Tech stack: Python 3.11, FastAPI, DeepFace (VGG-Face model ONLY), PostgreSQL + pgvector extension, psycopg2, Docker Compose.

Create the full project scaffold:
1. docker-compose.yml — postgres:15 with pgvector, app service, volumes
2. Dockerfile — python:3.11-slim, install system deps for DeepFace (libgl1, libglib2.0)
3. requirements.txt — fastapi, uvicorn, deepface, psycopg2-binary, python-multipart, python-dotenv, numpy
4. .env.example — DB_URL, PHOTO_DIR, SIMILARITY_THRESHOLD=0.4, AUTH_THRESHOLD=0.6, MODEL_NAME=VGG-Face
5. app/config.py — load all env vars as constants
6. app/database.py — connection pool, run_migrations() that creates pgvector extension + 3 tables:
   - images(image_id UUID PK, file_path TEXT UNIQUE, ingested_at TIMESTAMP)
   - faces(grab_id UUID PK, embedding vector(128), created_at TIMESTAMP)
   - face_images(grab_id UUID FK, image_id UUID FK, confidence FLOAT, PRIMARY KEY(grab_id, image_id))
   - CREATE INDEX ON faces USING hnsw (embedding vector_cosine_ops)
7. app/main.py — FastAPI app, call run_migrations() on startup, include routers, /health endpoint

Do not implement routes yet. Just scaffold. Make it runnable.
```

---

### PHASE 1 PROMPT — Ingestion Service
```
Implement the ingestion pipeline for Grabpic. Read context.md for full architecture.

Create app/services/face.py:
- extract_faces(image_path) → list of dicts {embedding: list[float], face_confidence: float}
- Uses DeepFace.represent() with model_name=config.MODEL_NAME, enforce_detection=False
- Filter out faces with face_confidence < 0.85
- Returns empty list if no faces detected (never raise, just return [])

Create app/services/ingestion.py:
- ingest_directory(photo_dir) → dict {processed: int, faces_found: int, skipped: int, errors: list}
- Walks photo_dir for .jpg, .jpeg, .png files
- For each image:
  1. Check if file_path already in images table → skip if yes (idempotent)
  2. Insert into images table
  3. Call extract_faces()
  4. For each face embedding:
     a. Query faces table: SELECT grab_id, embedding <=> %s AS distance ORDER BY distance LIMIT 1
     b. If distance < SIMILARITY_THRESHOLD → reuse that grab_id
     c. Else → INSERT new grab_id into faces
     d. INSERT into face_images(grab_id, image_id, confidence)
  5. Catch all exceptions per image, log and continue

Create app/routers/ingest.py:
- POST /ingest with optional body {photo_dir: str} (defaults to config.PHOTO_DIR)
- Returns ingestion summary dict
- Also expose GET /ingest/status to check last run stats (store in memory dict)

CRITICAL: All DB queries use parameterized statements. No string interpolation.
```

---

### PHASE 2 PROMPT — Selfie Auth
```
Implement selfie authentication for Grabpic. Read context.md.

Create app/services/auth.py:
- authenticate_selfie(image_bytes: bytes) → dict {grab_id, confidence, match_quality} or raise HTTPException
- Save bytes to temp file (use tempfile.NamedTemporaryFile)
- Call DeepFace.represent() on temp file
- If 0 faces detected → raise HTTPException(400, "No face detected in selfie")
- If multiple faces detected → raise HTTPException(400, "Multiple faces in selfie. Use a solo photo.")
- Query: SELECT grab_id, embedding <=> %s AS distance FROM faces ORDER BY distance LIMIT 1
- If no rows (empty DB) → raise HTTPException(404, "No faces indexed yet")
- If distance >= AUTH_THRESHOLD → raise HTTPException(401, "Face not recognized")
- Map distance to confidence and match_quality (see context.md)
- Clean up temp file always (finally block)

Create app/routers/auth.py:
- POST /auth/selfie — accepts multipart file upload (UploadFile)
- Validate: only image/* content types allowed → 415 if not
- Validate: file size < 10MB → 413 if exceeded
- Call authenticate_selfie() and return result

Create app/models.py:
- AuthResponse: grab_id, confidence, match_quality, authenticated=True
- IngestResponse: processed, faces_found, skipped, errors
- ImageListResponse: grab_id, images (list of paths), total
```

---

### PHASE 3 PROMPT — Image Retrieval + Error Handling Pass
```
Implement image retrieval and do a full error handling pass for Grabpic.

Create app/routers/images.py:
- GET /images/{grab_id}
- Validate grab_id is valid UUID format → 400 if not
- Check grab_id exists in faces table → 404 "Person not found" if not
- Query: SELECT i.file_path, fi.confidence FROM face_images fi JOIN images i ON fi.image_id = i.image_id WHERE fi.grab_id = %s ORDER BY fi.confidence DESC
- Return ImageListResponse

Error handling pass — add to main.py:
- Global exception handler for Exception → 500 with {"error": "Internal server error", "detail": str(e)}
- Request validation error handler → 422 with clear message
- Add request logging middleware (log method, path, status, duration)

Final checks:
- Every endpoint returns consistent JSON shape: always has "error" key on failure
- No endpoint ever returns a raw Python exception message to client
- /health returns {"status": "ok", "db": "connected", "model": config.MODEL_NAME}
  - Actually test DB connection in health check
```

---

### PHASE 4 PROMPT — Tests
```
Write tests for Grabpic using pytest. Use real test images from the photos/ dir.

tests/conftest.py:
- Fixture: test_client (TestClient from FastAPI)
- Fixture: sample_image_path (use any .jpg in photos/)
- Fixture: clean_db (truncate all tables before each test)

tests/test_ingest.py:
- test_ingest_empty_directory → expect 200, processed=0
- test_ingest_valid_photos → expect faces_found > 0
- test_ingest_idempotent → run twice, second run skipped == first run processed
- test_ingest_no_face_image → image with no face → skipped gracefully, no 500

tests/test_auth.py:
- test_auth_no_face → upload blank image → 400
- test_auth_multiple_faces → upload group photo → 400
- test_auth_valid_selfie → ingest photo first, then auth with same → 200 with grab_id
- test_auth_unknown_face → upload face not in DB → 401
- test_auth_wrong_format → upload .txt file → 415

tests/test_images.py:
- test_get_images_valid → ingest first, auth to get grab_id, then fetch → 200 with images list
- test_get_images_invalid_uuid → /images/not-a-uuid → 400
- test_get_images_not_found → /images/<random-uuid> → 404

Run with: pytest tests/ -v
```

---

### PHASE 5 PROMPT — README + Final Polish
```
Write the README.md for Grabpic submission.

Include:
1. One-paragraph description of what Grabpic does
2. Architecture section: describe the 3-table schema and the deduplication approach
3. Setup: docker-compose up --build, wait for health check
4. All curl examples:
   - POST /ingest (with and without body)
   - POST /auth/selfie (with file upload)
   - GET /images/{grab_id}
   - GET /health
5. Design decisions section:
   - Why VGG-Face and why consistent model usage matters
   - Why deduplication before insert (prevents duplicate grab_ids for same person)
   - Why confidence score in auth response
   - Threshold values and how to tune them
6. Edge cases handled section (list all 14 from todo.md)

Also create a simple schema diagram as ASCII art in README.
Keep it under 150 lines total.
```

---

## Running Tests
```bash
docker-compose up -d
pytest tests/ -v --tb=short
```

## Common Issues
| Issue | Fix |
|---|---|
| `pgvector not found` | Run `docker-compose down -v && docker-compose up -d` |
| `DeepFace model download` | First run downloads ~500MB, wait |
| `No face detected` | Photo too small/blurry, use clear frontal face photos |
| `distance always 0` | Same model used for both ingest and auth? Check config |