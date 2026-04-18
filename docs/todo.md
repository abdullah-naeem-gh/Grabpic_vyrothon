# Grabpic — Todo List

Legend: 🔴 CRITICAL (breaks everything if missed) | 🟡 IMPORTANT | 🟢 NICE TO HAVE

---

## Phase 0 — Scaffold
- [ ] 🔴 docker-compose.yml with postgres + pgvector image (ankane/pgvector or pgvector/pgvector)
- [ ] 🔴 Dockerfile installs libgl1 + libglib2.0 (DeepFace crashes without them)
- [ ] 🔴 requirements.txt pinned versions
- [ ] 🔴 app/config.py — MODEL_NAME = "VGG-Face" hardcoded as default, overridable via env
- [ ] 🔴 database.py creates pgvector extension BEFORE creating tables
- [ ] 🔴 HNSW index on faces.embedding for fast similarity search
- [ ] 🟡 .env.example committed (not .env)
- [ ] 🟢 /health endpoint checks actual DB connection

---

## Phase 1 — Ingestion
- [ ] 🔴 Same DeepFace model used in ingestion AND auth (set in config, never hardcode per service)
- [ ] 🔴 Deduplication: check similarity BEFORE inserting new grab_id
- [ ] 🔴 Multiple faces per image: loop ALL detected faces, not just first
- [ ] 🔴 face_images junction table populated for every face-image pair
- [ ] 🔴 Idempotent: skip already-ingested image paths (check file_path UNIQUE)
- [ ] 🟡 enforce_detection=False in DeepFace.represent() — prevents crash on partial faces
- [ ] 🟡 Filter low-confidence face detections (face_confidence < 0.85 → skip)
- [ ] 🟡 Per-image try/except — one corrupt image must not stop entire ingest
- [ ] 🟡 Support .jpg, .jpeg, .png — ignore everything else silently
- [ ] 🟢 Ingest summary response: {processed, faces_found, skipped, errors[]}

---

## Phase 2 — Selfie Auth
- [ ] 🔴 Reject selfies with 0 faces detected → 400
- [ ] 🔴 Reject selfies with multiple faces → 400 (can't know who is authenticating)
- [ ] 🔴 Threshold gate: distance >= AUTH_THRESHOLD → 401, never return a wrong person
- [ ] 🔴 Temp file cleanup in finally block — no leaked files
- [ ] 🟡 Return confidence score and match_quality in response (not just grab_id)
- [ ] 🟡 Validate file content-type is image/* → 415 before processing
- [ ] 🟡 Validate file size < 10MB → 413 before processing
- [ ] 🟡 Handle empty DB case (no faces indexed yet) → 404, not 500
- [ ] 🟢 match_quality: "high" / "medium" / "low" based on distance bands

---

## Phase 3 — Image Retrieval
- [ ] 🔴 Validate grab_id is valid UUID format → 400 (not 500 from DB)
- [ ] 🔴 Return 404 when grab_id not in faces table (not empty list)
- [ ] 🟡 ORDER BY confidence DESC so best matches appear first
- [ ] 🟢 Include total count in response

---

## Phase 4 — Error Handling
- [ ] 🔴 Global exception handler — never expose raw Python tracebacks to client
- [ ] 🔴 All DB queries use parameterized statements — no SQL injection
- [ ] 🟡 Consistent error response shape: {"error": "...", "detail": "..."}
- [ ] 🟡 Request logging middleware (method, path, status, ms)
- [ ] 🟢 422 handler with human-readable validation errors

---

## Phase 5 — Tests
- [ ] 🟡 test_ingest_idempotent — running twice must not duplicate grab_ids
- [ ] 🟡 test_auth_valid_selfie — ingest first, auth with same photo → must match
- [ ] 🟡 test_auth_unknown_face → 401
- [ ] 🟡 test_get_images_invalid_uuid → 400
- [ ] 🟡 test_get_images_not_found → 404
- [ ] 🟢 test_ingest_no_face_image → no 500, graceful skip

---

## Phase 6 — Submission
- [ ] 🔴 README with clear docker-compose up steps
- [ ] 🔴 Curl examples for all 4 endpoints
- [ ] 🟡 Schema diagram (ASCII art in README)
- [ ] 🟡 Design decisions section (deduplication, threshold, model consistency)
- [ ] 🟡 Edge cases handled section
- [ ] 🟢 Swagger accessible at /docs (free from FastAPI)

---

## All 14 Edge Cases (must handle all)

### Ingestion Edge Cases
1. 🟡 Image with 0 faces → skip, log, continue (don't fail whole batch)
2. 🔴 Image with multiple faces → process ALL, assign separate grab_ids
3. 🟡 Same image ingested twice → skip on second run (idempotent via UNIQUE path)
4. 🟡 Corrupt/unreadable image → catch exception, log, continue
5. 🟡 Blurry/partial face → DeepFace returns low confidence → skip
6. 🟡 Unsupported file format → ignore silently during crawl
7. 🔴 Same person appears across many photos → deduplication reuses grab_id

### Auth Edge Cases
8. 🔴 Selfie has 0 faces → 400 Bad Request
9. 🔴 Selfie has multiple faces → 400 Bad Request
10. 🟡 Selfie confidence below threshold → 401 Unauthorized
11. 🟡 Empty DB (no faces indexed) → 404 Not Found
12. 🟡 File too large → 413 Request Entity Too Large
13. 🟡 Wrong content type → 415 Unsupported Media Type

### Retrieval Edge Cases
14. 🔴 Invalid UUID format → 400 (not 500 from Postgres)
15. 🟡 grab_id not found → 404 (not empty list)

---

## Time Tracking (90 min budget)
- [ ] Phase 0 Scaffold → 0:00–0:15
- [ ] Phase 1 Ingestion → 0:15–0:40
- [ ] Phase 2 Auth → 0:40–0:60
- [ ] Phase 3 Retrieval + Error pass → 0:60–0:75
- [ ] Phase 4 Tests → 0:75–0:85
- [ ] Phase 5 README → 0:85–0:90