# Image Download Guide

## Two Ways to Get Images

### Option 1: Get Image Paths (JSON)
**Endpoint:** `GET /images/{grab_id}`

Returns a JSON list of file paths:
```bash
curl http://localhost:8000/images/YOUR-GRAB-ID | python3 -m json.tool
```

**Response:**
```json
{
  "grab_id": "550e8400-e29b-41d4-a716-446655440000",
  "images": [
    "/app/photos/image1.jpg",
    "/app/photos/image2.jpg"
  ],
  "total": 2
}
```

---

### Option 2: Download All Images as ZIP ⭐ NEW!
**Endpoint:** `GET /images/{grab_id}/download`

Downloads all images as a ZIP file:
```bash
# Download ZIP file
curl -o my_images.zip http://localhost:8000/images/YOUR-GRAB-ID/download

# Or with authentication grab_id from previous response
GRAB_ID="550e8400-e29b-41d4-a716-446655440000"
curl -o my_images.zip http://localhost:8000/images/$GRAB_ID/download
```

**ZIP Contents:**
- Images are ordered by confidence (best matches first)
- Filenames include confidence scores: `001_photo1_conf0.923.jpg`
- Format: `{order}_{original_name}_conf{confidence}{extension}`

---

## Complete Workflow Example

```bash
# Step 1: Upload test images (if you haven't already)
curl -X POST http://localhost:8000/ingest/upload \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg"

# Step 2: Authenticate with selfie and get grab_id
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@my_selfie.jpg" | python3 -m json.tool

# Response will contain:
# {
#   "grab_id": "550e8400-e29b-41d4-a716-446655440000",
#   "confidence": 0.85,
#   "match_quality": "high",
#   "authenticated": true
# }

# Step 3a: Get image paths as JSON
curl http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000 \
  | python3 -m json.tool

# Step 3b: Download all images as ZIP
curl -o my_images.zip \
  http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000/download

# Step 4: Extract and view
unzip my_images.zip
ls -lh
```

---

## Using Browser

You can also download directly in your browser:

1. Open: `http://localhost:8000/docs` (Swagger UI)
2. Find: `GET /images/{grab_id}/download`
3. Click "Try it out"
4. Enter your `grab_id`
5. Click "Execute"
6. Click "Download file" button

---

## Error Responses

Both endpoints return consistent error formats:

**Invalid UUID (400):**
```bash
$ curl http://localhost:8000/images/invalid-uuid/download
{
  "error": "Bad Request",
  "detail": "Invalid UUID format: invalid-uuid"
}
```

**Person Not Found (404):**
```bash
$ curl http://localhost:8000/images/00000000-0000-0000-0000-000000000000/download
{
  "error": "Not Found",
  "detail": "Person not found"
}
```

**No Images Available (404):**
```bash
{
  "error": "Not Found",
  "detail": "No images found for this person"
}
```

---

## Automated Script Example

Save this as `download_my_images.sh`:

```bash
#!/bin/bash

# 1. Authenticate and get grab_id
echo "Authenticating with selfie..."
RESPONSE=$(curl -s -X POST http://localhost:8000/auth/selfie \
  -F "file=@$1")

GRAB_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['grab_id'])")

echo "Got grab_id: $GRAB_ID"

# 2. Download images
echo "Downloading images..."
curl -o images_${GRAB_ID}.zip \
  http://localhost:8000/images/${GRAB_ID}/download

echo "Downloaded: images_${GRAB_ID}.zip"

# 3. Extract
unzip -q images_${GRAB_ID}.zip -d images_${GRAB_ID}
echo "Extracted to: images_${GRAB_ID}/"
ls images_${GRAB_ID}/
```

**Usage:**
```bash
chmod +x download_my_images.sh
./download_my_images.sh my_selfie.jpg
```

---

## Features

✅ All images in one ZIP file
✅ Images ordered by confidence (best first)
✅ Filenames include confidence scores
✅ Direct browser download support
✅ Consistent error handling
✅ Automatic file validation
✅ Memory-efficient streaming

---

## API Summary

| Endpoint | Method | Returns | Use Case |
|----------|--------|---------|----------|
| `/images/{grab_id}` | GET | JSON with paths | For frontend/API integration |
| `/images/{grab_id}/download` | GET | ZIP file | For direct download |

Both endpoints:
- Require valid UUID format
- Check person exists
- Return 404 if no images found
- Order images by confidence (DESC)
