import os
import mimetypes
import uuid
from app.config import settings
from app.utils.s3_client import upload_file, delete_file


def _content_type(filename: str) -> str:
    ct, _ = mimetypes.guess_type(filename)
    return ct or "application/octet-stream"


def ensure_directories():
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_RESULT_DIR, exist_ok=True)


def get_file_url(filename: str, directory: str) -> str:
    bucket = "uploads" if "uploads" in directory else "results"
    base = settings.PUBLIC_URL or ""
    return f"{base}/api/files/{bucket}/{filename}"


async def save_upload_file(file, upload_dir: str) -> str:
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    bucket = settings.S3_UPLOAD_BUCKET
    upload_file(bucket, filename, filepath, _content_type(filename))

    return filename


def upload_result_to_minio(filename: str, filepath: str) -> None:
    """Upload a result image to MinIO after detection."""
    bucket = settings.S3_RESULT_BUCKET
    upload_file(bucket, filename, filepath, _content_type(filename))


def delete_result_from_minio(filename: str) -> None:
    """Delete a result image from MinIO."""
    bucket = settings.S3_RESULT_BUCKET
    delete_file(bucket, filename)


def delete_upload_from_minio(filename: str) -> None:
    """Delete an uploaded image from MinIO."""
    bucket = settings.S3_UPLOAD_BUCKET
    delete_file(bucket, filename)
