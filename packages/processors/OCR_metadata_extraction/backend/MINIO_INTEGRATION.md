# MinIO Integration for Archipelago File Uploads

This guide explains the MinIO S3 storage integration that automatically uploads files and maintains valid S3 URLs in Archipelago Commons.

## Overview

The system now automatically uploads files to MinIO when creating Archipelago digital objects with file references. This ensures:
- Valid S3 URLs in Archipelago metadata
- Files are accessible via S3 protocol
- No "500 Service unavailable" errors from missing S3 storage
- Automatic deduplication (files uploaded once, reused if already exist)

## Architecture

```
OCR Data → DataMapper → MinIO Upload → S3 URL → Archipelago Metadata
```

1. **DataMapper** checks if file should be uploaded
2. **MinIOService** handles the actual upload to MinIO
3. Real S3 URL is included in Archipelago `as:document` field
4. Files are stored with actual size, mime type, and checksum

## Components

### 1. MinIO Configuration ([app/config.py](app/config.py))

```python
# MinIO S3 Storage (for Archipelago file uploads)
MINIO_ENDPOINT = 'esmero-minio:9000'
MINIO_ACCESS_KEY = 'minio'
MINIO_SECRET_KEY = 'minio123'
MINIO_BUCKET = 'archipelago'
MINIO_SECURE = False  # Use HTTP (True for HTTPS)
MINIO_ENABLED = True
```

### 2. MinIO Service ([app/services/minio_service.py](app/services/minio_service.py))

Provides methods for:
- `upload_file()` - Upload file from disk
- `upload_file_data()` - Upload file from bytes
- `file_exists()` - Check if file already uploaded
- `get_file_info()` - Get file metadata
- `delete_file()` - Delete file
- `check_connection()` - Test MinIO connectivity

### 3. Data Mapper Integration ([app/services/data_mapper.py](app/services/data_mapper.py))

New method:
- `upload_file_to_minio()` - Upload file and return (s3_url, mime_type, file_size)

Enhanced mapping:
- Automatically uploads files when `include_file_reference=True`
- Includes real S3 URLs in Archipelago metadata
- Falls back gracefully if MinIO is unavailable

### 4. Archipelago Service ([app/services/archipelago_service.py](app/services/archipelago_service.py))

Automatically enables file uploads:
```python
archipelago_data = DataMapper.map_ocr_to_archipelago(
    ocr_data=ocr_data,
    collection_id=collection_id,
    file_id=file_id,
    include_file_reference=True  # Uploads to MinIO
)
```

## Usage

### Automatic Upload (Default Behavior)

When you upload to Archipelago using the OCR data format, files are automatically uploaded to MinIO:

```python
from app.services.archipelago_service import ArchipelagoService

# Your OCR data with file path
ocr_data = {
    "name": "document.jpg",
    "text": "OCR text...",
    "file_info": {
        "filename": "document.jpg",
        "file_path": "path/to/document.jpg"  # Must be accessible
    },
    # ... other fields
}

# Upload - files automatically go to MinIO
service = ArchipelagoService()
result = service.create_digital_object_from_ocr_data(
    ocr_data=ocr_data,
    collection_id=110,
    file_id=49
)

# Result includes node with valid S3 file reference
print(result['url'])  # Archipelago node URL
# File is now in MinIO at s3://archipelago/document.jpg
```

### Manual MinIO Upload

You can also upload files directly to MinIO:

```python
from app.services.minio_service import MinIOService

service = MinIOService()

# Upload a file
result = service.upload_file(
    file_path="/path/to/document.jpg",
    object_name="document.jpg"
)

if result:
    print(f"S3 URL: {result['s3_url']}")
    print(f"HTTP URL: {result['http_url']}")
    print(f"Size: {result['size']} bytes")
    print(f"Type: {result['content_type']}")
```

### Check if File Exists

Before uploading, check if file already exists:

```python
from app.services.minio_service import MinIOService

service = MinIOService()

if service.file_exists("document.jpg"):
    print("File already uploaded")
    file_info = service.get_file_info("document.jpg")
    print(f"Existing S3 URL: {file_info['s3_url']}")
else:
    # Upload the file
    result = service.upload_file("path/to/document.jpg")
```

### Bulk Upload with MinIO

```python
from app.services.archipelago_service import ArchipelagoService

# List of OCR data with file paths
ocr_data_list = [
    {
        "name": "doc1.jpg",
        "text": "Text from doc1...",
        "file_info": {
            "filename": "doc1.jpg",
            "file_path": "path/to/doc1.jpg"
        }
    },
    {
        "name": "doc2.jpg",
        "text": "Text from doc2...",
        "file_info": {
            "filename": "doc2.jpg",
            "file_path": "path/to/doc2.jpg"
        }
    }
]

# All files will be uploaded to MinIO automatically
service = ArchipelagoService()
result = service.create_bulk_from_ocr_data(
    ocr_data_list=ocr_data_list,
    collection_name="My Documents"
)

# All files now have valid S3 URLs in Archipelago
print(f"Uploaded {result['created_documents']} documents")
print(f"All files stored in MinIO bucket: {Config.MINIO_BUCKET}")
```

## Environment Variables

Add these to your `.env` file:

```env
# MinIO S3 Storage
MINIO_ENDPOINT=esmero-minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123
MINIO_BUCKET=archipelago
MINIO_SECURE=false
MINIO_ENABLED=true
```

## Docker Configuration

### Add Backend to Archipelago Network

Update `docker-compose.yml` to include backend in archipelago network:

```yaml
backend:
  # ... existing config
  networks:
    - gvpocr-network
    - archipelago-network  # Access to MinIO

networks:
  gvpocr-network:
    driver: bridge
  archipelago-network:
    external: true
    name: archipelago-deployment_esmero-net  # Archipelago's network
```

### MinIO Container

The existing MinIO container (`esmero-minio`) is used:
```bash
docker ps | grep minio
# Shows: esmero-minio (ports 9000-9001)
```

## S3 URL Format

Files in MinIO get S3 URLs like:
```
s3://archipelago/document.jpg
```

HTTP access URL:
```
http://esmero-minio:9000/archipelago/document.jpg
```

## File Deduplication

The system automatically prevents duplicate uploads:

1. Check if file exists in MinIO by name
2. If exists, reuse existing S3 URL
3. If not exists, upload and create new S3 URL

This saves storage and upload time for repeated files.

## Archipelago Metadata Structure

When files are uploaded, the Archipelago metadata includes:

```json
{
  "as:document": {
    "urn:uuid:...": {
      "url": "s3://archipelago/document.jpg",  // Real MinIO S3 URL
      "name": "document.jpg",
      "type": "Document",
      "dr:fid": 49,
      "dr:for": "documents",
      "dr:filesize": 245678,  // Actual file size
      "dr:mimetype": "image/jpeg",  // Detected mime type
      "crypHashFunc": "md5"
    }
  }
}
```

## Error Handling

### MinIO Unavailable

If MinIO is unavailable, the system falls back gracefully:
- Logs warning message
- Uses default S3 URL format (s3://files/...)
- Uploads metadata without actual file
- No upload failure

### File Not Found

If source file doesn't exist:
- Logs error message
- Skips file upload
- Continues with metadata-only upload
- Returns warning in result

### Permission Errors

If backend can't access file:
- Logs error with file path
- Skips file upload
- Metadata still created

## Testing

### Test MinIO Connection

```python
from app.services.minio_service import MinIOService

service = MinIOService()
if service.check_connection():
    print("✓ MinIO connected")
else:
    print("✗ MinIO connection failed")
```

### Test File Upload

```python
from app.services.minio_service import MinIOService

service = MinIOService()

# Upload test file
result = service.upload_file(
    file_path="/path/to/test.jpg",
    object_name="test.jpg"
)

if result:
    print(f"✓ Upload successful: {result['s3_url']}")

    # Verify file exists
    if service.file_exists("test.jpg"):
        print("✓ File verified in MinIO")

        # Get file info
        info = service.get_file_info("test.jpg")
        print(f"  Size: {info['size']} bytes")
        print(f"  Type: {info['content_type']}")
else:
    print("✗ Upload failed")
```

### Test with Data Mapper

```python
from app.services.data_mapper import DataMapper

# Test upload via mapper
result = DataMapper.upload_file_to_minio(
    file_path="/path/to/document.jpg",
    object_name="document.jpg"
)

if result:
    s3_url, mime_type, file_size = result
    print(f"✓ S3 URL: {s3_url}")
    print(f"  Type: {mime_type}")
    print(f"  Size: {file_size} bytes")
else:
    print("✗ Upload failed")
```

## Troubleshooting

### Connection Refused

**Problem:** Cannot connect to MinIO
```
Error: Connection refused to esmero-minio:9000
```

**Solution:** Ensure backend is on archipelago network:
```bash
docker network connect archipelago-deployment_esmero-net gvpocr-backend
```

### Access Denied

**Problem:** MinIO returns 403 Forbidden
```
Error: Access Denied
```

**Solution:** Check credentials in `.env`:
```env
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123
```

### Bucket Not Found

**Problem:** Bucket doesn't exist
```
Error: The specified bucket does not exist
```

**Solution:** Service auto-creates bucket, but you can create manually:
```bash
# Access MinIO console at http://localhost:9001
# Or use mc client:
mc mb minio/archipelago
```

### File Path Issues

**Problem:** File not found during upload
```
Error: File not found: /path/to/file.jpg
```

**Solution:** Ensure file path is correct and accessible:
- Use absolute paths
- Or relative to `GVPOCR_PATH`
- Check Docker volume mounts

## Benefits

### Before MinIO Integration
- ❌ 500 errors from invalid S3 URLs
- ❌ Files not accessible in Archipelago
- ❌ Metadata-only digital objects
- ❌ Manual file upload required

### After MinIO Integration
- ✅ Valid S3 URLs automatically
- ✅ Files accessible in Archipelago
- ✅ Complete digital objects with files
- ✅ Automatic file upload
- ✅ Deduplication saves storage
- ✅ No 500 errors

## Security Notes

1. **Credentials**: MinIO credentials are in environment variables
2. **Network**: Backend and MinIO on same Docker network
3. **Bucket Policy**: Default bucket policy (can be restricted)
4. **HTTPS**: Can enable with `MINIO_SECURE=true`

## Performance

- **Upload Speed**: Depends on file size and network
- **Deduplication**: Instant (checks before upload)
- **Concurrent Uploads**: Supported (thread-safe)
- **Large Files**: Streaming upload (memory efficient)

## Future Enhancements

Potential improvements:
- [ ] Checksum verification (MD5, SHA256)
- [ ] Parallel bulk uploads
- [ ] Progress tracking for large files
- [ ] Automatic retry on failure
- [ ] Upload to specific folders/prefixes
- [ ] Lifecycle policies for old files
- [ ] CDN integration for faster access

## Related Documentation

- [DATA_MAPPING_GUIDE.md](DATA_MAPPING_GUIDE.md) - Data mapping guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting common issues
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Archipelago Documentation](https://archipelago.nyc/)

## API Reference

### MinIOService Methods

```python
class MinIOService:
    def __init__(self)
    def check_connection(self) -> bool
    def ensure_bucket_exists(self, bucket_name: Optional[str]) -> bool
    def upload_file(self, file_path: str, object_name: Optional[str],
                    bucket_name: Optional[str], content_type: Optional[str]) -> Optional[Dict]
    def upload_file_data(self, file_data: bytes, object_name: str,
                         bucket_name: Optional[str], content_type: Optional[str]) -> Optional[Dict]
    def file_exists(self, object_name: str, bucket_name: Optional[str]) -> bool
    def get_file_info(self, object_name: str, bucket_name: Optional[str]) -> Optional[Dict]
    def delete_file(self, object_name: str, bucket_name: Optional[str]) -> bool
```

### DataMapper MinIO Method

```python
@staticmethod
def upload_file_to_minio(file_path: str, object_name: Optional[str] = None) -> Optional[Tuple[str, str, int]]
```

Returns: `(s3_url, mime_type, file_size)` or `None`
