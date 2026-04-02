import os
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("s3_test")

def get_env(key, default=None):
    value = os.environ.get(key, default)
    if value is None:
        logger.error(f"Missing required env var: {key}")
    return value

def main():
    # Load config from env
    endpoint = get_env("S3_ENDPOINT")
    access_key = get_env("S3_ACCESS_KEY")
    secret_key = get_env("S3_SECRET_KEY")
    bucket = get_env("S3_BUCKET")
    region = get_env("S3_REGION")
    
    if not all([endpoint, access_key, secret_key, bucket, region]):
        logger.error("One or more required S3 env vars are missing. Aborting test.")
        exit(1)

    logger.info(f"Testing S3 connection: endpoint={endpoint}, bucket={bucket}, region={region}")
    
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    test_key = "s3_test_file.txt"
    test_content = b"S3 connectivity test file."

    # Upload test
    try:
        logger.info(f"Uploading test file to bucket '{bucket}' as '{test_key}'...")
        s3.put_object(Bucket=bucket, Key=test_key, Body=test_content)
        logger.info("Upload successful.")
    except ClientError as e:
        logger.error(f"Upload failed: {e}")
        exit(2)

    # Download test
    try:
        logger.info(f"Downloading test file '{test_key}' from bucket '{bucket}'...")
        response = s3.get_object(Bucket=bucket, Key=test_key)
        data = response["Body"].read()
        if data == test_content:
            logger.info("Download successful and content matches.")
        else:
            logger.error("Download succeeded but content does not match!")
            exit(3)
    except ClientError as e:
        logger.error(f"Download failed: {e}")
        exit(4)

    # Cleanup
    try:
        logger.info(f"Deleting test file '{test_key}' from bucket '{bucket}'...")
        s3.delete_object(Bucket=bucket, Key=test_key)
        logger.info("Cleanup successful.")
    except ClientError as e:
        logger.warning(f"Cleanup failed: {e}")

    logger.info("S3 connectivity test PASSED.")

if __name__ == "__main__":
    main()
