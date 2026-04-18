#!/bin/bash

# Script to run tests inside Docker container
# Runs each test file separately to avoid memory issues

echo "================================"
echo "Running GrabPic Test Suite"
echo "================================"
echo ""

# Ensure dependencies are installed
echo "Installing test dependencies..."
docker exec grabpic_app pip install -q pytest pytest-asyncio "httpx==0.25.2" pillow
echo ""

# Run test_ingest.py
echo "Running tests/test_ingest.py..."
docker exec grabpic_app python -m pytest tests/test_ingest.py -v
INGEST_EXIT=$?
echo ""

# Restart container to free memory
echo "Restarting container to free memory..."
docker compose restart app > /dev/null 2>&1
sleep 3
docker exec grabpic_app pip install -q pytest pytest-asyncio "httpx==0.25.2" pillow
echo ""

# Run test_auth.py
echo "Running tests/test_auth.py..."
docker exec grabpic_app python -m pytest tests/test_auth.py -v
AUTH_EXIT=$?
echo ""

# Restart container again
echo "Restarting container to free memory..."
docker compose restart app > /dev/null 2>&1
sleep 3
docker exec grabpic_app pip install -q pytest pytest-asyncio "httpx==0.25.2" pillow
echo ""

# Run test_images.py
echo "Running tests/test_images.py..."
docker exec grabpic_app python -m pytest tests/test_images.py -v
IMAGES_EXIT=$?
echo ""

echo "================================"
echo "Test Summary"
echo "================================"
echo "test_ingest.py: $([ $INGEST_EXIT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "test_auth.py: $([ $AUTH_EXIT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "test_images.py: $([ $IMAGES_EXIT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo ""

if [ $INGEST_EXIT -eq 0 ] && [ $AUTH_EXIT -eq 0 ] && [ $IMAGES_EXIT -eq 0 ]; then
    echo "All tests PASSED ✓"
    exit 0
else
    echo "Some tests FAILED ✗"
    exit 1
fi
