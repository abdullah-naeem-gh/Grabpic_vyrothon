from pydantic import BaseModel
from typing import List
from uuid import UUID


class AuthResponse(BaseModel):
    """Response model for selfie authentication"""
    grab_id: UUID
    confidence: float
    match_quality: str
    authenticated: bool = True


class IngestResponse(BaseModel):
    """Response model for image ingestion"""
    processed: int
    faces_found: int
    skipped: int
    errors: List[str] = []


class ImageListResponse(BaseModel):
    """Response model for fetching user images"""
    grab_id: UUID
    images: List[str]
    total: int
