"""
S3 Storage Provider (AWS S3 or MinIO)
"""
import os
import logging
from typing import Dict, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)

class S3ProviderReal:
    def __init__(self):
        self.endpoint_url = os.getenv('S3_ENDPOINT')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.bucket = os.getenv('S3_BUCKET')
        self.region = os.getenv('S3_REGION', 'us-east-1')
        logger.info(f"[S3ProviderReal] Initializing with endpoint={self.endpoint_url}, bucket={self.bucket}, region={self.region}, access_key={self.access_key}, secret_key={'set' if self.secret_key else 'unset'}")
        for h in logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket]):
            logger.error(f"[S3ProviderReal] Missing S3 config: endpoint={self.endpoint_url}, access_key={self.access_key}, secret_key={'set' if self.secret_key else 'unset'}, bucket={self.bucket}")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            raise ValueError("Missing S3 configuration in environment variables")
        if boto3 is None:
            logger.error("[S3ProviderReal] boto3 is not installed!")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            raise ImportError("boto3 is required for S3ProviderReal")
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        logger.info(f"[S3ProviderReal] boto3 client initialized successfully.")
        for h in logger.handlers:
            try:
                h.flush()
            except Exception:
                pass

    def upload_file_data(self, file_data: bytes, object_name: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"[S3ProviderReal] Attempting upload: bucket={self.bucket}, object_name={object_name}, content_type={content_type}, endpoint={self.endpoint_url}")
        for h in logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
        try:
            extra_args = {'ContentType': content_type} if content_type else {}
            self.s3.put_object(Bucket=self.bucket, Key=object_name, Body=file_data, **extra_args)
            s3_url = f's3://{self.bucket}/{object_name}'
            logger.info(f"[S3ProviderReal] Uploaded file to S3: {s3_url}")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            return {
                'success': True,
                'bucket': self.bucket,
                'object_name': object_name,
                's3_url': s3_url,
                'content_type': content_type,
                'endpoint_url': self.endpoint_url,
            }
        except ClientError as e:
            logger.error(f"[S3ProviderReal] S3 upload failed: {e}", exc_info=True)
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            return {'success': False, 'error': str(e), 'bucket': self.bucket, 'object_name': object_name, 'endpoint_url': self.endpoint_url}

    def download_file_data(self, object_name: str) -> Optional[bytes]:
        logger.info(f"[S3ProviderReal] Attempting download: bucket={self.bucket}, object_name={object_name}, endpoint={self.endpoint_url}")
        for h in logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=object_name)
            logger.info(f"[S3ProviderReal] Downloaded file from S3: s3://{self.bucket}/{object_name}")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"[S3ProviderReal] S3 download failed: {e}")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            return None
