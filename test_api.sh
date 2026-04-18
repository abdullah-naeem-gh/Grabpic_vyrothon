#!/bin/bash

# Grabpic API Test Script
# Tests all endpoints with various scenarios

echo "======================================"
echo "Grabpic API Testing Script"
echo "======================================"
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to check HTTP status
check_status() {
    local expected=$1
    local actual=$2
    local test_name=$3
    
    if [ "$actual" == "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name (Status: $actual)"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name (Expected: $expected, Got: $actual)"
        ((TESTS_FAILED++))
    fi
}

echo "1. Testing Health Endpoint"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/health)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "200" "$HTTP_CODE" "Health check"
echo ""

echo "2. Testing Ingestion Endpoint"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/ingest \
  -H "Content-Type: application/json" \
  -d '{"photo_dir": "/photos"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "200" "$HTTP_CODE" "Ingest photos"
echo ""

echo "3. Testing Selfie Authentication - Valid User"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/auth/selfie \
  -F "file=@photos/person1.jpg")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "200" "$HTTP_CODE" "Auth with valid selfie"

# Extract grab_id for later use
GRAB_ID=$(echo "$BODY" | python3 -c "import json,sys; print(json.load(sys.stdin)['grab_id'])" 2>/dev/null)
echo "Extracted grab_id: $GRAB_ID"
echo ""

echo "4. Testing Image Retrieval - Valid grab_id"
echo "-----------------------------------"
if [ -n "$GRAB_ID" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/images/$GRAB_ID)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    echo "Response: $BODY"
    check_status "200" "$HTTP_CODE" "Get images for valid grab_id"
else
    echo -e "${YELLOW}⚠ SKIP${NC}: No grab_id available"
fi
echo ""

echo "5. Testing Edge Cases - Invalid UUID"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/images/not-a-uuid)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "400" "$HTTP_CODE" "Invalid UUID format"
echo ""

echo "6. Testing Edge Cases - Non-existent grab_id"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" $BASE_URL/images/00000000-0000-0000-0000-000000000000)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "404" "$HTTP_CODE" "Non-existent grab_id"
echo ""

echo "7. Testing Edge Cases - Wrong Content Type"
echo "-----------------------------------"
echo "test" > /tmp/test.txt
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/auth/selfie \
  -F "file=@/tmp/test.txt;type=text/plain")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "415" "$HTTP_CODE" "Wrong content type"
rm /tmp/test.txt
echo ""

echo "8. Testing Edge Cases - File Too Large"
echo "-----------------------------------"
dd if=/dev/zero of=/tmp/large_image.jpg bs=1M count=11 2>/dev/null
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/auth/selfie \
  -F "file=@/tmp/large_image.jpg;type=image/jpeg")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "Response: $BODY"
check_status "413" "$HTTP_CODE" "File too large"
rm /tmp/large_image.jpg
echo ""

echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
