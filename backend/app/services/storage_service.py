import os
import uuid
import logging
from typing import Optional
import aioboto3
from fastapi import UploadFile

from app.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    @staticmethod
    def get_s3_client_args() -> dict:
        """Returns the connection args for aioboto3 based on settings"""
        return {
            "service_name": "s3",
            "endpoint_url": settings.r2_endpoint_url,
            "aws_access_key_id": settings.r2_access_key_id,
            "aws_secret_access_key": settings.r2_secret_access_key,
            # R2 doesn't use standard regions, but boto3 requires it
            "region_name": "auto", 
        }

    @staticmethod
    async def upload_file(upload_file: UploadFile) -> Optional[str]:
        """
        Uploads a file to Cloudflare R2 and returns the R2 object key (filename).
        """
        if not settings.r2_bucket_name or not settings.r2_access_key_id:
            logger.error("R2 credentials not configured.")
            return None

        # Generate a unique filename to prevent collisions
        filename = upload_file.filename or "unknown"
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Read file content
        file_content = await upload_file.read()
        
        session = aioboto3.Session()
        async with session.client(**StorageService.get_s3_client_args()) as s3_client:
            try:
                # Upload to R2
                await s3_client.put_object(
                    Bucket=settings.r2_bucket_name,
                    Key=unique_filename,
                    Body=file_content,
                    ContentType=upload_file.content_type
                )
                logger.info(f"Successfully uploaded {unique_filename} to R2")
                return unique_filename
            except Exception as e:
                logger.error(f"Failed to upload file to R2: {str(e)}")
                return None

    @staticmethod
    async def upload_translated_file(object_key: str, file_bytes: bytes, original_filename: str) -> bool:
        """
        Uploads the translated file to Cloudflare R2 with the correct ContentType.
        """
        if not settings.r2_bucket_name or not settings.r2_access_key_id:
            logger.error("R2 credentials not configured.")
            return False

        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''
        content_type_map = {
            'txt': 'text/plain; charset=utf-8',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'pdf': 'application/pdf',
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

        session = aioboto3.Session()
        async with session.client(**StorageService.get_s3_client_args()) as s3_client:
            try:
                await s3_client.put_object(
                    Bucket=settings.r2_bucket_name,
                    Key=object_key,
                    Body=file_bytes,
                    ContentType=content_type,
                    ContentDisposition=f'attachment; filename="{original_filename}"',
                )
                logger.info(f"Successfully uploaded translated file {object_key} to R2")
                return True
            except Exception as e:
                logger.error(f"Failed to upload translated file to R2: {str(e)}")
                return False

    @staticmethod
    async def get_presigned_url(object_key: str, expires_in: int = 3600, download_filename: str | None = None) -> Optional[str]:
        """
        Generates a presigned URL for secure access to the file.
        Passing download_filename will add Content-Disposition: attachment so browsers auto-download.
        """
        if not settings.r2_bucket_name or not settings.r2_access_key_id:
            logger.error("R2 credentials not configured.")
            return None

        session = aioboto3.Session()
        async with session.client(**StorageService.get_s3_client_args()) as s3_client:
            try:
                params = {
                    'Bucket': settings.r2_bucket_name,
                    'Key': object_key,
                }
                if download_filename:
                    params['ResponseContentDisposition'] = f'attachment; filename="{download_filename}"'
                url = await s3_client.generate_presigned_url(
                    'get_object',
                    Params=params,
                    ExpiresIn=expires_in
                )
                return url
            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {str(e)}")
                return None
