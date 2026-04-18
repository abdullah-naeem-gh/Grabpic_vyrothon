import os
import logging
from typing import Dict
from uuid import UUID
import psycopg2
from psycopg2.extras import execute_values
from ..database import get_connection, release_connection
from ..config import settings
from .face import extract_faces

logger = logging.getLogger(__name__)

# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}


def ingest_directory(photo_dir: str) -> Dict:
    """
    Ingest all images from a directory.
    
    Args:
        photo_dir: Path to directory containing photos
        
    Returns:
        Dict with {processed: int, faces_found: int, skipped: int, errors: list}
    """
    stats = {
        'processed': 0,
        'faces_found': 0,
        'skipped': 0,
        'errors': []
    }
    
    if not os.path.exists(photo_dir):
        stats['errors'].append(f"Directory not found: {photo_dir}")
        return stats
    
    if not os.path.isdir(photo_dir):
        stats['errors'].append(f"Path is not a directory: {photo_dir}")
        return stats
    
    # Walk through directory and process each image
    for root, _, files in os.walk(photo_dir):
        for filename in files:
            # Check if file has supported extension
            _, ext = os.path.splitext(filename.lower())
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            
            file_path = os.path.join(root, filename)
            
            try:
                result = _process_single_image(file_path)
                if result['status'] == 'skipped':
                    stats['skipped'] += 1
                elif result['status'] == 'processed':
                    stats['processed'] += 1
                    stats['faces_found'] += result['faces_count']
                elif result['status'] == 'error':
                    stats['errors'].append(result['error'])
            except Exception as e:
                # Catch all exceptions per image, log and continue
                error_msg = f"Error processing {file_path}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
    
    logger.info(f"Ingestion complete: {stats}")
    return stats


def _process_single_image(file_path: str) -> Dict:
    """
    Process a single image file.
    
    Returns:
        Dict with status ('processed', 'skipped', 'error') and additional info
    """
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return {
                'status': 'error',
                'error': f"Could not get database connection for {file_path}"
            }
        
        with conn.cursor() as cur:
            # Step 1: Check if file_path already exists in images table (idempotent)
            cur.execute(
                "SELECT image_id FROM images WHERE file_path = %s;",
                (file_path,)
            )
            existing_image = cur.fetchone()
            
            if existing_image:
                logger.debug(f"Image already ingested: {file_path}")
                return {'status': 'skipped'}
            
            # Step 2: Insert into images table
            cur.execute(
                """
                INSERT INTO images (file_path) 
                VALUES (%s) 
                RETURNING image_id;
                """,
                (file_path,)
            )
            image_id = cur.fetchone()[0]
            
            # Step 3: Extract faces from image
            faces = extract_faces(file_path)
            
            if not faces:
                # No faces found - commit the image record but no face records
                conn.commit()
                logger.debug(f"No faces found in {file_path}")
                return {'status': 'processed', 'faces_count': 0}
            
            # Step 4: Process each face
            faces_processed = 0
            for face_data in faces:
                embedding = face_data['embedding']
                face_confidence = face_data['face_confidence']
                
                # Convert embedding list to string format for pgvector
                # pgvector expects a string like '[0.1, 0.2, 0.3]'
                embedding_str = str(embedding)
                
                # Query for similar faces using cosine distance
                # <=> is the pgvector cosine distance operator
                cur.execute(
                    """
                    SELECT grab_id, embedding <=> %s::vector AS distance 
                    FROM faces 
                    ORDER BY distance 
                    LIMIT 1;
                    """,
                    (embedding_str,)
                )
                similar_face = cur.fetchone()
                
                grab_id = None
                
                # Check if similar face exists and is below threshold
                if similar_face and similar_face[1] < settings.SIMILARITY_THRESHOLD:
                    # Reuse existing grab_id
                    grab_id = similar_face[0]
                    logger.debug(f"Reusing grab_id {grab_id} (distance: {similar_face[1]})")
                else:
                    # Insert new face and get new grab_id
                    cur.execute(
                        """
                        INSERT INTO faces (embedding) 
                        VALUES (%s::vector) 
                        RETURNING grab_id;
                        """,
                        (embedding_str,)
                    )
                    grab_id = cur.fetchone()[0]
                    logger.debug(f"Created new grab_id {grab_id}")
                
                # Insert into face_images junction table
                cur.execute(
                    """
                    INSERT INTO face_images (grab_id, image_id, confidence) 
                    VALUES (%s, %s, %s);
                    """,
                    (grab_id, image_id, face_confidence)
                )
                
                faces_processed += 1
            
            # Commit all changes for this image
            conn.commit()
            logger.info(f"Processed {file_path}: {faces_processed} faces")
            
            return {
                'status': 'processed',
                'faces_count': faces_processed
            }
            
    except Exception as e:
        if conn:
            conn.rollback()
        error_msg = f"Error processing {file_path}: {str(e)}"
        logger.error(error_msg)
        return {
            'status': 'error',
            'error': error_msg
        }
    finally:
        if conn:
            release_connection(conn)
