# Grabpic

Grabpic is a high-performance facial recognition backend designed for large-scale events (marathons, races, conferences). Instead of manual photo tagging, photographers capture 50,000+ photos, and Grabpic automatically indexes every face. Runners authenticate with a selfie and instantly retrieve all their photos. The system uses VGG-Face embeddings with pgvector for similarity search and intelligently deduplicates faces to assign consistent grab_ids across multiple images of the same person.

**Tech Stack:** Python 3.11, FastAPI, DeepFace (VGG-Face), PostgreSQL + pgvector, Docker

**🚀 Live Demo:** http://13.41.81.112:8000/docs

## Architecture

### Database Schema (3 tables)

```
┌─────────────────────────┐
│      images             │
│─────────────────────────│
│ image_id (UUID, PK)     │◄─┐
│ file_path (TEXT)        │  │
│ ingested_at (TIMESTAMP) │  │
└─────────────────────────┘  │
                             │
┌─────────────────────────┐  │  ┌──────────────────────────┐
│       faces             │  │  │     face_images          │
│─────────────────────────│  │  │──────────────────────────│
│ grab_id (UUID, PK)      │◄─┼──┤ grab_id (UUID, FK)       │
│ embedding (vector 4096) │  │  │ image_id (UUID, FK)      │
│ created_at (TIMESTAMP)  │  └──┤ confidence (FLOAT)       │
└─────────────────────────┘     │ PK: (grab_id, image_id)  │
                                └──────────────────────────┘
```

**Deduplication Strategy:**
- During ingestion, before creating a new grab_id, we search existing faces using cosine similarity
- If distance < SIMILARITY_THRESHOLD (0.4), we reuse the existing grab_id
- This ensures the same person gets the same grab_id across all photos
- Junction table `face_images` tracks which faces appear in which images with confidence scores

## Setup

```bash
# Clone repository and start services
docker-compose up --build

# Wait ~10 seconds for database health check
# Service available at: http://localhost:8000
```

The application automatically runs database migrations on startup, creating the pgvector extension and all required tables. First run downloads the VGG-Face model (~580MB) - subsequent runs are much faster.

**Health Check:**
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "db": "connected", "model": "VGG-Face"}
```

## API Endpoints

### 1. Upload Photos (Easy Testing)
**Easiest way to test** - upload images directly without mounting volumes:

```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg" \
  -F "files=@photo3.jpg"
```

**What happens:**
- System detects all faces in uploaded images
- Creates unique `grab_id` for each person detected
- Same person across multiple photos gets the same `grab_id` (deduplication)
- Images saved to `/photos/upload_TIMESTAMP/` directory

**Response:**
```json
{
  "processed": 3,
  "faces_found": 5,
  "skipped": 0,
  "errors": []
}
```

**Note:** `processed` = images processed, `faces_found` = total face instances detected. One image can have multiple faces!

### 2. Authenticate with Selfie
Upload a selfie to get your `grab_id`:

```bash
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@my_selfie.jpg"
```

**What happens:**
- System extracts face embedding from your selfie
- Compares against all indexed faces using cosine similarity
- Returns match if distance < AUTH_THRESHOLD (0.6)
- Rejects if no face, multiple faces, or unrecognized

**Response:**
```json
{
  "grab_id": "123e4567-e89b-12d3-a456-426614174000",
  "confidence": 0.85,
  "match_quality": "high",
  "authenticated": true
}
```

**Match Quality Levels:**
- `high`: distance < 0.4 (very confident match)
- `medium`: 0.4 ≤ distance < 0.6 (acceptable match)
- `low`: 0.6 ≤ distance < threshold (marginal match)

### 3. List Your Images
Get all image paths for a grab_id:

```bash
curl http://localhost:8000/images/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "grab_id": "123e4567-e89b-12d3-a456-426614174000",
  "images": ["/photos/IMG_001.jpg", "/photos/IMG_045.jpg"],
  "total": 2
}
```

### 4. Download All Images as ZIP
Download all your photos in one ZIP file (sorted by confidence):

```bash
curl http://localhost:8000/images/123e4567-e89b-12d3-a456-426614174000/download \
  -o my_photos.zip
```

Files are named with confidence scores: `001_IMG_001_conf0.924.jpg`, `002_IMG_045_conf0.887.jpg`

### 5. Ingest from Directory (Batch Processing)
For processing images from mounted volumes:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"photo_dir": "/photos"}'
```

Default directory is `/photos` if no `photo_dir` specified.

### 6. Interactive Documentation
FastAPI auto-generates interactive API docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

**Perfect for judges** - test all endpoints directly in your browser!

## Design Decisions

### VGG-Face Model Choice
- **VGG-Face** produces 4096-dimensional embeddings with high accuracy for face recognition
- **Consistency is critical**: the same model must be used for both ingestion and authentication, otherwise embeddings are incomparable (different vector spaces!)
- Model is hardcoded in `config.py` (MODEL_NAME=VGG-Face) and reused across all services
- Alternative models (Facenet: 128-dim, ArcFace: 512-dim) are faster but VGG-Face offers better accuracy for this use case
- DeepFace model weights (~580MB) are cached after first download

### Deduplication Before Insert
- **Critical for correctness**: prevents duplicate grab_ids for the same person across multiple photos
- Before creating a new face, we query existing embeddings with similarity search
- If a match is found (distance < SIMILARITY_THRESHOLD), we reuse that grab_id
- Without this, the same runner photographed 50 times would get 50 different grab_ids - breaking the entire system!
- Junction table `face_images` tracks many-to-many relationship (one person → many images)

### Confidence Score in Auth Response
- Returns both distance-based confidence (0-1 scale) and categorical match_quality (high/medium/low)
- Helps clients decide whether to show "Welcome back!" vs "Please try again" vs "Not recognized"
- High quality: distance < 0.4, Medium: 0.4-0.6, Low: > 0.6
- Transparency builds trust - users can see *how confident* the system is, not just yes/no

### Threshold Values
- **SIMILARITY_THRESHOLD=0.4**: For deduplication during ingestion (same person detection)
- **AUTH_THRESHOLD=0.6**: For selfie authentication (stricter to prevent false positives)
- **Why different?** Ingestion favors recall (capture same person), auth favors precision (never match wrong person)
- **Tuning guide**: Lower thresholds = stricter matching, higher = more lenient
  1. Ingest test dataset with known duplicates
  2. Authenticate with selfies of known people
  3. Log the distance values
  4. Adjust thresholds to balance false positives vs false negatives

## Edge Cases Handled

### Ingestion (7 cases)
1. **Image with 0 faces**: Skipped gracefully, logged, batch continues
2. **Image with multiple faces**: All faces processed independently with separate grab_ids
3. **Same image ingested twice**: Skipped via UNIQUE constraint on file_path (idempotent)
4. **Corrupt/unreadable image**: Exception caught, logged, batch continues
5. **Blurry/partial face**: Low confidence from DeepFace → filtered out (< 0.85 threshold)
6. **Unsupported file format**: Ignored silently (only .jpg, .jpeg, .png processed)
7. **Same person across many photos**: Deduplication reuses existing grab_id

### Authentication (6 cases)
8. **Selfie with 0 faces**: 400 Bad Request
9. **Selfie with multiple faces**: 400 Bad Request (ambiguous identity)
10. **Face not recognized**: 401 Unauthorized (distance > AUTH_THRESHOLD)
11. **Empty database**: 404 Not Found (no faces indexed yet)
12. **File too large**: 413 Request Entity Too Large (> 10MB limit)
13. **Wrong content type**: 415 Unsupported Media Type (non-image files)

### Retrieval (2 cases)
14. **Invalid UUID format**: 400 Bad Request (not 500 from database)
15. **grab_id not found**: 404 Not Found (not empty list)

## Testing

### Manual Testing (Quick Start)
1. **Interactive docs**: http://localhost:8000/docs - test all endpoints in browser
2. **Upload test images**: Use `/ingest/upload` endpoint with sample photos
3. **Authenticate**: Upload one of the same photos to `/auth/selfie`
4. **Retrieve**: Use the returned `grab_id` to fetch images via `/images/{grab_id}`

### Automated Testing
```bash
# Run full test suite (23 tests)
docker exec grabpic_app python -m pytest tests/ -v

# Run specific test files
docker exec grabpic_app python -m pytest tests/test_auth.py -v
```

**Test coverage:** Ingestion (6 tests), Authentication (9 tests), Image Retrieval (8 tests)

See `docs/testing-guide.md` for detailed testing instructions.

## Performance Notes
- **First ingestion**: ~10-15 seconds (includes model download)
- **Subsequent ingestions**: ~2-3 seconds for 6 images
- **Authentication**: ~1-2 seconds per selfie (after model cached)
- **Image retrieval**: <100ms

## Common Issues

| Issue | Solution |
|-------|----------|
| "Failed to connect" | Wait 10s after `docker-compose up` for services to start |
| Slow first request | VGG-Face model downloading (~580MB), subsequent requests are fast |
| "No face detected" | Use clear frontal face photos, avoid blurry/partial faces |
| Empty results | Ensure ingestion completed successfully first |

Check logs: `docker logs grabpic_app --tail 50`
