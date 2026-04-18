import tempfile
import logging
from typing import Dict
from fastapi import HTTPException
from deepface import DeepFace
from ..config import settings
from ..database import get_connection, release_connection

logger = logging.getLogger(__name__)


def authenticate_selfie(image_bytes: bytes) -> Dict:
    """
    Authenticate a user by comparing their selfie against stored face embeddings.
    
    Args:
        image_bytes: Raw bytes of the uploaded image
        
    Returns:
        Dict with grab_id, confidence, and match_quality
        
    Raises:
        HTTPException:
            - 400: No face detected or multiple faces in selfie
            - 401: Face not recognized (distance >= AUTH_THRESHOLD)
            - 404: No faces indexed in database yet
    """
    temp_file = None
    
    try:
        # Save bytes to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(image_bytes)
        temp_file.flush()
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Extract face embedding using DeepFace
        try:
            result = DeepFace.represent(
                img_path=temp_file_path,
                model_name=settings.MODEL_NAME,
                enforce_detection=False
            )
        except Exception as e:
            logger.error(f"DeepFace error during selfie processing: {e}")
            raise HTTPException(
                status_code=400,
                detail="Could not process selfie image"
            )
        
        # Check face count
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=400,
                detail="No face detected in selfie"
            )
        
        if len(result) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple faces in selfie. Use a solo photo."
            )
        
        # Extract embedding from the single detected face
        selfie_embedding = result[0].get('embedding', [])
        if not selfie_embedding:
            raise HTTPException(
                status_code=400,
                detail="Could not extract face embedding from selfie"
            )
        
        # Query database for nearest match
        conn = get_connection()
        if not conn:
            raise HTTPException(
                status_code=500,
                detail="Database connection failed"
            )
        
        try:
            with conn.cursor() as cur:
                # First check if database has any faces
                cur.execute("SELECT COUNT(*) FROM faces;")
                face_count = cur.fetchone()[0]
                
                if face_count == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="No faces indexed yet"
                    )
                
                # Find nearest neighbor using cosine distance operator
                # pgvector uses <=> for cosine distance
                cur.execute("""
                    SELECT grab_id, embedding <=> %s::vector AS distance
                    FROM faces
                    ORDER BY distance
                    LIMIT 1;
                """, (selfie_embedding,))
                
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail="No faces indexed yet"
                    )
                
                grab_id, distance = row
                
                # Check if distance exceeds authentication threshold
                if distance >= settings.AUTH_THRESHOLD:
                    raise HTTPException(
                        status_code=401,
                        detail="Face not recognized"
                    )
                
                # Map distance to confidence and match_quality
                confidence = round(1 - distance, 4)
                
                if distance < 0.3:
                    match_quality = "high"
                elif distance < 0.45:
                    match_quality = "medium"
                else:
                    match_quality = "low"
                
                logger.info(
                    f"Authenticated grab_id={grab_id} with distance={distance:.4f}, "
                    f"confidence={confidence}, quality={match_quality}"
                )
                
                return {
                    "grab_id": grab_id,
                    "confidence": confidence,
                    "match_quality": match_quality
                }
                
        finally:
            release_connection(conn)
            
    finally:
        # Always clean up temp file
        if temp_file:
            try:
                import os
                if hasattr(temp_file, 'name') and os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                elif temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
