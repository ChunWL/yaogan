from pydantic import BaseModel
from typing import Optional
import os


class Settings(BaseModel):
    APP_NAME: str = "RSOD Detection Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    STATIC_DIR: str = "static"
    UPLOAD_DIR: str = "static/uploads"
    RESULT_DIR: str = "static/results"

    YOLO_MODEL_PATH: str = "gt.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    IOU_THRESHOLD: float = 0.45

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "models"
    MINIO_SECURE: bool = False

    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]


def get_settings() -> Settings:
    settings = Settings()
    
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    if hasattr(settings, key):
                        try:
                            setattr(settings, key, type(getattr(settings, key))(value))
                        except ValueError:
                            pass
    
    return settings


settings = get_settings()