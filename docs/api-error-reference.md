# GrabPic API Error Reference

## Standard Error Response Format

All error responses follow this consistent JSON structure:

```json
{
  "error": "<Error Type>",
  "detail": "<Specific error message>"
}
```

## Error Codes by Endpoint

### GET /health
**Success Response (200):**
```json
{
  "status": "ok",
  "db": "connected",
  "model": "VGG-Face"
}
```

---

### GET /images/{grab_id}
Retrieve all images for a person by their grab_id.

**Success Response (200):**
```json
{
  "grab_id": "550e8400-e29b-41d4-a716-446655440000",
  "images": ["/path/to/image1.jpg", "/path/to/image2.jpg"],
  "total": 2
}
```

**Error Responses:**

**400 - Invalid UUID Format**
```json
{
  "error": "Bad Request",
  "detail": "Invalid UUID format: not-a-uuid"
}
```

**404 - Person Not Found**
```json
{
  "error": "Not Found",
  "detail": "Person not found"
}
```

**500 - Database Connection Failed**
```json
{
  "error": "Internal Server Error",
  "detail": "Database connection failed"
}
```

---

### POST /auth/selfie
Authenticate a user by uploading a selfie.

**Request:** Multipart form data with image file

**Success Response (200):**
```json
{
  "grab_id": "550e8400-e29b-41d4-a716-446655440000",
  "confidence": 0.8234,
  "match_quality": "high",
  "authenticated": true
}
```

**Error Responses:**

**400 - No Face Detected**
```json
{
  "error": "Bad Request",
  "detail": "No face detected in selfie"
}
```

**400 - Multiple Faces**
```json
{
  "error": "Bad Request",
  "detail": "Multiple faces in selfie. Use a solo photo."
}
```

**401 - Face Not Recognized**
```json
{
  "error": "Unauthorized",
  "detail": "Face not recognized"
}
```

**404 - No Faces Indexed**
```json
{
  "error": "Not Found",
  "detail": "No faces indexed yet"
}
```

**413 - File Too Large**
```json
{
  "error": "Payload Too Large",
  "detail": "Request Entity Too Large. Maximum file size is 10MB, got 15728640 bytes"
}
```

**415 - Wrong Content Type**
```json
{
  "error": "Unsupported Media Type",
  "detail": "Unsupported Media Type. Expected image/*, got text/plain"
}
```

---

### POST /ingest
Ingest photos from a directory.

**Request Body:**
```json
{
  "photo_dir": "/path/to/photos"
}
```

**Success Response (200):**
```json
{
  "processed": 50,
  "faces_found": 45,
  "skipped": 2,
  "errors": ["Error processing file1.jpg: corrupted"]
}
```

**Error Responses:**

**500 - Ingestion Failed**
```json
{
  "error": "Internal Server Error",
  "detail": "Ingestion failed: <error message>"
}
```

---

### POST /ingest/upload
Upload and ingest photos via multipart form data.

**Request:** Multipart form data with multiple image files

**Success Response (200):**
```json
{
  "processed": 10,
  "faces_found": 8,
  "skipped": 1,
  "errors": []
}
```

**Error Responses:**

**400 - No Files Uploaded**
```json
{
  "error": "Bad Request",
  "detail": "No files uploaded"
}
```

**422 - Validation Error**
```json
{
  "error": "Validation error",
  "detail": "body -> files: Field required"
}
```

**500 - Ingestion Failed**
```json
{
  "error": "Internal Server Error",
  "detail": "Ingestion failed: <error message>"
}
```

---

## HTTP Status Code Summary

| Code | Type | When |
|------|------|------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input (UUID format, no face, multiple faces, etc.) |
| 401 | Unauthorized | Face not recognized during authentication |
| 404 | Not Found | Resource doesn't exist (person, faces in database) |
| 413 | Payload Too Large | File exceeds size limit (>10MB) |
| 415 | Unsupported Media Type | Wrong file type (expected image) |
| 422 | Unprocessable Entity | Request validation failed (missing fields, wrong types) |
| 500 | Internal Server Error | Unexpected server error |

---

## Request Logging

All requests are logged with the following information:
- HTTP method
- Request path
- Response status code
- Request duration in milliseconds

Example log entries:
```
INFO:app.main:Request started: GET /images/not-a-uuid
INFO:app.main:Request completed: GET /images/not-a-uuid status=400 duration=1.48ms
```

---

## Testing Error Responses

```bash
# Invalid UUID
curl http://localhost:8000/images/invalid-uuid

# Person not found
curl http://localhost:8000/images/$(uuidgen)

# Wrong content type
curl -X POST http://localhost:8000/auth/selfie -F "file=@document.pdf"

# Missing required field
curl -X POST http://localhost:8000/ingest/upload

# Check logs
docker compose logs app --tail 20
```
