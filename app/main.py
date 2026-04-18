from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .database import run_migrations, get_connection, release_connection
from .routers import ingest, auth, images
from .config import settings
from contextlib import asynccontextmanager
import logging
import time

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


# HTTPException handler to ensure consistent error format
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTPException with consistent error shape.
    All error responses have an 'error' key.
    """
    # Map status codes to error messages
    status_messages = {
        400: "Bad Request",
        401: "Unauthorized",
        404: "Not Found",
        413: "Payload Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Entity",
        500: "Internal Server Error"
    }
    
    error_message = status_messages.get(exc.status_code, "Error")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_message,
            "detail": exc.detail
        }
    )


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Returns 500 with consistent error shape.
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Request validation error handler (422 errors)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors with clear messages.
    Returns 422 with consistent error shape.
    """
    errors = exc.errors()
    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
    
    # Format validation errors for clarity
    error_details = []
    for error in errors:
        location = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{location}: {error['msg']}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": "; ".join(error_details)
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with method, path, status code, and duration.
    """
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"Request started: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log response
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"status={response.status_code} duration={duration_ms:.2f}ms"
    )
    
    return response


# Include routers
app.include_router(ingest.router)
app.include_router(auth.router)
app.include_router(images.router)


@app.get("/health")
async def health():
    """
    Health check endpoint with database connection test.
    
    Returns:
        - status: "ok" if healthy
        - db: "connected" or "disconnected"
        - model: The face recognition model name
    """
    conn = get_connection()
    db_status = "disconnected"
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                result = cur.fetchone()
                if result and result[0] == 1:
                    db_status = "connected"
        except Exception as e:
            logger.error(f"Health check database query failed: {e}")
            db_status = "disconnected"
        finally:
            release_connection(conn)
    
    return {
        "status": "ok",
        "db": db_status,
        "model": settings.MODEL_NAME
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
