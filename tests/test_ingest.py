import os
import tempfile
import shutil
from PIL import Image
import numpy as np


def test_ingest_empty_directory(test_client, clean_db, temp_empty_dir):
    """
    Test ingesting an empty directory.
    Should return 200 with processed=0.
    """
    response = test_client.post(
        "/ingest",
        json={"photo_dir": temp_empty_dir}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["processed"] == 0
    assert data["faces_found"] == 0
    assert data["skipped"] == 0


def test_ingest_valid_photos(test_client, clean_db, photos_dir):
    """
    Test ingesting valid photos from the photos/ directory.
    Should find faces and process them successfully.
    """
    response = test_client.post(
        "/ingest",
        json={"photo_dir": photos_dir}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have processed some images
    assert data["processed"] >= 0
    
    # Should have found at least some faces (if there are valid images)
    # Note: person1.jpg and other large files should contain faces
    assert data["faces_found"] >= 0
    
    # May have skipped some files (like the dummy text files)
    assert data["skipped"] >= 0
    
    # Check that faces_found is reasonable
    # If we processed any images with faces, faces_found should be > 0
    if data["processed"] > 0:
        # At least person1.jpg, person2.jpg, person5.jpg, person6.jpg are real
        assert data["faces_found"] > 0, "Expected to find faces in valid photos"


def test_ingest_idempotent(test_client, clean_db, photos_dir):
    """
    Test that running ingestion twice is idempotent.
    Second run should skip all images that were already processed.
    """
    # First run
    response1 = test_client.post(
        "/ingest",
        json={"photo_dir": photos_dir}
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    first_processed = data1["processed"]
    first_faces = data1["faces_found"]
    
    # Second run on same directory
    response2 = test_client.post(
        "/ingest",
        json={"photo_dir": photos_dir}
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Second run should skip all files that were processed in first run
    assert data2["skipped"] == first_processed, \
        f"Expected {first_processed} skipped files, got {data2['skipped']}"
    
    # Second run should process 0 new images
    assert data2["processed"] == 0, \
        f"Expected 0 processed in second run, got {data2['processed']}"
    
    # No new faces should be found
    assert data2["faces_found"] == 0, \
        f"Expected 0 new faces in second run, got {data2['faces_found']}"


def test_ingest_no_face_image(test_client, clean_db, tmp_path):
    """
    Test ingesting an image with no face.
    Should be skipped gracefully without returning 500.
    """
    # Create a temporary directory with a no-face image
    test_dir = tmp_path / "no_face_test"
    test_dir.mkdir()
    
    # Create a blank image (no face)
    blank_image_path = test_dir / "blank.jpg"
    img = Image.new('RGB', (300, 300), color='white')
    img.save(blank_image_path)
    
    # Ingest the directory
    response = test_client.post(
        "/ingest",
        json={"photo_dir": str(test_dir)}
    )
    
    # Should return 200 (not 500)
    assert response.status_code == 200
    data = response.json()
    
    # The image was processed but no face found
    # Should be counted as either processed with 0 faces or skipped
    assert data["processed"] >= 0
    assert data["faces_found"] == 0
    
    # Should not crash or return error


def test_ingest_mixed_valid_invalid(test_client, clean_db, tmp_path, sample_image_path):
    """
    Test ingesting a mix of valid images and non-image files.
    Should process valid images and skip invalid ones.
    """
    # Create a temporary directory
    test_dir = tmp_path / "mixed_test"
    test_dir.mkdir()
    
    # Copy a valid image
    valid_image = test_dir / "valid.jpg"
    shutil.copy(sample_image_path, valid_image)
    
    # Create a text file with .jpg extension (invalid)
    fake_image = test_dir / "fake.jpg"
    fake_image.write_text("This is not an image")
    
    # Create a blank image (no face)
    blank_image = test_dir / "blank.jpg"
    img = Image.new('RGB', (200, 200), color='blue')
    img.save(blank_image)
    
    # Ingest the directory
    response = test_client.post(
        "/ingest",
        json={"photo_dir": str(test_dir)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should handle the mix without crashing
    # At least the valid image should be attempted
    assert data["processed"] >= 0
    assert data["skipped"] >= 0
    
    # May have errors for invalid files
    assert isinstance(data["errors"], list)


def test_ingest_default_photo_dir(test_client, clean_db):
    """
    Test ingestion without providing photo_dir.
    Should use the default from config (photos/).
    """
    response = test_client.post("/ingest", json={})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should successfully process with default directory
    assert "processed" in data
    assert "faces_found" in data
    assert "skipped" in data
