import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
from ..services.ingestion import ingest_directory
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# In-memory storage for last run stats
_last_run_stats: Dict = {}


class IngestRequest(BaseModel):
    photo_dir: Optional[str] = None


class IngestResponse(BaseModel):
    processed: int
    faces_found: int
    skipped: int
    errors: List[str]


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
