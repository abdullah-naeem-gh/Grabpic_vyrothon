# Quick Start: Error Handling in GrabPic

## For Developers Adding New Endpoints

All error handling is centralized in `app/main.py`. When adding new endpoints, you only need to:

### 1. Raise HTTPException for known errors

```python
from fastapi import HTTPException

# Example: Invalid input
raise HTTPException(
    status_code=400,
    detail="Invalid input: ..."
)

# Example: Resource not found
raise HTTPException(
    status_code=404,
    detail="Resource not found"
)

# Example: Unauthorized
raise HTTPException(
    status_code=401,
    detail="Authentication failed"
)
```

The global handlers in `main.py` will automatically:
- Add the `"error"` key to the response
- Map the status code to a human-readable error type
- Log the error appropriately

### 2. Let unexpected errors bubble up

Don't catch general exceptions - let them propagate to the global exception handler:

```python
# ❌ DON'T DO THIS:
try:
    result = some_operation()
except Exception as e:
    return {"message": str(e)}  # Raw exception, inconsistent format

# ✅ DO THIS:
result = some_operation()  # Let exceptions bubble up
```

The global exception handler will:
- Catch all unhandled exceptions
- Log the full stack trace
- Return a consistent 500 error response
- Never leak raw Python exceptions to clients

### 3. Database operations

Always use the connection pool properly:

```python
from ..database import get_connection, release_connection

conn = get_connection()
if not conn:
    raise HTTPException(status_code=500, detail="Database connection failed")

try:
    with conn.cursor() as cur:
        cur.execute("SELECT ...")
        result = cur.fetchall()
finally:
    release_connection(conn)  # Always release!
```

## Error Response Format

All error responses automatically follow this format:

```json
{
  "error": "<Error Type>",
  "detail": "<Specific message>"
}
```

| Status | Error Type | When to Use |
|--------|-----------|-------------|
| 400 | Bad Request | Invalid input, validation failed |
| 401 | Unauthorized | Authentication failed |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | File/request too large |
| 415 | Unsupported Media Type | Wrong content type |
| 422 | Unprocessable Entity | Request validation error |
| 500 | Internal Server Error | Unexpected server error |

## Logging

All requests are automatically logged with:
- Start: method and path
- End: status code and duration

No additional logging code needed in your endpoints!

## Testing Your Endpoint

```bash
# Test your endpoint
curl http://localhost:8000/your/endpoint

# Check logs
docker compose logs app --tail 20

# Verify error format has "error" key
curl http://localhost:8000/your/endpoint/invalid-input | python3 -m json.tool
```

## Summary

✅ Just raise `HTTPException` with appropriate status codes
✅ Let unexpected errors bubble up to global handler
✅ Always release database connections
✅ Don't catch general exceptions
✅ No need to format error responses manually
✅ All logging happens automatically

That's it! The centralized error handling takes care of the rest.
