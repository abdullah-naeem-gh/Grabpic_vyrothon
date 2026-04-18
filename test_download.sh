#!/bin/bash

# GrabPic Image Download Test Script
# This script tests both the JSON and ZIP download endpoints

echo "======================================"
echo "GrabPic Image Download Test"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8000"

# Check if grab_id was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <grab_id>"
    echo ""
    echo "Example:"
    echo "  $0 e10bda72-9125-4632-ba9f-0776fc1b58e5"
    echo ""
    echo "Or authenticate first to get a grab_id:"
    echo "  curl -X POST $BASE_URL/auth/selfie -F \"file=@your_selfie.jpg\""
    exit 1
fi

GRAB_ID=$1

echo -e "${BLUE}Step 1: Get image paths (JSON)${NC}"
echo "--------------------------------------"
curl -s "$BASE_URL/images/$GRAB_ID" | python3 -m json.tool
echo ""
echo ""

echo -e "${BLUE}Step 2: Download images as ZIP${NC}"
echo "--------------------------------------"
OUTPUT_FILE="images_${GRAB_ID}.zip"
curl -s -o "$OUTPUT_FILE" "$BASE_URL/images/$GRAB_ID/download"

if [ -f "$OUTPUT_FILE" ]; then
    SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo -e "${GREEN}✓ Downloaded: $OUTPUT_FILE ($SIZE)${NC}"
    echo ""
    
    echo "ZIP Contents:"
    unzip -l "$OUTPUT_FILE"
    echo ""
    
    # Extract to directory
    EXTRACT_DIR="images_${GRAB_ID}"
    mkdir -p "$EXTRACT_DIR"
    unzip -q "$OUTPUT_FILE" -d "$EXTRACT_DIR"
    
    echo -e "${GREEN}✓ Extracted to: $EXTRACT_DIR/${NC}"
    echo ""
    echo "Files:"
    ls -lh "$EXTRACT_DIR/"
else
    echo "❌ Download failed"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}✓ Test Complete!${NC}"
echo "======================================"
