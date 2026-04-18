# Grabpic — Facial Recognition Backend

A high-performance facial recognition backend for large-scale events (e.g., marathons with 500 runners, 50,000 photos).

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for testing scripts)

### Run the Application

```bash
# 1. Start the services
docker-compose up --build

# 2. Download test images (optional)
python3 download_test_images.py

# 3. Access Swagger docs
open http://localhost:8000/docs
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "online",
  "database": "healthy"
}
```

---

### 2. Ingest Photos
Crawl a directory and process all images to extract and index faces.

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "photo_dir": "./photos"
  }'
```

**Response:**
```json
{
  "processed": 6,
  "faces_found": 8,
  "skipped": 0,
  "errors": []
}
```

---

### 3. Authenticate with Selfie
Upload a selfie to authenticate and retrieve your `grab_id`.

```bash
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@photos/person1_a.jpg"
```

**Success Response (200):**
```json
{
  "grab_id": "123e4567-e89b-12d3-a456-426614174000",
  "confidence": 0.9234,
  "match_quality": "high",
  "authenticated": true
}
```

**Error Responses:**

- **400 Bad Request** - No face detected:
  ```json
  {
    "detail": "No face detected in selfie"
  }
  ```

- **400 Bad Request** - Multiple faces:
  ```json
  {
    "detail": "Multiple faces in selfie. Use a solo photo."
  }
  ```

- **401 Unauthorized** - Face not recognized:
  ```json
  {
    "detail": "Face not recognized"
  }
  ```

- **404 Not Found** - Empty database:
  ```json
  {
    "detail": "No faces indexed yet"
  }
  ```

- **413 Request Entity Too Large**:
  ```json
  {
    "detail": "Request Entity Too Large. Maximum file size is 10MB, got 12345678 bytes"
  }
  ```

- **415 Unsupported Media Type**:
  ```json
  {
    "detail": "Unsupported Media Type. Expected image/*, got application/pdf"
  }
  ```

---

### 4. Retrieve User Images
Get all images for a specific `grab_id`.

```bash
curl http://localhost:8000/images/123e4567-e89b-12d3-a456-426614174000
```

**Success Response (200):**
```json
{
  "grab_id": "123e4567-e89b-12d3-a456-426614174000",
  "images": [
    "./photos/person1_a.jpg",
    "./photos/person1_b.jpg"
  ],
  "total": 2
}
```

**Error Responses:**

- **400 Bad Request** - Invalid UUID:
  ```json
  {
    "detail": "Invalid UUID format: not-a-uuid"
  }
  ```

- **404 Not Found** - grab_id not found:
  ```json
  {
    "detail": "grab_id not found: 123e4567-e89b-12d3-a456-426614174000"
  }
  ```

---

## Testing Workflow

Here's a complete workflow to test the system:

```bash
# 1. Download test images
python3 download_test_images.py

# 2. Ingest photos
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"photo_dir": "./photos"}'

# 3. Authenticate with a selfie (use one of the ingested images)
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@photos/person1_a.jpg" \
  | python3 -m json.tool

# 4. Extract grab_id from response and fetch images
# Replace GRAB_ID with the actual grab_id from step 3
curl http://localhost:8000/images/GRAB_ID \
  | python3 -m json.tool
```

---

## Architecture

### Database Schema

```
┌─────────────┐         ┌─────────────────┐         ┌─────────────┐
│   images    │         │   face_images   │         │    faces    │
├─────────────┤         ├─────────────────┤         ├─────────────┤
│ image_id PK │◄───────┤ image_id FK     │         │ grab_id PK  │
│ file_path U │         │ grab_id FK      ├────────►│ embedding   │
│ ingested_at │         │ confidence      │         │ created_at  │
└─────────────┘         └─────────────────┘         └─────────────┘
```

**Key Points:**
- `images`: Stores metadata about each ingested photo
- `faces`: Stores unique face embeddings with a unique `grab_id`
- `face_images`: Junction table mapping which faces appear in which images
- One image can contain multiple people (multiple `grab_id`s)
- One person (grab_id) can appear in multiple images

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3.11 | DeepFace ecosystem, development speed |
| Framework | FastAPI | Auto Swagger docs, async support, clean API |
| Face AI | DeepFace (VGG-Face) | Simple pip install, consistent embeddings |
| Database | PostgreSQL + pgvector | Vector similarity search with cosine distance |
| ORM | psycopg2 (raw SQL) | Fast development for competition scope |
| Container | Docker Compose | One-command deployment for judges |

---

## Design Decisions

### 1. Face Deduplication
**Problem:** Same person appears in multiple photos — we need one `grab_id` per person, not per photo.

**Solution:** During ingestion, for each detected face:
1. Query existing faces using cosine distance: `embedding <=> new_embedding`
2. If distance < 0.4 → same person → reuse existing `grab_id`
3. If distance >= 0.4 → new person → create new `grab_id`

This ensures each unique person gets exactly one `grab_id`.

### 2. Threshold Strategy

We use different thresholds for different purposes:

| Threshold | Value | Use Case |
|-----------|-------|----------|
| Deduplication | 0.4 | Identifying same person during ingestion |
| Authentication | 0.6 | Allowing user to authenticate with selfie |

**Rationale:**
- Deduplication threshold is stricter (0.4) to avoid merging different people
- Auth threshold is looser (0.6) to account for lighting, angle, expression changes

### 3. Match Quality Mapping

```python
if distance < 0.3:   match_quality = "high"    # Very confident match
elif distance < 0.45: match_quality = "medium"  # Good match
else:                 match_quality = "low"     # Acceptable but not ideal
```

Confidence score: `confidence = 1 - distance`

This gives judges visibility into match quality without exposing raw distance metrics.

### 4. Model Consistency
**CRITICAL:** VGG-Face is used everywhere (ingestion AND authentication).

Mixing models produces incompatible embeddings and breaks matching.
Configured once in `app/config.py` as `MODEL_NAME = "VGG-Face"`.

---

## Edge Cases Handled

### Ingestion Edge Cases
1. ✅ **Image with 0 faces** → Skipped, logged, continues processing
2. ✅ **Image with multiple faces** → All faces processed, separate `grab_id`s assigned
3. ✅ **Duplicate image path** → Skipped via UNIQUE constraint on `file_path`
4. ✅ **Corrupt/unreadable image** → Exception caught, logged, continues
5. ✅ **Blurry/low-confidence face** → Filtered out (face_confidence < 0.85)
6. ✅ **Unsupported file format** → Ignored during directory crawl

### Authentication Edge Cases
7. ✅ **Selfie with 0 faces** → 400 Bad Request
8. ✅ **Selfie with multiple faces** → 400 Bad Request ("Use a solo photo")
9. ✅ **Distance >= AUTH_THRESHOLD** → 401 Unauthorized
10. ✅ **Empty database** → 404 Not Found ("No faces indexed yet")
11. ✅ **File too large (>10MB)** → 413 Request Entity Too Large
12. ✅ **Wrong content type** → 415 Unsupported Media Type

### Retrieval Edge Cases
13. ✅ **Invalid UUID format** → 400 Bad Request
14. ✅ **grab_id not found** → 404 Not Found (not empty list)

---

## Project Structure

```
grabpic/
├── docker-compose.yml       # Service orchestration
├── Dockerfile               # Python + DeepFace + system deps
├── requirements.txt         # Pinned Python dependencies
├── .env                     # Environment variables (not committed)
├── .env.example             # Template for .env
├── README.md                # This file
├── download_test_images.py  # Fetch sample images for testing
├── app/
│   ├── main.py              # FastAPI app, routes, lifespan
│   ├── config.py            # Settings (thresholds, model name)
│   ├── database.py          # DB connection pool, migrations
│   ├── models.py            # Pydantic response models
│   ├── services/
│   │   ├── ingestion.py     # Crawl + face detection pipeline
│   │   ├── face.py          # DeepFace wrapper
│   │   └── auth.py          # Selfie authentication logic
│   └── routers/
│       ├── ingest.py        # POST /ingest
│       ├── auth.py          # POST /auth/selfie
│       └── images.py        # GET /images/{grab_id}
└── photos/                  # Sample images directory
```

---

## Development

### Environment Variables

Create a `.env` file (use `.env.example` as template):

```env
DATABASE_URL=postgresql://grabpic:password@db:5432/grabpic
PHOTO_DIR=./photos
SIMILARITY_THRESHOLD=0.4
AUTH_THRESHOLD=0.6
MODEL_NAME=VGG-Face
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python -c "from app.database import run_migrations; run_migrations()"

# Start server
uvicorn app.main:app --reload
```

---

## Swagger Documentation

Interactive API documentation is automatically available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test all endpoints directly from the Swagger UI.

---

## Performance Considerations

### Vector Indexing
VGG-Face produces 4096-dimensional embeddings. pgvector's HNSW and IVFFlat indexes support up to 2000 dimensions.

For this competition scope (500 runners), sequential scans are acceptable.

**Production considerations:**
1. Use a model with fewer dimensions (e.g., Facenet → 128D)
2. Apply PCA dimensionality reduction
3. Use specialized vector databases (Pinecone, Milvus, Qdrant)

### Scalability
- Connection pooling via psycopg2.pool (1-10 connections)
- Idempotent ingestion (duplicate paths skipped)
- Per-image error handling (one corrupt image doesn't stop batch)
- Temp file cleanup in finally blocks

---

## Troubleshooting

### DeepFace Installation Issues
If DeepFace fails with OpenCV errors, ensure system dependencies are installed:

```bash
apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0
```

(Already included in Dockerfile)

### Database Connection Issues
Check that PostgreSQL is running and pgvector extension is enabled:

```bash
docker-compose logs db
```

### No Faces Detected
Ensure images contain clear, front-facing faces. DeepFace works best with:
- Good lighting
- Front-facing angles
- Faces > 100x100 pixels
- Minimal occlusion

---

## License

MIT

---

## Author

Built for Vyrothon 2026 Hackathon
