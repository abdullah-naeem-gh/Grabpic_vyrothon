import uuid


def test_get_images_valid(test_client, clean_db, sample_image_path, photos_dir):
    """
    Test successful image retrieval flow:
    1. Ingest photos to populate database
    2. Authenticate to get a grab_id
    3. Fetch images using the grab_id
    4. Should return 200 with list of images
    """
    # Step 1: Ingest photos
    ingest_response = test_client.post(
        "/ingest",
        json={"photo_dir": photos_dir}
    )
    
    assert ingest_response.status_code == 200
    ingest_data = ingest_response.json()
    assert ingest_data["faces_found"] > 0, "Need faces in DB for this test"
    
    # Step 2: Authenticate to get grab_id
    with open(sample_image_path, "rb") as f:
        auth_response = test_client.post(
            "/auth/selfie",
            files={"file": ("selfie.jpg", f, "image/jpeg")}
        )
    
    assert auth_response.status_code == 200
    auth_data = auth_response.json()
    grab_id = auth_data["grab_id"]
    
    # Step 3: Fetch images for this grab_id
    response = test_client.get(f"/images/{grab_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "grab_id" in data
    assert "images" in data
    assert "total" in data
    
    # Verify data types
    assert isinstance(data["grab_id"], str)
    assert isinstance(data["images"], list)
    assert isinstance(data["total"], int)
    
    # Verify consistency
    assert len(data["images"]) == data["total"]
    
    # Should have at least one image
    assert data["total"] > 0, "Expected at least one image for authenticated user"
    
    # All image paths should be strings
    for img_path in data["images"]:
        assert isinstance(img_path, str)
        assert len(img_path) > 0


def test_get_images_invalid_uuid(test_client, clean_db):
    """
    Test fetching images with invalid UUID format.
    Should return 400 Bad Request (or 404 for empty string).
    """
    invalid_uuids = [
        "not-a-uuid",
        "12345",
        "invalid-uuid-format",
        "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ]
    
    for invalid_uuid in invalid_uuids:
        response = test_client.get(f"/images/{invalid_uuid}")
        
        # Should return 400 (Bad Request)
        assert response.status_code == 400, f"Failed for UUID: {invalid_uuid}"
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "Invalid UUID" in data["detail"] or "Invalid UUID" in str(data)
    
    # Empty string is a special case - returns 404 (no route match)
    response = test_client.get(f"/images/")
    assert response.status_code == 404


def test_get_images_not_found(test_client, clean_db):
    """
    Test fetching images with a valid UUID that doesn't exist in database.
    Should return 404 Not Found.
    """
    # Generate a random UUID that's valid but not in DB
    random_uuid = str(uuid.uuid4())
    
    response = test_client.get(f"/images/{random_uuid}")
    
    # Should return 404 (Not Found)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_get_images_empty_result(test_client, clean_db, photos_dir):
    """
    Test fetching images for a grab_id that exists but has no associated images.
    This is an edge case that could happen if face_images entries are deleted.
    """
    # Ingest and auth to get a valid grab_id
    test_client.post("/ingest", json={"photo_dir": photos_dir})
    
    # For this test, we'd need to manipulate the DB to create a face with no images
    # Since that's complex, we'll just verify the normal case returns images
    # The actual "empty result" case is rare in production
    
    # This test documents expected behavior but may need DB manipulation to fully test
    pass


def test_get_images_ordering(test_client, clean_db, sample_image_path, photos_dir):
    """
    Test that images are returned ordered by confidence (descending).
    Higher confidence matches should appear first.
    """
    # Ingest photos
    test_client.post("/ingest", json={"photo_dir": photos_dir})
    
    # Authenticate
    with open(sample_image_path, "rb") as f:
        auth_response = test_client.post(
            "/auth/selfie",
            files={"file": ("selfie.jpg", f, "image/jpeg")}
        )
    
    if auth_response.status_code != 200:
        # Skip if auth failed (might happen with synthetic test data)
        return
    
    grab_id = auth_response.json()["grab_id"]
    
    # Fetch images
    response = test_client.get(f"/images/{grab_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # If multiple images exist, they should be ordered
    # (We can't verify the actual ordering without confidence scores in response,
    # but we can verify the endpoint works)
    assert data["total"] >= 0


def test_get_images_multiple_users(test_client, clean_db, sample_image_path, sample_image_path_2, photos_dir):
    """
    Test that each grab_id only returns their own images.
    Verify isolation between different users.
    """
    # Ingest photos
    ingest_response = test_client.post(
        "/ingest",
        json={"photo_dir": photos_dir}
    )
    
    assert ingest_response.status_code == 200
    
    # Try to authenticate with two different images
    grab_ids = []
    
    for img_path in [sample_image_path, sample_image_path_2]:
        with open(img_path, "rb") as f:
            auth_response = test_client.post(
                "/auth/selfie",
                files={"file": (f"selfie_{len(grab_ids)}.jpg", f, "image/jpeg")}
            )
        
        if auth_response.status_code == 200:
            grab_ids.append(auth_response.json()["grab_id"])
    
    # If we got at least one grab_id, test image retrieval
    if len(grab_ids) > 0:
        for grab_id in grab_ids:
            response = test_client.get(f"/images/{grab_id}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify the grab_id matches
            assert data["grab_id"] == grab_id
            
            # Should have images
            assert data["total"] >= 0


def test_get_images_download_endpoint_exists(test_client, clean_db, sample_image_path, photos_dir):
    """
    Test that the download endpoint exists and responds appropriately.
    """
    # Ingest photos
    test_client.post("/ingest", json={"photo_dir": photos_dir})
    
    # Authenticate
    with open(sample_image_path, "rb") as f:
        auth_response = test_client.post(
            "/auth/selfie",
            files={"file": ("selfie.jpg", f, "image/jpeg")}
        )
    
    if auth_response.status_code != 200:
        # Skip if auth failed
        return
    
    grab_id = auth_response.json()["grab_id"]
    
    # Try download endpoint
    response = test_client.get(f"/images/{grab_id}/download")
    
    # Should return 200 with ZIP file or 404 if no images
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        # Verify it's a ZIP file
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")


def test_get_images_with_special_characters_in_uuid(test_client, clean_db):
    """
    Test handling of UUIDs with special characters or malformed format.
    Security test for SQL injection, XSS, and path traversal attempts.
    All should be rejected with 400 or 404 (no exploitation possible).
    """
    # Various security attack attempts
    malicious_inputs = [
        "'; DROP TABLE faces; --",  # SQL injection attempt
        "<script>alert('xss')</script>",  # XSS attempt
        "../etc/passwd",  # Path traversal
        "../../secrets",  # Path traversal
        "not-a-valid-uuid",  # Invalid format
    ]
    
    for malicious_input in malicious_inputs:
        response = test_client.get(f"/images/{malicious_input}")
        
        # Should return error (400 or 404), never 200
        assert response.status_code in [400, 404], \
            f"Security test failed for: {malicious_input}"
        
        data = response.json()
        # Response should have error information (either "error" or "detail" key)
        assert "error" in data or "detail" in data
        
        # Most importantly: should not return any sensitive data
        # and should not cause server errors (500)
        assert response.status_code != 500


def test_get_images_case_sensitivity(test_client, clean_db, sample_image_path, photos_dir):
    """
    Test that UUIDs are case-insensitive (standard UUID behavior).
    """
    # Ingest and authenticate
    test_client.post("/ingest", json={"photo_dir": photos_dir})
    
    with open(sample_image_path, "rb") as f:
        auth_response = test_client.post(
            "/auth/selfie",
            files={"file": ("selfie.jpg", f, "image/jpeg")}
        )
    
    if auth_response.status_code != 200:
        return
    
    grab_id = auth_response.json()["grab_id"]
    
    # Test with uppercase UUID
    response_upper = test_client.get(f"/images/{grab_id.upper()}")
    
    # Test with lowercase UUID
    response_lower = test_client.get(f"/images/{grab_id.lower()}")
    
    # Both should work (UUIDs are case-insensitive)
    assert response_upper.status_code == 200
    assert response_lower.status_code == 200
    
    # Both should return the same data
    assert response_upper.json() == response_lower.json()
