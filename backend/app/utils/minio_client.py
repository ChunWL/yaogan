import os
from minio import Minio
from minio.error import S3Error
from app.config import settings


_minio_client = None


def get_minio_client():
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _minio_client


def download_model(model_key: str, local_path: str) -> bool:
    client = get_minio_client()
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        client.fget_object(settings.MINIO_BUCKET, model_key, local_path)
        return True
    except S3Error:
        return False
