import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException
from ..models import ImageListResponse
from ..database import get_connection, release_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["Images"])


@router.get("/{grab_id}", response_model=ImageListResponse)
async def get_user_images(grab_id: str):
    """
    Retrieve all images for a given grab_id.
    
    Returns:
        - grab_id: The user's unique identifier
        - images: List of image file paths
        - total: Count of images
    
    Error handling:
        - 400: Invalid UUID format
        - 404: grab_id not found in database
    """
    
    # Validate UUID format
    try:
        grab_id_uuid = UUID(grab_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid UUID format: {grab_id}"
        )
    
    # Query database
    conn = get_connection()
    if not conn:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )
    
    try:
        with conn.cursor() as cur:
            # Check if grab_id exists
            cur.execute(
                "SELECT COUNT(*) FROM faces WHERE grab_id = %s;",
                (str(grab_id_uuid),)
            )
            if cur.fetchone()[0] == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"grab_id not found: {grab_id}"
                )
            
            # Fetch all images for this grab_id, ordered by confidence descending
            cur.execute("""
                SELECT i.file_path, fi.confidence
                FROM face_images fi
                JOIN images i ON fi.image_id = i.image_id
                WHERE fi.grab_id = %s
                ORDER BY fi.confidence DESC;
            """, (str(grab_id_uuid),))
            
            rows = cur.fetchall()
            
            # Extract file paths
            images = [row[0] for row in rows]
            
            return ImageListResponse(
                grab_id=grab_id_uuid,
                images=images,
                total=len(images)
            )
            
    finally:
        release_connection(conn)
