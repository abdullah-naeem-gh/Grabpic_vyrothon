import logging
from typing import List, Dict
from deepface import DeepFace
from ..config import settings

logger = logging.getLogger(__name__)


def extract_faces(image_path: str) -> List[Dict]:
    """
    Extract face embeddings from an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of dicts with {embedding: list[float], face_confidence: float}
        Returns empty list if no faces detected or on error (never raises)
    """
    try:
        # Use DeepFace.represent to extract face embeddings
        # enforce_detection=False prevents crashes on partial/unclear faces
        result = DeepFace.represent(
            img_path=image_path,
            model_name=settings.MODEL_NAME,
            enforce_detection=False
        )
        
        # DeepFace.represent returns a list of dicts, one per face
        faces = []
        for face_data in result:
            # Extract confidence - DeepFace returns it in the face_confidence field
            face_confidence = face_data.get('face_confidence', 0.0)
            
            # Filter out low confidence faces (< 0.85)
            if face_confidence < 0.85:
                logger.debug(f"Skipping face with low confidence: {face_confidence}")
                continue
            
            embedding = face_data.get('embedding', [])
            if not embedding:
                logger.warning(f"Face detected but no embedding in {image_path}")
                continue
                
            faces.append({
                'embedding': embedding,
                'face_confidence': face_confidence
            })
        
        logger.info(f"Extracted {len(faces)} faces from {image_path}")
        return faces
        
    except Exception as e:
        # Never raise - return empty list on any error
        logger.error(f"Error extracting faces from {image_path}: {e}")
        return []
