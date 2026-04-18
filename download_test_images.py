#!/usr/bin/env python3
"""
Download test images for Grabpic validation.
Uses sample face images from various sources.
"""
import os
import requests
from pathlib import Path

# Create photos directory
photos_dir = Path("photos")
photos_dir.mkdir(exist_ok=True)

# Sample face image URLs (public domain / test images)
test_images = [
    # Different people for deduplication testing
    ("person1_a.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img1.jpg"),
    ("person1_b.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img2.jpg"),
    ("person2_a.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img3.jpg"),
    ("person2_b.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img4.jpg"),
    ("person3.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img5.jpg"),
    ("person4.jpg", "https://raw.githubusercontent.com/serengil/deepface_models/master/samples/img6.jpg"),
]

print("Downloading test images...")
downloaded = 0
for filename, url in test_images:
    filepath = photos_dir / filename
    if filepath.exists():
        print(f"  ✓ {filename} already exists")
        continue
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        filepath.write_bytes(response.content)
        print(f"  ✓ Downloaded {filename}")
        downloaded += 1
    except Exception as e:
        print(f"  ✗ Failed to download {filename}: {e}")

print(f"\nDownloaded {downloaded} new images, {len(list(photos_dir.glob('*.jpg')))} total")
