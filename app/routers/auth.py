import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models import AuthResponse
from ..services.auth import authenticate_selfie

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/selfie", response_model=AuthResponse)
async def authenticate_with_selfie(file: UploadFile = File(...)):
    """
    Authenticate a user by uploading a selfie.
    
    - Accepts only image files (image/*)
    - Maximum file size: 10MB
    - Returns grab_id, confidence score, and match quality
    
    Edge cases handled:
    - 400: No face detected or multiple faces
    - 401: Face not recognized
    - 404: No faces in database
    - 413: File too large
    - 415: Wrong content type
    """
    
    # Validate content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported Media Type. Expected image/*, got {file.content_type}"
        )
    
    # Read file bytes
    image_bytes = await file.read()
    
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Request Entity Too Large. Maximum file size is 10MB, got {len(image_bytes)} bytes"
        )
    
    # Call authentication service
    result = authenticate_selfie(image_bytes)
    
    return AuthResponse(**result)
