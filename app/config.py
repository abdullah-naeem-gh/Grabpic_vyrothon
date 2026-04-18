import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    PHOTO_DIR: str = "./photos"
    SIMILARITY_THRESHOLD: float = 0.4
    AUTH_THRESHOLD: float = 0.6
    MODEL_NAME: str = "VGG-Face"

    class Config:
        env_file = ".env"

settings = Settings()
