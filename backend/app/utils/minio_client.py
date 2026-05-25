import os
import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
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


def ensure_buckets():
    """Create required buckets if they don't exist."""
    client = get_minio_client()
    buckets = [
        settings.MINIO_BUCKET,
        settings.MINIO_UPLOAD_BUCKET,
        settings.MINIO_RESULT_BUCKET,
        settings.MINIO_AVATAR_BUCKET,
    ]
    for bucket in buckets:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            print(f"Created MinIO bucket: {bucket}")


def upload_fileobj(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload bytes to MinIO."""
    client = get_minio_client()
    try:
        client.put_object(bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
        return True
    except S3Error as e:
        print(f"MinIO upload failed: {e}")
        return False


def upload_file(bucket: str, object_name: str, file_path: str, content_type: str = "application/octet-stream") -> bool:
    """Upload a local file to MinIO."""
    client = get_minio_client()
    try:
        client.fput_object(bucket, object_name, file_path, content_type=content_type)
        return True
    except S3Error as e:
        print(f"MinIO upload failed: {e}")
        return False


def download_file(bucket: str, object_name: str, local_path: str) -> bool:
    """Download a file from MinIO to local path."""
    client = get_minio_client()
    try:
        client.fget_object(bucket, object_name, local_path)
        return True
    except S3Error:
        return False


def delete_file(bucket: str, object_name: str) -> bool:
    """Delete an object from MinIO."""
    client = get_minio_client()
    try:
        client.remove_object(bucket, object_name)
        return True
    except S3Error as e:
        print(f"MinIO delete failed: {e}")
        return False


def file_exists(bucket: str, object_name: str) -> bool:
    """Check if an object exists in MinIO."""
    client = get_minio_client()
    try:
        client.stat_object(bucket, object_name)
        return True
    except S3Error:
        return False


def get_file_response(bucket: str, object_name: str):
    """Stream a file from MinIO as a FastAPI response."""
    client = get_minio_client()
    try:
        response = client.get_object(bucket, object_name)
        content_type = response.getheader("Content-Type", "application/octet-stream")
        return StreamingResponse(
            response.stream(32 * 1024),
            media_type=content_type,
            headers={
                "Content-Length": response.getheader("Content-Length", "0"),
                "Cache-Control": "public, max-age=86400",
            },
        )
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")


def download_model(model_key: str, local_path: str) -> bool:
    return download_file(settings.MINIO_BUCKET, model_key, local_path)
