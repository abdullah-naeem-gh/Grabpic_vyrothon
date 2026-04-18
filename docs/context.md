# Grabpic — Full System Context

## What We're Building
A facial recognition backend for large-scale events (e.g., marathons with 500 runners, 50,000 photos).
- Crawls a storage directory, detects all faces, assigns unique `grab_id` per person
- Users authenticate with a selfie to retrieve their photos
- One image can contain multiple people → multiple `grab_id`s

## Tech Stack
| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.11 | DeepFace ecosystem, speed of development |
| Framework | FastAPI | Auto Swagger docs (free nice-to-have), async, clean |
| Face AI | DeepFace (VGG-Face model) | One pip install, wraps everything, consistent |
| DB | PostgreSQL + pgvector | Judges prefer Postgres; pgvector adds ANN search |
| ORM | psycopg2 (raw SQL) | Faster to write than SQLAlchemy for this scope |
| Containerization | Docker Compose | Reproducible, judges can run with one command |

> **CRITICAL:** Use VGG-Face everywhere — ingest AND selfie auth must use the same model or embeddings are incompatible.

## Database Schema

```
images        → image_id UUID PK, file_path TEXT, ingested_at TIMESTAMP
faces         → grab_id UUID PK, embedding vector(128), created_at TIMESTAMP
face_images   → grab_id UUID FK, image_id UUID FK, confidence FLOAT
               (junction table: one image → many grab_ids, one grab_id → many images)
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/ingest` | Crawl directory, process all images |
| POST | `/auth/selfie` | Upload selfie → returns grab_id + confidence |
| GET | `/images/{grab_id}` | Fetch all image paths for a person |
| GET | `/docs` | Swagger UI (auto from FastAPI) |
| GET | `/health` | Health check |

## Similarity Threshold
- `distance < 0.4` → same person (reuse grab_id) — used during ingest deduplication
- `distance < 0.6` → auth match (return grab_id with confidence)
- `distance >= 0.6` → no match → 401 Unauthorized

## Confidence Mapping
```python
if distance < 0.3:   match_quality = "high"
elif distance < 0.45: match_quality = "medium"
else:                 match_quality = "low"
confidence = round(1 - distance, 4)
```

## Project Structure
```
grabpic/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
├── app/
│   ├── main.py           # FastAPI app, routes
│   ├── config.py         # Constants (model name, threshold, etc.)
│   ├── database.py       # DB connection, migrations
│   ├── models.py         # Pydantic response models
│   ├── services/
│   │   ├── ingestion.py  # Crawl + face pipeline
│   │   ├── face.py       # DeepFace wrapper
│   │   └── auth.py       # Selfie auth logic
│   └── routers/
│       ├── ingest.py
│       ├── auth.py
│       └── images.py
├── photos/               # Sample images for testing
├── tests/
│   ├── test_ingest.py
│   ├── test_auth.py
│   └── test_images.py
├── context.md
├── instructions.md
└── todo.md
```