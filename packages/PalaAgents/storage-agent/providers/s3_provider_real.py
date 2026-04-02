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
        
        # Replica config
        self.replica_enabled = os.getenv('S3_ENABLE_REPLICA', 'false').lower() == 'true'
        self.replica_endpoint_url = os.getenv('S3_REPLICA_ENDPOINT')
        self.replica_access_key = os.getenv('S3_REPLICA_ACCESS_KEY')
        self.replica_secret_key = os.getenv('S3_REPLICA_SECRET_KEY')
        self.replica_bucket = os.getenv('S3_REPLICA_BUCKET')
        self.replica_region = os.getenv('S3_REPLICA_REGION', 'us-east-1')
        
        logger.info(f"[S3ProviderReal] Initializing PRIMARY: endpoint={self.endpoint_url}, bucket={self.bucket}, region={self.region}")
        if self.replica_enabled:
            logger.info(f"[S3ProviderReal] Initializing REPLICA: endpoint={self.replica_endpoint_url}, bucket={self.replica_bucket}, region={self.replica_region}")
        for h in logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
                
        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket]):
            logger.error(f"[S3ProviderReal] Missing PRIMARY S3 config: endpoint={self.endpoint_url}, access_key={self.access_key}, secret_key={'set' if self.secret_key else 'unset'}, bucket={self.bucket}")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            raise ValueError("Missing S3 configuration in environment variables")
            
        if self.replica_enabled and not all([self.replica_endpoint_url, self.replica_access_key, self.replica_secret_key, self.replica_bucket]):
            logger.warning(f"[S3ProviderReal] Replica enabled but missing config: endpoint={self.replica_endpoint_url}, access_key={self.replica_access_key}, secret_key={'set' if self.replica_secret_key else 'unset'}, bucket={self.replica_bucket}")
            self.replica_enabled = False
            
        if boto3 is None:
            logger.error("[S3ProviderReal] boto3 is not installed!")
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            raise ImportError("boto3 is required for S3ProviderReal")
            
        # Initialize primary S3 client
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        logger.info(f"[S3ProviderReal] PRIMARY boto3 client initialized successfully.")
        
        # Initialize replica S3 client if enabled
        self.s3_replica = None
        if self.replica_enabled:
            try:
                self.s3_replica = boto3.client(
                    's3',
                    endpoint_url=self.replica_endpoint_url,
                    aws_access_key_id=self.replica_access_key,
                    aws_secret_access_key=self.replica_secret_key,
                    region_name=self.replica_region,
                )
                logger.info(f"[S3ProviderReal] REPLICA boto3 client initialized successfully.")
            except Exception as e:
                logger.error(f"[S3ProviderReal] Failed to initialize REPLICA client: {e}")
                self.s3_replica = None
                self.replica_enabled = False
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
            logger.info(f"[S3ProviderReal] PRIMARY upload success: {s3_url}")
            
            # Replicate to replica bucket if enabled
            replica_result = None
            if self.replica_enabled and self.s3_replica:
                try:
                    self.s3_replica.put_object(Bucket=self.replica_bucket, Key=object_name, Body=file_data, **extra_args)
                    replica_url = f's3://{self.replica_bucket}/{object_name}'
                    logger.info(f"[S3ProviderReal] REPLICA upload success: {replica_url}")
                    replica_result = {
                        'success': True,
                        'bucket': self.replica_bucket,
                        'object_name': object_name,
                        's3_url': replica_url,
                        'content_type': content_type,
                        'endpoint_url': self.replica_endpoint_url,
                    }
                except ClientError as e:
                    logger.warning(f"[S3ProviderReal] REPLICA upload failed (non-critical): {e}")
                    replica_result = {'success': False, 'error': str(e), 'bucket': self.replica_bucket}
            
            for h in logger.handlers:
                try:
                    h.flush()
                except Exception:
                    pass
                    
            return {
                'success': True,
                'primary': {
                    'bucket': self.bucket,
                    'object_name': object_name,
                    's3_url': s3_url,
                    'content_type': content_type,
                    'endpoint_url': self.endpoint_url,
                },
                'replica': replica_result,
            }
        except ClientError as e:
            logger.error(f"[S3ProviderReal] PRIMARY S3 upload failed: {e}", exc_info=True)
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
