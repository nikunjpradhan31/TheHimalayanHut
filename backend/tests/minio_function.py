from minio import Minio
import os
from dotenv import load_dotenv
from io import BytesIO
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, HTTPException
from datetime import timedelta

router = APIRouter(prefix="/minio", tags=["minio"])

load_dotenv()

MINIO_USERNAME = os.getenv("MINIO_USERNAME")
MINIO_PASSWORD = os.getenv("MINIO_PASSWORD")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")

client = Minio(endpoint=MINIO_ENDPOINT, access_key= MINIO_USERNAME, secret_key = MINIO_PASSWORD, secure = False)

#upload file (unsigned)
def upload_single_file(bucket: str, object_name: str, data: BytesIO, content_type: str):
    data.seek(0, 2) 
    size = data.tell()
    data.seek(0)
    return client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=data,
        content_type=content_type,
        length=size
    )

def upload_files_bulk_parallel(bucket: str, files: List[Dict[str, BytesIO]], content_type: str, max_workers: int = 8):
    """
    Upload multiple files in parallel to a given bucket.

    Args:
        bucket (str): MinIO bucket name.
        files (List[Dict[str, BytesIO]]): List of {"object_name": ..., "data": BytesIO}.
        content_type (str): Content-Type header to apply to all files.
        max_workers (int): Maximum number of parallel threads (default 8).
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(upload_single_file, bucket, file, content_type)
            for file in files
        ]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    return results

#file urls (presigned)
def get_presigned_image_url(bucket: str, file_key: str, expires_in: int = 60000) -> str:
    """
    Generate a presigned URL for a single image download.
    """
    url = client.presigned_get_object(bucket_name=bucket, object_name=file_key, expiry=expires_in)
    return url

def get_multiple_presigned_image_urls(bucket: str, file_keys: List[str], expires_in: int = 60000) -> List[str]:
    """
    Generate presigned URLs for multiple image downloads.
    """
    urls = {}
    for key in file_keys:
        url = client.presigned_get_object(bucket_name=bucket, object_name=key, expiry=expires_in)
        urls[key] = url
    return urls

def create_presigned_put_url(bucket_name: str, file_key: str, expires_in_seconds: int = 600):
    url = client.presigned_put_object(
        bucket_name=bucket_name,
        object_name=file_key,
        expires=timedelta(seconds=expires_in_seconds)
    )
    return url

def delete_file(bucket_name: str, file_key: str):
    client.remove_object(bucket_name, file_key)

def validate_uploaded_file(bucket_name: str, file_key: str) -> bool:
    try:
        stat = client.stat_object(bucket_name, file_key)
        if stat.size > 30 * 1024 * 1024:  
            return False
        if not stat.content_type.startswith('image/'):
            return False
        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False

#single file
@router.get("/generate_presigned_put_url/{file_key}", response_model=str)
def generate_presigned_put_url(file_key: str, expires_in_seconds: int = 600):
    """Generate a presigned URL for a single file."""
    bucket_name = "production"
    presigned_url = create_presigned_put_url(bucket_name, file_key, expires_in_seconds)
    return presigned_url

@router.post("/validate_upload")
def validate_upload(file_key: str):
    bucket = "production"

    is_valid = validate_uploaded_file(bucket, file_key)
    if not is_valid:
        delete_file(bucket, file_key)
        raise HTTPException(status_code=400, detail="File did not pass validation and was deleted.")

    return {"message": "File validated successfully!"}

