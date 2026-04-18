import logging
import os
import io
import zipfile
from uuid import UUID
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
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
                    detail="Person not found"
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


@router.get("/{grab_id}/download")
async def download_user_images(grab_id: str):
    """
    Download all images for a given grab_id as a ZIP file.
    
    Returns:
        ZIP file containing all images for the person
    
    Error handling:
        - 400: Invalid UUID format
        - 404: Person not found or no images available
        - 500: File system or database error
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
                    detail="Person not found"
                )
            
            # Fetch all images for this grab_id
            cur.execute("""
                SELECT i.file_path, fi.confidence
                FROM face_images fi
                JOIN images i ON fi.image_id = i.image_id
                WHERE fi.grab_id = %s
                ORDER BY fi.confidence DESC;
            """, (str(grab_id_uuid),))
            
            rows = cur.fetchall()
            
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="No images found for this person"
                )
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            files_added = 0
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, (file_path, confidence) in enumerate(rows, 1):
                    # Check if file exists
                    if not os.path.exists(file_path):
                        logger.warning(f"File not found: {file_path}")
                        continue
                    
                    # Get original filename
                    original_filename = os.path.basename(file_path)
                    filename_without_ext, ext = os.path.splitext(original_filename)
                    
                    # Create new filename with confidence score
                    new_filename = f"{idx:03d}_{filename_without_ext}_conf{confidence:.3f}{ext}"
                    
                    # Add file to ZIP
                    zip_file.write(file_path, arcname=new_filename)
                    files_added += 1
                    logger.info(f"Added {file_path} to ZIP as {new_filename}")
            
            # Check if any files were added
            if files_added == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No accessible image files found"
                )
            
            zip_buffer.seek(0)
            
            # Return ZIP file
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=images_{grab_id_uuid}.zip"
                }
            )
            
    finally:
        release_connection(conn)
