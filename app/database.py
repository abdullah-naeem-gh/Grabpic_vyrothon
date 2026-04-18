import psycopg2
from psycopg2 import pool
from .config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize connection pool
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        dsn=settings.DATABASE_URL
    )
    if db_pool:
        logger.info("Connection pool created successfully")
except (Exception, psycopg2.DatabaseError) as error:
    logger.error(f"Error while connecting to PostgreSQL: {error}")
    db_pool = None

def get_connection():
    if db_pool:
        return db_pool.getconn()
    return None

def release_connection(conn):
    if db_pool:
        db_pool.putconn(conn)

def run_migrations():
    """
    Creates pgvector extension and initializes tables.
    """
    conn = get_connection()
    if not conn:
        logger.error("Could not get a connection for migrations")
        return

    try:
        with conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # 1. images table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    file_path TEXT UNIQUE NOT NULL,
                    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. faces table
            # vector(128) as per user requirement (VGG-Face usually has a different size, but I will follow the user's explicit instruction)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS faces (
                    grab_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    embedding vector(128),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. face_images (mapping) table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS face_images (
                    grab_id UUID REFERENCES faces(grab_id) ON DELETE CASCADE,
                    image_id UUID REFERENCES images(image_id) ON DELETE CASCADE,
                    confidence FLOAT NOT NULL,
                    PRIMARY KEY (grab_id, image_id)
                );
            """)

            # Create HNSW index for cosine similarity
            cur.execute("""
                CREATE INDEX IF NOT EXISTS faces_embedding_hnsw_idx 
                ON faces USING hnsw (embedding vector_cosine_ops);
            """)

            conn.commit()
            logger.info("Database migrations completed successfully")
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f"Error during migrations: {error}")
        conn.rollback()
    finally:
        release_connection(conn)
