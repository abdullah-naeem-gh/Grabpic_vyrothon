# Grabpic API - Quick Testing Guide for Judges

This document provides quick curl commands to test all API functionality.

## Prerequisites

Start the application:
```bash
docker compose up --build
```

## Quick Test Workflow

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "online", "database": "healthy"}
```

---

### 2. Ingest Photos
Process all images in the photos directory:
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"photo_dir": "/photos"}'
```

**Expected Response:**
```json
{
  "processed": 8,
  "faces_found": 7,
  "skipped": 0,
  "errors": []
}
```

---

### 3. Authenticate with Selfie
Upload a selfie to get your `grab_id`:

**From host machine:**
```bash
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@photos/person1.jpg"
```

**From inside Docker:**
```bash
docker exec grabpic_app curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@/photos/person1.jpg"
```

**Expected Response (200 OK):**
```json
{
  "grab_id": "f53af081-195f-4ceb-9c9f-c62a447b8ad0",
  "confidence": 1.0,
  "match_quality": "high",
  "authenticated": true
}
```

**Save the grab_id for the next step!**

---

### 4. Retrieve Your Images
Replace `GRAB_ID` with the value from step 3:

```bash
curl http://localhost:8000/images/GRAB_ID
```

**Example:**
```bash
curl http://localhost:8000/images/f53af081-195f-4ceb-9c9f-c62a447b8ad0
```

**Expected Response:**
```json
{
  "grab_id": "f53af081-195f-4ceb-9c9f-c62a447b8ad0",
  "images": [
    "/photos/person1.jpg",
    "/photos/person1_duplicate.jpg"
  ],
  "total": 2
}
```

---

## Edge Case Testing

### No Face Detected (400)
```bash
# Create a solid color image
docker exec grabpic_app python3 -c "from PIL import Image; img = Image.new('RGB', (100, 100), color='blue'); img.save('/tmp/no_face.jpg')"

# Try to authenticate with it
docker exec grabpic_app curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@/tmp/no_face.jpg"
```

**Expected:** `400 Bad Request` or `401 Unauthorized`

---

### Wrong Content Type (415)
```bash
echo "test" > /tmp/test.txt
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@/tmp/test.txt;type=text/plain"
```

**Expected Response:**
```json
{
  "detail": "Unsupported Media Type. Expected image/*, got text/plain"
}
```

---

### File Too Large (413)
```bash
# Create an 11MB file
dd if=/dev/zero of=/tmp/large_image.jpg bs=1M count=11

# Try to upload it
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@/tmp/large_image.jpg;type=image/jpeg"
```

**Expected Response:**
```json
{
  "detail": "Request Entity Too Large. Maximum file size is 10MB, got 11534336 bytes"
}
```

---

### Invalid UUID (400)
```bash
curl http://localhost:8000/images/not-a-uuid
```

**Expected Response:**
```json
{
  "detail": "Invalid UUID format: not-a-uuid"
}
```

---

### Non-existent grab_id (404)
```bash
curl http://localhost:8000/images/00000000-0000-0000-0000-000000000000
```

**Expected Response:**
```json
{
  "detail": "grab_id not found: 00000000-0000-0000-0000-000000000000"
}
```

---

### Empty Database (404)
```bash
# Clear the database
docker exec grabpic_db psql -U postgres -d grabpic \
  -c "DELETE FROM face_images; DELETE FROM faces; DELETE FROM images;"

# Try to authenticate
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@photos/person1.jpg"
```

**Expected Response:**
```json
{
  "detail": "No faces indexed yet"
}
```

**Don't forget to re-ingest after this test!**

---

## Interactive API Documentation

FastAPI provides interactive documentation at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test all endpoints directly from the browser!

---

## Full Test Script

Run the automated test script:
```bash
./test_api.sh
```

This will test all endpoints and edge cases automatically.

---

## Database Inspection

### Check ingested images
```bash
docker exec grabpic_db psql -U postgres -d grabpic \
  -c "SELECT COUNT(*) FROM images;"
```

### Check unique faces
```bash
docker exec grabpic_db psql -U postgres -d grabpic \
  -c "SELECT COUNT(*) FROM faces;"
```

### Check face-image mappings
```bash
docker exec grabpic_db psql -U postgres -d grabpic \
  -c "SELECT grab_id, COUNT(*) as image_count FROM face_images GROUP BY grab_id;"
```

---

## Tips for Judges

1. **Swagger UI is the easiest way to test**: Just open http://localhost:8000/docs in your browser

2. **Use pretty-printed JSON**: Pipe curl output to `python3 -m json.tool`:
   ```bash
   curl http://localhost:8000/health | python3 -m json.tool
   ```

3. **Check response times**: Add `-w "\nTime: %{time_total}s\n"` to curl:
   ```bash
   curl -w "\nTime: %{time_total}s\n" http://localhost:8000/health
   ```

4. **Test with your own photos**: Copy images to the `photos/` directory and re-run ingestion

5. **Reset database**: Clear all tables to test empty database scenarios:
   ```bash
   docker exec grabpic_db psql -U postgres -d grabpic \
     -c "DELETE FROM face_images; DELETE FROM faces; DELETE FROM images;"
   ```

---

## Common Issues

### "curl: (7) Failed to connect"
- Make sure Docker containers are running: `docker ps`
- Wait a few seconds for the app to start up after `docker compose up`

### "detail": "Internal Server Error"
- Check logs: `docker logs grabpic_app --tail 50`
- Ensure photos directory exists: `docker exec grabpic_app ls -la /photos`

### Slow first authentication
- DeepFace downloads the VGG-Face model on first use (~580MB)
- Subsequent requests will be much faster (model is cached)

---

## Performance Notes

- **First ingestion**: ~10-15 seconds for 6 images (includes model download)
- **Subsequent ingestions**: ~2-3 seconds for 6 images
- **Authentication**: ~1-2 seconds per selfie (after model is cached)
- **Image retrieval**: <100ms
