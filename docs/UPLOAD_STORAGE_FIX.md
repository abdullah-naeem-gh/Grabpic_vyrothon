# Upload Storage Fix

## Problem

Previously, when you uploaded images via `/ingest/upload`, they were stored in temporary directories (`/tmp/grabpic_upload_*`) that were deleted immediately after processing. This caused the `/images/{grab_id}/download` endpoint to fail with:

```json
{
  "error": "Not Found",
  "detail": "No accessible image files found"
}
```

Even though the database had references to those files, the actual image files no longer existed on disk.

## Solution

Modified `app/routers/ingest.py` to:
1. Store uploaded files in **permanent subdirectories** within `PHOTO_DIR`
2. Use timestamped directory names: `photos/upload_YYYYMMDD_HHMMSS/`
3. Keep files available for future retrieval

## How It Works Now

### Upload Flow:

1. **Upload images** via `/ingest/upload`
   ```bash
   curl -X POST http://localhost:8000/ingest/upload \
     -F "files=@image1.jpg" \
     -F "files=@image2.jpg"
   ```

2. **Files are stored permanently** in:
   ```
   /photos/upload_20260418_063203/
   ├── image1.jpg
   └── image2.jpg
   ```

3. **Database stores permanent paths**:
   ```
   /photos/upload_20260418_063203/image1.jpg
   ```

4. **Download works** because files still exist:
   ```bash
   curl -o images.zip http://localhost:8000/images/{grab_id}/download
   ```

## Testing

### Complete Test Flow:

```bash
# 1. Upload images
curl -X POST http://localhost:8000/ingest/upload \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.jpg"

# Response:
# {
#   "processed": 2,
#   "faces_found": 2,
#   "skipped": 0,
#   "errors": []
# }

# 2. Authenticate with selfie
curl -X POST http://localhost:8000/auth/selfie \
  -F "file=@selfie.jpg" | python3 -m json.tool

# Response includes grab_id:
# {
#   "grab_id": "550e8400-e29b-41d4-a716-446655440000",
#   "confidence": 0.85,
#   "match_quality": "high",
#   "authenticated": true
# }

# 3. Get image list (shows permanent paths)
curl http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000 | python3 -m json.tool

# Response:
# {
#   "grab_id": "550e8400-e29b-41d4-a716-446655440000",
#   "images": [
#     "/photos/upload_20260418_063203/photo1.jpg",
#     "/photos/upload_20260418_063203/photo2.jpg"
#   ],
#   "total": 2
# }

# 4. Download ZIP - NOW WORKS! ✅
curl -o my_images.zip \
  http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000/download

unzip -l my_images.zip
# Archive:  my_images.zip
#   Length      Date    Time    Name
# ---------  ---------- -----   ----
#    577217  04-18-2026 06:32   001_photo1_conf0.890.jpg
#    577217  04-18-2026 06:32   002_photo2_conf0.890.jpg
# ---------                     -------
#   1154434                     2 files
```

## Directory Structure

```
/photos/
├── person1.jpg              # From /ingest endpoint (directory ingestion)
├── person2.jpg
├── upload_20260418_120530/  # From /ingest/upload (API upload)
│   ├── selfie1.jpg
│   └── selfie2.jpg
└── upload_20260418_123045/  # Another upload batch
    ├── group_photo.jpg
    └── portrait.jpg
```

## What Happens to Old Temp Files?

If you have old uploads from before this fix (stored in `/tmp/grabpic_upload_*`):
- The database still has references to them
- The `/download` endpoint will skip them (with a warning in logs)
- Only accessible files are included in the ZIP
- If ALL files are inaccessible, you get a 404 error

## Benefits

✅ Uploaded images are permanently stored
✅ Download endpoint works reliably
✅ Each upload batch is isolated in its own directory
✅ Easy to track when images were uploaded
✅ No data loss after container restarts
✅ Consistent with directory-based ingestion

## Storage Management

Uploaded files are stored in Docker volumes (as defined in `docker-compose.yml`):

```yaml
volumes:
  - ./photos:/photos
```

This means:
- Files persist across container restarts
- Files are accessible on the host at `./photos/upload_*/`
- You can manually manage storage by cleaning old `upload_*` directories

## Modified Files

- `app/routers/ingest.py` - Changed `/ingest/upload` endpoint to use permanent storage
- No database schema changes required
- No configuration changes required

## Rollout

After deploying this fix:
1. All new uploads work correctly
2. Old uploads with temp paths will be skipped in downloads
3. No migration needed - system handles mixed paths gracefully
