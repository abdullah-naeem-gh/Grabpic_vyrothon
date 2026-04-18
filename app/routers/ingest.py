import logging
import os
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, List
from ..services.ingestion import ingest_directory
from ..config import settings
from ..models import IngestResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# In-memory storage for last run stats
_last_run_stats: Dict = {}


class IngestRequest(BaseModel):
    photo_dir: Optional[str] = None


class IngestStatusResponse(BaseModel):
    last_run: Optional[Dict] = None


@router.post("", response_model=IngestResponse)
async def ingest_photos(request: IngestRequest = IngestRequest()):
    """
    Ingest photos from a directory.
    
    Args:
        request: Optional request body with photo_dir (defaults to config.PHOTO_DIR)
        
    Returns:
        Ingestion summary with processed count, faces found, skipped, and errors
    """
    global _last_run_stats
    
    # Use provided photo_dir or fall back to config default
    photo_dir = request.photo_dir if request.photo_dir else settings.PHOTO_DIR
    
    logger.info(f"Starting ingestion from directory: {photo_dir}")
    
    try:
        stats = ingest_directory(photo_dir)
        
        # Store stats for status endpoint
        _last_run_stats = {
            "photo_dir": photo_dir,
            "stats": stats
        }
        
        return IngestResponse(**stats)
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/upload", response_model=IngestResponse)
async def ingest_uploaded_files(files: List[UploadFile] = File(...)):
    """
    Ingest photos uploaded via multipart/form-data.
    Judges can test by uploading images directly via Swagger UI or curl.
    
    Args:
        files: List of image files (JPG, JPEG, PNG)
        
    Returns:
        Ingestion summary with processed count, faces found, skipped, and errors
        
    Example:
        curl -X POST http://localhost:8000/ingest/upload \\
             -F "files=@photo1.jpg" \\
             -F "files=@photo2.jpg"
    """
    global _last_run_stats
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Ensure photo directory exists
    os.makedirs(settings.PHOTO_DIR, exist_ok=True)
    
    # Create uploads subdirectory with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = os.path.join(settings.PHOTO_DIR, f"upload_{timestamp}")
    os.makedirs(upload_dir, exist_ok=True)
    
    try:
        # Save uploaded files to permanent directory
        saved_count = 0
        for upload_file in files:
            # Validate file extension
            filename = upload_file.filename.lower()
            if not filename.endswith(('.jpg', '.jpeg', '.png')):
                logger.warning(f"Skipping non-image file: {upload_file.filename}")
                continue
            
            # Save file to permanent location
            file_path = os.path.join(upload_dir, upload_file.filename)
            with open(file_path, "wb") as f:
                content = await upload_file.read()
                f.write(content)
            saved_count += 1
        
        logger.info(f"Saved {saved_count} uploaded files to {upload_dir}")
        
        # Run ingestion on permanent directory
        stats = ingest_directory(upload_dir)
        
        # Store stats for status endpoint
        _last_run_stats = {
            "source": "upload",
            "files_uploaded": saved_count,
            "upload_dir": upload_dir,
            "stats": stats
        }
        
        return IngestResponse(**stats)
        
    except Exception as e:
        logger.error(f"Upload ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/status", response_model=IngestStatusResponse)
async def get_ingest_status():
    """
    Get the status of the last ingestion run.
    
    Returns:
        Statistics from the last ingestion run, or None if no run yet
    """
    if not _last_run_stats:
        return IngestStatusResponse(last_run=None)
    
    return IngestStatusResponse(last_run=_last_run_stats)
