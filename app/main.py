from fastapi import FastAPI
from .database import run_migrations, get_connection, release_connection
from .routers import ingest
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup migrations
    logger.info("Running database migrations...")
    run_migrations()
    yield
    # Shutdown logic (if any)
    logger.info("Shutting down...")

app = FastAPI(
    title="Grabpic Backend",
    description="Facial recognition backend for large-scale events",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(ingest.router)

@app.get("/health")
async def health():
    # Simple check for database connection
    conn = get_connection()
    db_status = "unhealthy"
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                db_status = "healthy"
        except Exception:
            db_status = "unhealthy"
        finally:
            release_connection(conn)
    
    return {
        "status": "online",
        "database": db_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
