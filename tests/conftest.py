import os
import pytest
from fastapi.testclient import TestClient
from glob import glob
from dotenv import load_dotenv

# Detect if running inside Docker or locally
# Inside Docker, /app directory exists and is the working directory
IS_DOCKER = os.path.exists('/app/app') or os.getcwd() == '/app'

# Load test environment variables
if not IS_DOCKER:
    # Running locally - use .env.test with localhost
    test_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.test')
    if os.path.exists(test_env_path):
        load_dotenv(test_env_path, override=True)
    else:
        # Fallback to regular .env but update DATABASE_URL for localhost
        load_dotenv(override=True)
        if 'DATABASE_URL' in os.environ and '@db:' in os.environ['DATABASE_URL']:
            os.environ['DATABASE_URL'] = os.environ['DATABASE_URL'].replace('@db:', '@localhost:')
else:
    # Running in Docker - use existing environment (from .env)
    load_dotenv(override=False)

# Import after setting environment
from app.main import app
from app.database import get_connection, release_connection


@pytest.fixture(scope="session")
def test_client():
    """
    Create a TestClient instance for FastAPI app.
    Scope is session to reuse the same client across all tests.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def sample_image_path():
    """
    Return path to a real test image from photos/ directory.
    Uses person1.jpg which should contain a valid face.
    """
    # Use /photos (Docker) or local path based on environment
    if IS_DOCKER:
        photos_dir = "/photos"
    else:
        photos_dir = "/Users/abdullahnaeem/Projects/GrabPic_Vyrothon/photos"
    
    # Find the first valid JPG image (not the dummy text files)
    jpg_files = glob(os.path.join(photos_dir, "*.jpg"))
    
    for jpg_file in jpg_files:
        # Check if file is actually a JPEG (not ASCII text)
        if os.path.getsize(jpg_file) > 1000:  # Real images are > 1KB
            return jpg_file
    
    # Fallback to person1.jpg if nothing found
    return os.path.join(photos_dir, "person1.jpg")


@pytest.fixture(scope="session")
def sample_image_path_2():
    """
    Return path to a second test image (different person).
    Used for testing multiple face scenarios.
    """
    # Use /photos (Docker) or local path based on environment
    if IS_DOCKER:
        photos_dir = "/photos"
    else:
        photos_dir = "/Users/abdullahnaeem/Projects/GrabPic_Vyrothon/photos"
    
    # Find valid JPG images
    jpg_files = sorted(glob(os.path.join(photos_dir, "*.jpg")))
    
    valid_images = []
    for jpg_file in jpg_files:
        if os.path.getsize(jpg_file) > 1000:
            valid_images.append(jpg_file)
    
    # Return second valid image or fallback to person2.jpg
    if len(valid_images) >= 2:
        return valid_images[1]
    
    return os.path.join(photos_dir, "person2.jpg")


@pytest.fixture(scope="function")
def clean_db():
    """
    Truncate all database tables before each test.
    Ensures tests start with a clean state.
    """
    conn = get_connection()
    if not conn:
        pytest.fail("Could not connect to database for cleanup")
    
    try:
        with conn.cursor() as cur:
            # Truncate in correct order (respect foreign keys)
            cur.execute("TRUNCATE TABLE face_images CASCADE;")
            cur.execute("TRUNCATE TABLE faces CASCADE;")
            cur.execute("TRUNCATE TABLE images CASCADE;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        pytest.fail(f"Database cleanup failed: {e}")
    finally:
        release_connection(conn)
    
    yield
    
    # Optional: cleanup after test too
    conn = get_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE face_images CASCADE;")
                cur.execute("TRUNCATE TABLE faces CASCADE;")
                cur.execute("TRUNCATE TABLE images CASCADE;")
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            release_connection(conn)


@pytest.fixture(scope="session")
def temp_empty_dir(tmp_path_factory):
    """
    Create a temporary empty directory for testing empty ingestion.
    """
    empty_dir = tmp_path_factory.mktemp("empty_photos")
    return str(empty_dir)


@pytest.fixture(scope="session")
def photos_dir():
    """
    Return the path to the photos directory.
    """
    if IS_DOCKER:
        return "/photos"
    else:
        return "/Users/abdullahnaeem/Projects/GrabPic_Vyrothon/photos"
