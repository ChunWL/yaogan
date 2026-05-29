from pydantic import BaseModel
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
    VIDEO_RESULT_DIR: str = "data/videos"
    VIDEO_FRAME_INTERVAL: int = 5
    VIDEO_TASK_TIMEOUT: int = 300

    YOLO_MODEL_PATH: str = "gt.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    IOU_THRESHOLD: float = 0.45

    S3_ENDPOINT: str = "localhost:9000"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "models"
    S3_UPLOAD_BUCKET: str = "uploads"
    S3_RESULT_BUCKET: str = "results"
    S3_AVATAR_BUCKET: str = "avatars"
    S3_SECURE: bool = False

    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    PUBLIC_URL: str = ""  # 生产环境设为后端域名，如 https://yaogan.onrender.com

    DATABASE_URL: str = "postgresql://rsod_user:rsod_password@localhost:5432/rsod_db"
    JWT_SECRET_KEY: str = "yaogan-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440


def _parse_env_value(value: str, target_type: type):
    """Parse a string value into the target type."""
    if target_type == bool:
        return value.lower() in ("true", "1", "yes")
    if target_type == list:
        return [v.strip() for v in value.split(",") if v.strip()]
    return target_type(value)


def _load_from_env_file(settings: Settings):
    """Apply .env file values (lowest priority, for local dev)."""
    env_file = ".env"
    if not os.path.exists(env_file):
        return
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            if hasattr(settings, key) and key not in os.environ:
                try:
                    setattr(settings, key, _parse_env_value(value, type(getattr(settings, key))))
                except (ValueError, TypeError):
                    pass


def _load_from_os_environ(settings: Settings):
    """Apply os.environ values (highest priority)."""
    # Backward compat: map old MINIO_* env var names to new S3_* settings
    _env_aliases = {
        "MINIO_ENDPOINT": "S3_ENDPOINT",
        "MINIO_ACCESS_KEY": "S3_ACCESS_KEY",
        "MINIO_SECRET_KEY": "S3_SECRET_KEY",
        "MINIO_BUCKET": "S3_BUCKET",
        "MINIO_UPLOAD_BUCKET": "S3_UPLOAD_BUCKET",
        "MINIO_RESULT_BUCKET": "S3_RESULT_BUCKET",
        "MINIO_AVATAR_BUCKET": "S3_AVATAR_BUCKET",
        "MINIO_SECURE": "S3_SECURE",
    }
    for old_key, new_key in _env_aliases.items():
        if old_key in os.environ and new_key not in os.environ:
            os.environ[new_key] = os.environ[old_key]

    for key in settings.model_fields:
        env_val = os.environ.get(key)
        if env_val is not None:
            try:
                setattr(settings, key, _parse_env_value(env_val, type(getattr(settings, key))))
            except (ValueError, TypeError):
                pass

    # Always respect PORT from Render
    port = os.environ.get("PORT")
    if port is not None:
        settings.PORT = int(port)

    # Support DATABASE_URL from Render managed PostgreSQL
    db_url = os.environ.get("DATABASE_URL")
    if db_url is not None:
        settings.DATABASE_URL = db_url


def get_settings() -> Settings:
    settings = Settings()
    _load_from_env_file(settings)
    _load_from_os_environ(settings)
    return settings


settings = get_settings()