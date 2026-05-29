import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from app.config import settings


_s3_client = None


def _get_endpoint_url() -> str:
    ep = settings.S3_ENDPOINT
    if "://" in ep:
        return ep
    scheme = "https" if settings.S3_SECURE else "http"
    return f"{scheme}://{ep}"


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=_get_endpoint_url(),
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=BotoConfig(
                s3={"addressing_style": "path"},
                signature_version="s3v4",
            ),
        )
    return _s3_client


def ensure_buckets():
    """Create required buckets if they don't exist. Errors are non-fatal."""
    try:
        client = get_s3_client()
        buckets = [
            settings.S3_BUCKET,
            settings.S3_UPLOAD_BUCKET,
            settings.S3_RESULT_BUCKET,
            settings.S3_AVATAR_BUCKET,
        ]
        for bucket in buckets:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError:
                client.create_bucket(Bucket=bucket)
                print(f"Created S3 bucket: {bucket}")
    except Exception as e:
        print(f"WARNING: S3 connection failed, buckets not ensured: {e}")


def upload_fileobj(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    """Upload bytes to S3."""
    client = get_s3_client()
    try:
        client.put_object(Bucket=bucket, Key=object_name, Body=data, ContentType=content_type)
        return True
    except ClientError as e:
        print(f"S3 upload failed: {e}")
        return False


def upload_file(bucket: str, object_name: str, file_path: str, content_type: str = "application/octet-stream") -> bool:
    """Upload a local file to S3."""
    client = get_s3_client()
    try:
        client.upload_file(file_path, bucket, object_name, ExtraArgs={"ContentType": content_type})
        return True
    except ClientError as e:
        print(f"S3 upload failed: {e}")
        return False


def download_file(bucket: str, object_name: str, local_path: str) -> bool:
    """Download a file from S3 to local path."""
    client = get_s3_client()
    try:
        client.download_file(bucket, object_name, local_path)
        return True
    except ClientError:
        return False


def delete_file(bucket: str, object_name: str) -> bool:
    """Delete an object from S3."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=object_name)
        return True
    except ClientError as e:
        print(f"S3 delete failed: {e}")
        return False


def file_exists(bucket: str, object_name: str) -> bool:
    """Check if an object exists in S3."""
    client = get_s3_client()
    try:
        client.head_object(Bucket=bucket, Key=object_name)
        return True
    except ClientError:
        return False


def get_file_response(bucket: str, object_name: str):
    """Stream a file from S3 as a FastAPI response."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=bucket, Key=object_name)
        return StreamingResponse(
            response["Body"].iter_chunks(chunk_size=32 * 1024),
            media_type=response.get("ContentType", "application/octet-stream"),
            headers={
                "Content-Length": str(response.get("ContentLength", 0)),
                "Cache-Control": "public, max-age=86400",
            },
        )
    except ClientError as e:
        code = e.response["Error"].get("Code", "")
        if code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")


def download_model(model_key: str, local_path: str) -> bool:
    """Download a model file from S3 models bucket to local path."""
    return download_file(settings.S3_BUCKET, model_key, local_path)
