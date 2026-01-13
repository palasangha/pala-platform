import os
import csv
import json
import logging
import zipfile
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import urllib3

from app.config import Config

logger = logging.getLogger(__name__)


class AMIService:
    """Service for creating and managing Archipelago AMI Sets"""

    def __init__(self):
        self.base_url = Config.ARCHIPELAGO_BASE_URL
        self.username = Config.ARCHIPELAGO_USERNAME
        self.password = Config.ARCHIPELAGO_PASSWORD
        self.enabled = Config.ARCHIPELAGO_ENABLED
        self.session = None
        self.csrf_token = None
        
        # Configure SSL verification
        self.verify_ssl = os.getenv('ARCHIPELAGO_VERIFY_SSL', 'true').lower() == 'true'
        
        if not self.verify_ssl:
            logger.warning("⚠️  SSL verification disabled for Archipelago - development only!")
            # Suppress urllib3 SSL warnings
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _login(self) -> Optional[str]:
        """Login to Archipelago and get CSRF token"""
        try:
            # Create session BEFORE login so cookies are automatically managed
            self.session = requests.Session()
            self.session.verify = self.verify_ssl

            login_url = f"{self.base_url}/user/login?_format=json"
            logger.info(f"Logging in to Archipelago at {login_url} (SSL verify={self.verify_ssl})")

            # Use session.post so cookies are automatically stored
            response = self.session.post(
                login_url,
                json={'name': self.username, 'pass': self.password},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            self.csrf_token = result.get('csrf_token')

            if not self.csrf_token:
                logger.error("Login response did not contain csrf_token")
                logger.debug(f"Login response: {result}")
                return None

            logger.info(f"Successfully logged in to Archipelago (CSRF token: {self.csrf_token[:20]}...)")
            logger.debug(f"Session cookies: {self.session.cookies}")

            return self.csrf_token

        except Exception as e:
            logger.error(f"Failed to login to Archipelago: {str(e)}", exc_info=True)
            return None

    def diagnose_archipelago_endpoints(self) -> Dict[str, Any]:
        """
        Diagnose Archipelago endpoints and permissions
        Returns a report of what's working and what's not
        """
        if not self.csrf_token:
            self._login()

        if not self.csrf_token:
            return {'error': 'Authentication failed'}

        report = {
            'authentication': 'OK',
            'endpoints': {}
        }

        # Test various endpoints
        test_endpoints = [
            ('/amiset/add', 'GET', 'AMI Set creation form'),
            ('/ami/new', 'GET', 'AMI new form'),
            ('/amiset/list', 'GET', 'AMI Set list'),
            ('/jsonapi/ami_set_entity/ami_set_entity', 'GET', 'AMI Set JSON:API'),
            ('/jsonapi/file/file', 'GET', 'File JSON:API'),
            ('/file/upload', 'GET', 'File upload REST'),
            ('/admin/content/amiset', 'GET', 'AMI Set admin'),
        ]

        logger.info("=== Archipelago Endpoint Diagnostics ===")

        for path, method, description in test_endpoints:
            url = f"{self.base_url}{path}"
            try:
                if method == 'GET':
                    response = self.session.get(url, timeout=10)
                else:
                    response = self.session.post(url, timeout=10)

                status = response.status_code
                accessible = status in [200, 201, 302, 403]  # 403 means endpoint exists but forbidden

                report['endpoints'][path] = {
                    'status': status,
                    'accessible': accessible,
                    'description': description,
                    'content_type': response.headers.get('Content-Type', 'unknown')
                }

                logger.info(f"  [{status}] {path} - {description}")
                if status == 403:
                    logger.warning(f"    → Forbidden (endpoint exists but no permission)")
                elif status == 404:
                    logger.warning(f"    → Not found")
                elif status in [200, 201]:
                    logger.info(f"    → OK")

            except Exception as e:
                report['endpoints'][path] = {
                    'error': str(e),
                    'accessible': False,
                    'description': description
                }
                logger.error(f"  [ERROR] {path} - {str(e)}")

        logger.info("=== End Diagnostics ===")
        return report

    def _resolve_file_path(self, file_path: str) -> str:
        """Resolve relative file paths to absolute paths"""
        if os.path.isabs(file_path):
            return file_path

        gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')

        if file_path.startswith('Bhushanji/'):
            return os.path.join(gvpocr_path, file_path[10:])
        else:
            return os.path.join(gvpocr_path, file_path)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename: spaces -> underscores, limit 200 chars"""
        import re
        sanitized = filename.replace(' ', '_')
        sanitized = re.sub(r'[^\w\-.]', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized[:200]

    class ValidationResult:
        """Result of source file validation"""
        def __init__(self):
            self.valid = True
            self.total_files = 0
            self.found_files = []
            self.missing_files = []
            self.validation_errors = []

        def to_dict(self):
            return {
                'valid': self.valid,
                'total_files': self.total_files,
                'found': len(self.found_files),
                'missing': len(self.missing_files),
                'missing_files': self.missing_files,
                'errors': self.validation_errors
            }

    def validate_source_files(self, ocr_data_list: List[Dict]) -> 'AMIService.ValidationResult':
        """Validate ALL source files exist before creating AMI Set"""
        result = self.ValidationResult()
        result.total_files = len(ocr_data_list)

        for ocr_data in ocr_data_list:
            file_info = ocr_data.get('file_info', {})
            file_path = self._resolve_file_path(file_info.get('file_path', ''))
            filename = file_info.get('filename', '')

            if not file_path or not os.path.exists(file_path):
                result.valid = False
                result.missing_files.append(file_path or filename)
                result.validation_errors.append(f"File not found: {filename}")
            else:
                result.found_files.append(file_path)

        return result

    def generate_ocr_text_files(self, ocr_data_list: List[Dict[str, Any]], output_dir: str) -> List[str]:
        """Generate individual .txt file for each document with FULL OCR text"""
        text_dir = os.path.join(output_dir, 'ocr_text')
        os.makedirs(text_dir, exist_ok=True)

        generated_files = []

        for ocr_data in ocr_data_list:
            filename = ocr_data.get('file_info', {}).get('filename', '')
            if not filename:
                continue

            base_name = self.sanitize_filename(os.path.splitext(filename)[0])
            text_filename = f"{base_name}_ocr.txt"
            text_path = os.path.join(text_dir, text_filename)

            full_text = ocr_data.get('text', '')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(full_text)

            generated_files.append(text_path)
            logger.debug(f"Generated OCR text: {text_filename} ({len(full_text)} chars)")

        return generated_files

    def generate_metadata_files(self, ocr_data_list: List[Dict[str, Any]], output_dir: str) -> List[str]:
        """Generate individual .json file for each document with OCR metadata"""
        from datetime import datetime

        metadata_dir = os.path.join(output_dir, 'ocr_metadata')
        os.makedirs(metadata_dir, exist_ok=True)

        generated_files = []

        for ocr_data in ocr_data_list:
            filename = ocr_data.get('file_info', {}).get('filename', '')
            if not filename:
                continue

            base_name = self.sanitize_filename(os.path.splitext(filename)[0])
            metadata_filename = f"{base_name}_metadata.json"
            metadata_path = os.path.join(metadata_dir, metadata_filename)

            # Get processing_date and convert to ISO format if it's a datetime object
            processing_date = ocr_data.get('ocr_metadata', {}).get('processing_date', '')
            if isinstance(processing_date, datetime):
                processing_date = processing_date.isoformat()

            metadata = {
                'provider': ocr_data.get('ocr_metadata', {}).get('provider', ''),
                'confidence': ocr_data.get('ocr_metadata', {}).get('confidence', 0),
                'detected_language': ocr_data.get('ocr_metadata', {}).get('language', ''),
                'processing_date': processing_date,
                'file_info': {
                    'filename': ocr_data.get('file_info', {}).get('filename', ''),
                    'file_path': str(ocr_data.get('file_info', {}).get('file_path', ''))
                },
                'text_length': len(ocr_data.get('text', ''))
            }

            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            generated_files.append(metadata_path)

        return generated_files

    def generate_thumbnails(self, ocr_data_list: List[Dict[str, Any]], output_dir: str) -> List[str]:
        """Generate thumbnail previews: PDFs -> first page, Images -> resized"""
        from PIL import Image
        import subprocess

        thumb_dir = os.path.join(output_dir, 'thumbnails')
        os.makedirs(thumb_dir, exist_ok=True)

        generated_thumbnails = []
        THUMB_SIZE = (300, 300)

        for ocr_data in ocr_data_list:
            file_info = ocr_data.get('file_info', {})
            file_path = self._resolve_file_path(file_info.get('file_path', ''))
            filename = file_info.get('filename', '')

            if not filename:
                continue

            if not os.path.exists(file_path):
                logger.warning(f"Source file not found for thumbnail: {file_path}")
                continue

            base_name = self.sanitize_filename(os.path.splitext(filename)[0])
            thumb_filename = f"{base_name}_thumb.jpg"
            thumb_path = os.path.join(thumb_dir, thumb_filename)

            try:
                ext = os.path.splitext(file_path)[1].lower()

                if ext == '.pdf':
                    # Use pdftoppm to extract first page as JPG
                    subprocess.run([
                        'pdftoppm', '-jpeg', '-f', '1', '-l', '1',
                        '-scale-to', '300', file_path,
                        os.path.splitext(thumb_path)[0]
                    ], check=True, capture_output=True)

                    # Rename output file (pdftoppm creates prefix-1.jpg)
                    temp_thumb = f"{os.path.splitext(thumb_path)[0]}-1.jpg"
                    if os.path.exists(temp_thumb):
                        os.rename(temp_thumb, thumb_path)

                elif ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
                    # Resize image using PIL
                    img = Image.open(file_path)
                    img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
                    img.convert('RGB').save(thumb_path, 'JPEG', quality=85)

                if os.path.exists(thumb_path):
                    generated_thumbnails.append(thumb_path)
                    logger.debug(f"Generated thumbnail: {thumb_filename}")

            except Exception as e:
                logger.error(f"Error generating thumbnail for {filename}: {e}")
                continue

        return generated_thumbnails

    def create_csv_from_ocr_data(
        self,
        ocr_data_list: List[Dict[str, Any]],
        output_path: str,
        collection_id: Optional[int] = None,
        ami_set_dir: Optional[str] = None
    ) -> bool:
        """
        Create CSV file from OCR data for AMI ingestion per Archipelago specifications

        Reference: https://docs.archipelago.nyc/1.4.0/ami_index/

        Args:
            ocr_data_list: List of OCR result dictionaries
            output_path: Path where CSV file should be created
            collection_id: Optional collection node ID for ismemberof field
            ami_set_dir: Optional directory containing generated files (text, metadata, thumbnails)

        Returns:
            True if CSV created successfully, False otherwise
        """
        try:
            # Define CSV headers per Archipelago's requirements
            # Required columns: node_uuid, type, label
            # File columns: documents, images, videos, audios, model
            # Metadata columns: any Strawberry Field metadata fields
            headers = [
                # Essential Archipelago columns (per docs)
                'node_uuid',           # Must be unique; auto-generated if not provided
                'type',                # Content type (e.g., 'DigitalDocument')
                'label',               # Title/label for the object (required)
                'description',         # Description field

                # File field columns - Archipelago extracts from ZIP and assigns FIDs
                'documents',           # PDF/document filenames from ZIP
                'images',              # Image filenames (JPG, PNG, TIF, etc)

                # Enhanced file references (new columns for full artifacts)
                'ocr_text_file',       # Reference to full OCR text file
                'ocr_metadata_file',   # Reference to metadata JSON file
                'thumbnail',           # Reference to thumbnail image

                'ismemberof',          # Collection node ID for parent relationship

                # Metadata columns (stored in Strawberry Field JSON)
                'language',            # Language code
                'owner',               # Owner/organization
                'rights',              # Rights statement
                'creator',             # Creator

                # OCR-specific metadata (stored in Strawberry Field as custom fields)
                'ocr_text_preview',    # First 500 chars of OCR text (for CSV preview)
                'ocr_provider',        # OCR provider used
                'ocr_confidence',      # OCR confidence score
                'ocr_language',        # Detected language from OCR
                'ocr_processing_date', # Date OCR was processed
            ]

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()

                for ocr_data in ocr_data_list:
                    # Generate UUID for this node (required by Archipelago)
                    import uuid
                    node_uuid = str(uuid.uuid4())

                    # Extract data from OCR results
                    file_info = ocr_data.get('file_info', {})
                    ocr_metadata = ocr_data.get('ocr_metadata', {})
                    filename = file_info.get('filename', '')

                    # Validate required fields
                    if not filename:
                        logger.warning(f"Skipping record: no filename provided")
                        continue

                    label = ocr_data.get('label', ocr_data.get('name', filename))
                    if not label:
                        logger.warning(f"Skipping record: no label for {filename}")
                        continue

                    # Determine file column based on extension (per Archipelago file type mapping)
                    file_column = 'documents'  # Default to documents
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                        file_column = 'images'
                    elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        file_column = 'videos'
                    elif filename.lower().endswith(('.mp3', '.wav', '.flac', '.aac')):
                        file_column = 'audios'

                    # Build CSV row with all required and optional fields
                    # Per Archipelago docs: all fields are optional except node_uuid, type, label

                    # Generate sanitized base filename for references to generated files
                    base_name = self.sanitize_filename(os.path.splitext(filename)[0])

                    row = {
                        # Required fields
                        'node_uuid': node_uuid,  # Unique identifier for this ADO
                        'type': 'DigitalDocument',  # Content type
                        'label': label,  # Required title/label

                        # Description
                        'description': ocr_data.get('description', f"OCR processed: {filename}"),

                        # Initialize ALL file columns to empty string
                        # Archipelago requires these columns to exist (even if empty)
                        'documents': '',  # PDF/document files
                        'images': '',     # Image files

                        # Enhanced file references (new columns)
                        'ocr_text_file': f"{base_name}_ocr.txt",
                        'ocr_metadata_file': f"{base_name}_metadata.json",
                        'thumbnail': f"{base_name}_thumb.jpg",

                        # Collection membership (optional)
                        'ismemberof': str(collection_id) if collection_id else '',

                        # Metadata fields (stored in Strawberry Field JSON)
                        'language': ocr_metadata.get('language', 'en').title() or 'English',
                        'owner': 'Vipassana Research Institute',
                        'rights': 'All rights Owned by Vipassana Research Institute',
                        'creator': 'VRI',

                        # OCR-specific metadata (custom fields in Strawberry Field)
                        'ocr_text_preview': ocr_data.get('text', '')[:500],  # First 500 chars
                        'ocr_provider': ocr_metadata.get('provider', ''),
                        'ocr_confidence': ocr_metadata.get('confidence', ''),
                        'ocr_language': ocr_metadata.get('language', ''),
                        'ocr_processing_date': ocr_metadata.get('processing_date', ''),
                    }

                    # Override the appropriate file column with actual filename
                    row[file_column] = filename

                    writer.writerow(row)

            logger.info(f"Created CSV file with {len(ocr_data_list)} rows: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating CSV file: {str(e)}", exc_info=True)
            return False

    def create_zip_from_files(
        self,
        ocr_data_list: List[Dict[str, Any]],
        output_path: str,
        ami_set_dir: Optional[str] = None
    ) -> bool:
        """
        Create flat ZIP file containing all artifacts for AMI ingestion

        Args:
            ocr_data_list: List of OCR result dictionaries
            output_path: Path where ZIP file should be created
            ami_set_dir: Directory containing staged files (source_files, ocr_text, ocr_metadata, thumbnails)

        Returns:
            True if ZIP created successfully, False otherwise
        """
        try:
            files_added = 0
            files_failed = 0

            # If ami_set_dir provided, use staged directories (PRIMARY METHOD)
            if ami_set_dir:
                logger.info(f"Creating ZIP from job directory: {ami_set_dir}")
                
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from subdirectories with flat structure
                    # Order: source_files first, then metadata/artifacts
                    subdirs = ['source_files', 'ocr_text', 'ocr_metadata', 'thumbnails']
                    
                    for subdir in subdirs:
                        dir_path = os.path.join(ami_set_dir, subdir)
                        
                        if not os.path.exists(dir_path):
                            logger.debug(f"Subdirectory not found: {dir_path}")
                            continue
                        
                        if not os.path.isdir(dir_path):
                            logger.warning(f"Path is not a directory: {dir_path}")
                            continue
                        
                        try:
                            files_in_subdir = os.listdir(dir_path)
                            logger.debug(f"Found {len(files_in_subdir)} files in {subdir}")
                            
                            for filename in files_in_subdir:
                                file_path = os.path.join(dir_path, filename)
                                
                                # Only add files, skip directories
                                if os.path.isfile(file_path):
                                    try:
                                        # Add with flat structure (no subdirectories in ZIP)
                                        zipf.write(file_path, arcname=filename)
                                        files_added += 1
                                        logger.debug(f"Added to ZIP: {filename} (from {subdir})")
                                    except Exception as e:
                                        logger.error(f"Failed to add {filename} to ZIP: {e}")
                                        files_failed += 1
                                else:
                                    logger.debug(f"Skipping non-file: {filename}")
                        
                        except OSError as e:
                            logger.error(f"Error reading directory {dir_path}: {e}")
                            continue

                # Verify ZIP integrity and report
                try:
                    with zipfile.ZipFile(output_path, 'r') as zipf:
                        file_list = zipf.namelist()
                        zip_size = os.path.getsize(output_path)
                        logger.info(f"✓ Created ZIP file: {output_path}")
                        logger.info(f"  Total files in ZIP: {len(file_list)}")
                        logger.info(f"  ZIP file size: {zip_size:,} bytes ({zip_size / (1024*1024):.2f} MB)")
                        logger.info(f"  Files added: {files_added}, Failed: {files_failed}")
                        
                        if files_failed > 0:
                            logger.warning(f"  ⚠ {files_failed} files failed to add")
                        
                        # List files in ZIP for debugging
                        logger.debug(f"  Files in ZIP:")
                        for f in sorted(file_list)[:10]:  # Show first 10
                            logger.debug(f"    - {f}")
                        if len(file_list) > 10:
                            logger.debug(f"    ... and {len(file_list) - 10} more")
                        
                        return len(file_list) > 0  # Success if ZIP has files
                
                except zipfile.BadZipFile as e:
                    logger.error(f"ZIP file validation failed: {e}")
                    return False

            # Fallback: Legacy method if ami_set_dir not provided
            # (for backward compatibility)
            logger.warning("Creating ZIP using legacy method (ami_set_dir not provided)")
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ocr_data in ocr_data_list:
                    file_info = ocr_data.get('file_info', {})
                    file_path = file_info.get('file_path', '')
                    filename = file_info.get('filename', '')

                    # Skip if no file path provided
                    if not file_path:
                        logger.warning(f"No file path provided for {filename}, skipping")
                        files_failed += 1
                        continue

                    # Resolve file path if relative
                    if not os.path.isabs(file_path):
                        gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')

                        # Handle case where file_path starts with 'Bhushanji/'
                        if file_path.startswith('Bhushanji/'):
                            file_path = os.path.join(gvpocr_path, file_path[10:])
                        else:
                            file_path = os.path.join(gvpocr_path, file_path)

                    # Check if file exists
                    if os.path.exists(file_path):
                        try:
                            zipf.write(file_path, arcname=filename)
                            files_added += 1
                            logger.debug(f"Added to ZIP: {filename}")
                        except Exception as e:
                            logger.error(f"Failed to add {filename}: {e}")
                            files_failed += 1
                    else:
                        logger.warning(f"File not found: {file_path}")
                        files_failed += 1

            logger.info(f"✓ Created ZIP file: {output_path}")
            logger.info(f"  Files added: {files_added}, Failed: {files_failed}")
            return files_added > 0

        except Exception as e:
            logger.error(f"Error creating ZIP file: {str(e)}", exc_info=True)
            return False

    def upload_file_multipart(
        self,
        file_path: str,
        filename: Optional[str] = None,
        field_name: str = 'files[]'
    ) -> Optional[int]:
        """
        Upload a file to Archipelago using multipart/form-data (webform style)

        Args:
            file_path: Path to file to upload
            filename: Optional filename (defaults to basename of file_path)
            field_name: Form field name (default: 'files[]')

        Returns:
            File entity ID (fid) if successful, None otherwise
        """
        if not self.csrf_token:
            self._login()

        if not self.csrf_token or not self.session:
            logger.error("Cannot upload file - authentication not initialized")
            return None

        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            if not filename:
                filename = os.path.basename(file_path)

            file_size = os.path.getsize(file_path)
            logger.info(f"Uploading '{filename}' ({file_size / (1024*1024):.2f} MB) via multipart form...")

            # Try multipart/form-data upload endpoints
            upload_endpoints = [
                # Drupal REST file upload (multipart)
                f"{self.base_url}/file/upload/ami_set_entity/ami_set_entity/field_source_data",
                f"{self.base_url}/file/upload/ami_set_entity/ami_set_entity/field_zip_file",
                f"{self.base_url}/file/upload",
            ]

            for endpoint_url in upload_endpoints:
                logger.debug(f"  Trying multipart endpoint: {endpoint_url}")

                try:
                    with open(file_path, 'rb') as f:
                        files = {field_name: (filename, f, 'application/octet-stream')}
                        headers = {
                            'X-CSRF-Token': self.csrf_token,
                            # Let requests set Content-Type with boundary
                        }

                        response = self.session.post(
                            f"{endpoint_url}?_format=json",
                            files=files,
                            headers=headers,
                            timeout=300
                        )

                        if response.status_code in [200, 201]:
                            logger.info(f"✓ Multipart upload succeeded: {endpoint_url}")

                            try:
                                result = response.json()
                                # Extract FID from response
                                fid = None
                                if 'fid' in result:
                                    fid_data = result['fid']
                                    if isinstance(fid_data, list):
                                        fid = fid_data[0].get('value') if fid_data else None
                                    elif isinstance(fid_data, int):
                                        fid = fid_data

                                if fid:
                                    logger.info(f"  File ID (FID): {fid}")
                                    return fid
                                else:
                                    logger.warning(f"  Response missing FID: {result}")
                            except Exception as e:
                                logger.error(f"  Error parsing response: {e}")
                                logger.error(f"  Response: {response.text[:500]}")
                        else:
                            logger.debug(f"  Status {response.status_code}: {response.text[:200]}")

                except Exception as e:
                    logger.debug(f"  Endpoint failed: {str(e)}")
                    continue

            logger.warning("All multipart upload attempts failed")
            return None

        except Exception as e:
            logger.error(f"Error in multipart upload: {str(e)}", exc_info=True)
            return None

    def upload_file_to_archipelago(
        self,
        file_path: str,
        filename: Optional[str] = None,
        field_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Upload a file to Archipelago and get file entity ID
        Tries multiple upload methods for maximum compatibility

        Args:
            file_path: Path to file to upload
            filename: Optional filename (defaults to basename of file_path)

        Returns:
            File entity ID (fid) if successful, None otherwise
        """
        if not self.csrf_token:
            self._login()

        if not self.csrf_token or not self.session:
            logger.error("Cannot upload file - authentication not initialized")
            logger.debug(f"  csrf_token: {bool(self.csrf_token)}, session: {bool(self.session)}")
            return None

        # METHOD 1: Try multipart/form-data upload first (most compatible)
        logger.info("Attempting upload method 1: multipart/form-data")
        fid = self.upload_file_multipart(file_path, filename)
        if fid:
            return fid

        logger.warning("Multipart upload failed, trying binary upload methods...")

        # METHOD 2: Try binary upload with multiple endpoints
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            if not filename:
                filename = os.path.basename(file_path)

            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Log file details
            logger.debug(f"Uploading file: {filename}")
            logger.debug(f"  Path: {file_path}")
            logger.debug(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")

            with open(file_path, 'rb') as f:
                file_content = f.read()

            # CRITICAL FIX for HTTP 415: Archipelago JSON:API ONLY accepts application/octet-stream
            # The error "No route found that matches Content-Type: text/csv" means Archipelago
            # rejects ANY specific MIME type (text/csv, application/zip, image/jpeg, etc.)
            # It REQUIRES application/octet-stream for the binary file data
            content_type = 'application/octet-stream'  # MUST use this - Archipelago only accepts this
            
            logger.debug(f"  File: {filename}")
            logger.debug(f"  Using Content-Type: {content_type} (Archipelago JSON:API requirement)")

            # Determine file extension to detect file type
            file_ext = os.path.splitext(filename)[1].lower()

            # Try alternative upload endpoints based on Drupal configuration
            # Different Archipelago instances may have different endpoints enabled

            # Option 1: Try REST API endpoint (most compatible)
            # This is the traditional Drupal file upload endpoint
            upload_endpoints = [
                # REST API endpoint - most compatible with older Drupal/Archipelago
                {
                    'url': f"{self.base_url}/file/upload/ami_set_entity/ami_set_entity/zip_file?_format=json",
                    'headers': {
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'file; filename="{filename}"',
                        'X-CSRF-Token': self.csrf_token
                    },
                    'name': 'REST API (ami_set zip_file field)'
                },
                # Generic REST upload endpoint
                {
                    'url': f"{self.base_url}/file/upload?_format=json",
                    'headers': {
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'file; filename="{filename}"',
                        'X-CSRF-Token': self.csrf_token
                    },
                    'name': 'REST API (generic)'
                },
                # JSON:API endpoint (newer Drupal)
                {
                    'url': f"{self.base_url}/jsonapi/file/file",
                    'headers': {
                        'Content-Type': 'application/octet-stream',
                        'Accept': 'application/vnd.api+json',
                        'Content-Disposition': f'file; filename="{filename}"',
                        'X-CSRF-Token': self.csrf_token
                    },
                    'name': 'JSON:API'
                }
            ]

            logger.info(f"Uploading '{filename}' ({file_size / (1024*1024):.2f} MB) to Archipelago...")

            # Try each endpoint until one succeeds
            response = None
            last_error = None

            for endpoint_config in upload_endpoints:
                endpoint_url = endpoint_config['url']
                headers = endpoint_config['headers']
                endpoint_name = endpoint_config['name']

                logger.debug(f"  Trying endpoint: {endpoint_name}")
                logger.debug(f"  URL: {endpoint_url}")
                logger.debug(f"  Headers: {headers}")

                try:
                    response = self.session.post(
                        endpoint_url,
                        data=file_content,
                        headers=headers,
                        timeout=300  # 5 minute timeout for large files
                    )

                    if response.status_code in [200, 201]:
                        logger.info(f"✓ Successfully uploaded using: {endpoint_name}")
                        break
                    else:
                        logger.warning(f"  {endpoint_name} failed with status {response.status_code}")
                        last_error = f"{endpoint_name}: HTTP {response.status_code}"

                except Exception as e:
                    logger.warning(f"  {endpoint_name} error: {str(e)}")
                    last_error = f"{endpoint_name}: {str(e)}"
                    continue

            if not response or response.status_code not in [200, 201]:
                logger.error(f"❌ All upload endpoints failed!")
                logger.error(f"  Last error: {last_error}")
                if response:
                    logger.error(f"  Last response status: {response.status_code}")
                    logger.error(f"  Last response body: {response.text[:500]}")
                return None

            # Parse JSON response with error handling
            try:
                result = response.json()
            except ValueError as json_err:
                logger.error(f"❌ Failed to parse Archipelago response as JSON!")
                logger.error(f"  Filename: {filename}")
                logger.error(f"  Status code: {response.status_code}")
                logger.error(f"  Content-Type: {response.headers.get('Content-Type')}")
                logger.error(f"  Response body (first 500 chars): {response.text[:500]}")
                logger.error(f"  JSON parse error: {json_err}")
                return None

            # Extract file ID - handle both REST API and JSON:API response formats
            fid = None

            # JSON:API format: {"data": {"attributes": {"drupal_internal__fid": 123}}}
            if 'data' in result:
                file_data = result.get('data', {})
                fid = file_data.get('attributes', {}).get('drupal_internal__fid')
                logger.debug(f"  Parsed JSON:API format response")

            # REST API format: {"fid": [{"value": 123}]} or {"fid": 123}
            elif 'fid' in result:
                fid_data = result.get('fid')
                if isinstance(fid_data, list) and len(fid_data) > 0:
                    fid = fid_data[0].get('value')
                elif isinstance(fid_data, int):
                    fid = fid_data
                logger.debug(f"  Parsed REST API format response")

            # Fallback: try to find fid anywhere in response
            if not fid:
                # Try common field names
                for field in ['drupal_internal__fid', 'id', 'file_id', 'entity_id']:
                    if field in result:
                        fid = result[field]
                        logger.debug(f"  Found FID in field: {field}")
                        break

            if fid:
                logger.info(f"✓ Successfully uploaded '{filename}'")
                logger.info(f"  File ID (FID): {fid}")
                logger.info(f"  Size: {file_size / (1024*1024):.2f} MB")
                return fid
            else:
                logger.error(f"❌ File upload response missing FID!")
                logger.error(f"  Response: {result}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"❌ Upload timeout for '{filename}' - file may be too large")
            logger.error(f"  Check Archipelago connectivity and server performance")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error uploading '{filename}': {e}")
            logger.error(f"  Is Archipelago accessible at {self.base_url}?")
            return None
        except Exception as e:
            logger.error(f"❌ Error uploading file '{filename}': {str(e)}", exc_info=True)
            return None

    def create_ami_set_via_selenium(
        self,
        name: str,
        csv_path: str,
        zip_path: Optional[str] = None,
        collection_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an AMI Set using Selenium WebDriver for JavaScript-rendered forms

        Args:
            name: Name for the AMI Set
            csv_path: Path to CSV file with metadata
            zip_path: Optional path to ZIP file with source files
            collection_id: Optional collection node ID for membership

        Returns:
            Dictionary with AMI Set info or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        if not self.csrf_token:
            self._login()

        if not self.csrf_token:
            return None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            import re

            logger.info("Creating AMI Set via Selenium WebDriver...")

            # Configure Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # Create WebDriver
            driver = None
            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)

                # Transfer session cookies to Selenium
                logger.info("Transferring authenticated session to Selenium...")
                driver.get(self.base_url)

                # Add cookies from requests session
                for cookie in self.session.cookies:
                    cookie_dict = {
                        'name': cookie.name,
                        'value': cookie.value,
                        'domain': cookie.domain,
                        'path': cookie.path,
                        'secure': cookie.secure
                    }
                    try:
                        driver.add_cookie(cookie_dict)
                    except Exception as e:
                        logger.debug(f"Could not add cookie {cookie.name}: {e}")

                # Try multiple form URLs
                form_urls = [
                    f"{self.base_url}/amiset/add",
                    f"{self.base_url}/ami/new",
                    f"{self.base_url}/node/add/ami_set_entity",
                ]

                form_loaded = False
                for url in form_urls:
                    logger.info(f"Attempting to load form: {url}")
                    try:
                        driver.get(url)

                        # Wait for form to load
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "form"))
                        )

                        logger.info(f"✓ Form loaded successfully from: {url}")
                        form_loaded = True
                        break

                    except TimeoutException:
                        logger.debug(f"Timeout loading form from: {url}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error loading form from {url}: {e}")
                        continue

                if not form_loaded:
                    logger.error("✗ Could not load AMI Set form from any URL")
                    logger.error(f"  Tried URLs: {form_urls}")
                    return None

                # Find and fill the name field
                logger.info("Filling form fields...")
                try:
                    name_field = driver.find_element(By.CSS_SELECTOR, "input[name*='name']")
                    name_field.clear()
                    name_field.send_keys(name)
                    logger.info(f"  ✓ Set name: {name}")
                except NoSuchElementException:
                    logger.error("  ✗ Could not find name field")
                    return None

                # Find and upload CSV file
                try:
                    csv_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    csv_uploaded = False

                    for file_input in csv_inputs:
                        field_name = file_input.get_attribute('name') or ''
                        if 'source' in field_name.lower() or 'csv' in field_name.lower():
                            if os.path.exists(csv_path):
                                file_input.send_keys(os.path.abspath(csv_path))
                                logger.info(f"  ✓ Uploaded CSV to field: {field_name}")
                                csv_uploaded = True
                                break

                    if not csv_uploaded:
                        logger.error("  ✗ Could not find CSV upload field or upload failed")
                        return None

                except Exception as e:
                    logger.error(f"  ✗ Error uploading CSV: {e}")
                    return None

                # Find and upload ZIP file (if provided)
                if zip_path and os.path.exists(zip_path):
                    try:
                        csv_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                        zip_uploaded = False

                        for file_input in csv_inputs:
                            field_name = file_input.get_attribute('name') or ''
                            if 'zip' in field_name.lower():
                                file_input.send_keys(os.path.abspath(zip_path))
                                logger.info(f"  ✓ Uploaded ZIP to field: {field_name}")
                                zip_uploaded = True
                                break

                        if not zip_uploaded:
                            logger.warning("  ⚠ Could not find ZIP upload field")

                    except Exception as e:
                        logger.warning(f"  ⚠ Error uploading ZIP: {e}")

                # Fill collection field if provided
                if collection_id:
                    try:
                        collection_field = driver.find_element(
                            By.CSS_SELECTOR,
                            "input[name*='ismemberof'], input[name*='collection']"
                        )
                        collection_field.clear()
                        collection_field.send_keys(str(collection_id))
                        logger.info(f"  ✓ Set collection: {collection_id}")
                    except NoSuchElementException:
                        logger.debug("  Collection field not found (may not be required)")

                # Submit the form
                logger.info("Submitting form...")
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                    submit_button.click()

                    # Wait for navigation/success message
                    import time
                    time.sleep(3)

                    current_url = driver.current_url
                    page_source = driver.page_source

                    logger.info(f"  Form submitted. Current URL: {current_url}")

                    # Check for success
                    ami_set_id = None
                    match = re.search(r'/amiset/(\d+)', current_url)
                    if not match:
                        match = re.search(r'/ami_set_entity/(\d+)', current_url)

                    if match:
                        ami_set_id = match.group(1)
                        logger.info(f"✓ Created AMI Set: {name} (ID: {ami_set_id})")
                        return {
                            'success': True,
                            'ami_set_id': ami_set_id,
                            'name': name,
                            'message': f'AMI Set created successfully. Process it at: {self.base_url}/amiset/{ami_set_id}/process'
                        }

                    # Check for success message in page
                    if 'has been created' in page_source or 'successfully' in page_source.lower():
                        logger.info(f"✓ AMI Set created (ID not found in URL)")
                        return {
                            'success': True,
                            'message': 'AMI Set created successfully'
                        }

                    # Check for error messages
                    if 'error' in page_source.lower() or 'required' in page_source.lower():
                        logger.error("✗ Form submission may have failed - error messages detected")
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(page_source, 'html.parser')
                        error_messages = soup.find_all(['div', 'span'], class_=lambda x: x and ('error' in x.lower() or 'message' in x.lower()))
                        for msg in error_messages[:5]:
                            logger.error(f"    - {msg.get_text().strip()[:200]}")

                    logger.error("✗ Form submission result unclear")
                    logger.debug(f"  Page excerpt: {page_source[:500]}")
                    return None

                except Exception as e:
                    logger.error(f"✗ Error submitting form: {e}")
                    return None

            finally:
                if driver:
                    driver.quit()
                    logger.debug("Selenium WebDriver closed")

        except ImportError as e:
            logger.error(f"Selenium not installed: {e}")
            logger.error("Install with: pip install selenium webdriver-manager")
            return None
        except Exception as e:
            logger.error(f"Error creating AMI Set via Selenium: {str(e)}", exc_info=True)
            return None

    def create_ami_set_via_webform(
        self,
        name: str,
        csv_path: str,
        zip_path: Optional[str] = None,
        collection_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an AMI Set via proper Drupal form submission with tokens

        Args:
            name: Name for the AMI Set
            csv_path: Path to CSV file with metadata
            zip_path: Optional path to ZIP file with source files
            collection_id: Optional collection node ID for membership

        Returns:
            Dictionary with AMI Set info or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        if not self.csrf_token:
            self._login()

        if not self.csrf_token:
            return None

        try:
            from bs4 import BeautifulSoup
            import re

            logger.info("Creating AMI Set via Drupal form submission...")

            # Step 1: Fetch the AMI Set creation form to get form tokens
            form_urls = [
                f"{self.base_url}/amiset/add",
                f"{self.base_url}/ami/new",
                f"{self.base_url}/node/add/ami_set_entity",
            ]

            form_data = None
            form_url = None

            for url in form_urls:
                logger.debug(f"  Fetching form from: {url}")
                try:
                    response = self.session.get(url)
                    if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                        soup = BeautifulSoup(response.text, 'html.parser')
                        form = soup.find('form')

                        if form:
                            logger.info(f"✓ Found form at: {url}")
                            form_url = url
                            form_action = form.get('action', url)

                            # Extract ALL hidden fields and form structure
                            form_data = {}

                            # Get all hidden inputs
                            for input_tag in form.find_all('input', type='hidden'):
                                name = input_tag.get('name', '')
                                value = input_tag.get('value', '')
                                if name:
                                    form_data[name] = value
                                    logger.debug(f"  Hidden field: {name}")

                            # Find submit button name
                            submit_button = form.find('input', type='submit')
                            if not submit_button:
                                submit_button = form.find('button', type='submit')

                            submit_name = 'op'
                            submit_value = 'Save'
                            if submit_button:
                                submit_name = submit_button.get('name', 'op')
                                submit_value = submit_button.get('value', 'Save')
                                logger.debug(f"  Submit button: {submit_name}={submit_value}")

                            # Find file upload fields
                            file_fields = {}
                            for file_input in form.find_all('input', type='file'):
                                field_name = file_input.get('name', '')
                                field_id = file_input.get('id', '')
                                logger.debug(f"  File field: {field_name} (id: {field_id})")

                                # Determine if it's CSV or ZIP field
                                if 'source' in field_name.lower() or 'csv' in field_name.lower():
                                    file_fields['csv'] = field_name
                                elif 'zip' in field_name.lower():
                                    file_fields['zip'] = field_name

                            # Find name field
                            name_field = form.find('input', attrs={'name': lambda x: x and 'name' in x.lower()})
                            if name_field:
                                name_field_name = name_field.get('name', 'name[0][value]')
                                logger.debug(f"  Name field: {name_field_name}")
                                form_data['_name_field'] = name_field_name

                            form_data['_submit_name'] = submit_name
                            form_data['_submit_value'] = submit_value
                            form_data['_file_fields'] = file_fields
                            form_data['_form_action'] = form_action

                            if form_data:
                                break
                except Exception as e:
                    logger.debug(f"  Error fetching form: {str(e)}")
                    continue

            if not form_data or not form_url:
                logger.error("✗ Could not fetch AMI Set creation form or extract tokens")
                logger.error(f"  Tried URLs: {form_urls}")
                logger.error(f"  This may indicate:")
                logger.error(f"    1. AMI Set module not enabled in Archipelago")
                logger.error(f"    2. User doesn't have permission to create AMI Sets")
                logger.error(f"    3. Form URL has changed in newer Archipelago version")
                logger.error(f"  Please check Archipelago configuration and permissions")
                return None

            # Step 2: Prepare form submission with files
            logger.info("Submitting AMI Set form with tokens...")

            # Extract metadata from form_data
            file_fields = form_data.pop('_file_fields', {})
            submit_name = form_data.pop('_submit_name', 'op')
            submit_value = form_data.pop('_submit_value', 'Save')
            name_field_name = form_data.pop('_name_field', 'name[0][value]')
            form_action = form_data.pop('_form_action', form_url)

            logger.debug(f"  File fields found: {file_fields}")
            logger.debug(f"  Name field: {name_field_name}")
            logger.debug(f"  Submit: {submit_name}={submit_value}")
            logger.debug(f"  Form action: {form_action}")

            # Prepare files using discovered field names
            files_to_upload = {}

            # Check CSV file
            if os.path.exists(csv_path):
                if 'csv' in file_fields:
                    csv_field = file_fields['csv']
                    files_to_upload[csv_field] = (
                        os.path.basename(csv_path),
                        open(csv_path, 'rb'),
                        'text/csv'
                    )
                    logger.info(f"  ✓ Adding CSV to field: {csv_field}")
                else:
                    logger.error(f"  ✗ CSV field not found in form! Available file fields: {list(file_fields.keys())}")
                    logger.error(f"  Form may not have expected structure. Cannot upload CSV file.")
                    return None
            else:
                logger.error(f"  ✗ CSV file not found: {csv_path}")
                return None

            # Check ZIP file
            if zip_path:
                if os.path.exists(zip_path):
                    if 'zip' in file_fields:
                        zip_field = file_fields['zip']
                        files_to_upload[zip_field] = (
                            os.path.basename(zip_path),
                            open(zip_path, 'rb'),
                            'application/zip'
                        )
                        logger.info(f"  ✓ Adding ZIP to field: {zip_field}")
                    else:
                        logger.warning(f"  ⚠ ZIP field not found in form! Available file fields: {list(file_fields.keys())}")
                        logger.warning(f"  Proceeding without ZIP file (form may not support it)")
                else:
                    logger.warning(f"  ⚠ ZIP file not found: {zip_path}")

            # Verify we have files to upload
            if not files_to_upload:
                logger.error("  ✗ No files prepared for upload! Cannot submit form.")
                return None

            logger.info(f"  Files prepared for upload: {list(files_to_upload.keys())}")

            # Add form data (already has all hidden fields)
            form_data[name_field_name] = name
            form_data[submit_name] = submit_value

            if collection_id:
                form_data['field_ismemberof[0][target_id]'] = str(collection_id)

            # Use form action if different from form URL
            submission_url = form_action if form_action and not form_action.startswith('/') else form_url
            if form_action and form_action.startswith('/'):
                submission_url = f"{self.base_url}{form_action}"

            logger.debug(f"  Submitting to: {submission_url}")
            logger.debug(f"  Form data keys: {list(form_data.keys())}")
            logger.debug(f"  Files: {list(files_to_upload.keys())}")

            try:
                # Submit the form
                response = self.session.post(
                    submission_url,
                    data=form_data,
                    files=files_to_upload,
                    timeout=300,
                    allow_redirects=True
                )

                logger.debug(f"  Form submission status: {response.status_code}")
                logger.debug(f"  Final URL: {response.url}")

                # Check if successful
                if response.status_code in [200, 201]:
                    # Try to extract AMI Set ID from final URL
                    ami_set_id = None
                    match = re.search(r'/amiset/(\d+)', response.url)
                    if not match:
                        match = re.search(r'/ami_set_entity/(\d+)', response.url)
                    if match:
                        ami_set_id = match.group(1)
                        logger.info(f"✓ Created AMI Set: {name} (ID: {ami_set_id})")
                        return {
                            'success': True,
                            'ami_set_id': ami_set_id,
                            'name': name,
                            'message': f'AMI Set created successfully. Process it at: {self.base_url}/amiset/{ami_set_id}/process'
                        }
                    else:
                        # Check for success message in response
                        if 'has been created' in response.text or 'successfully' in response.text.lower():
                            logger.info(f"✓ AMI Set created (ID not found in URL)")
                            return {
                                'success': True,
                                'message': 'AMI Set created successfully'
                            }

                logger.error(f"✗ Form submission may have failed")
                logger.error(f"  Status code: {response.status_code}")
                logger.error(f"  Content-Type: {response.headers.get('Content-Type')}")
                logger.error(f"  Final URL: {response.url}")
                logger.error(f"  Submitted to: {submission_url}")
                logger.error(f"  Files submitted: {list(files_to_upload.keys())}")
                logger.error(f"  Form data keys: {list(form_data.keys())}")

                # Check for Drupal error messages in response
                if 'error' in response.text.lower() or 'required' in response.text.lower():
                    logger.error(f"  Response may contain validation errors:")
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    error_messages = soup.find_all(['div', 'span'], class_=lambda x: x and ('error' in x.lower() or 'message' in x.lower()))
                    for msg in error_messages[:5]:  # Show first 5 error messages
                        logger.error(f"    - {msg.get_text().strip()[:200]}")

                logger.error(f"  Response excerpt: {response.text[:1000]}")

                # Save full response for debugging
                debug_file = f"/tmp/archipelago_form_response_{name.replace(' ', '_')}.html"
                try:
                    with open(debug_file, 'w') as f:
                        f.write(response.text)
                    logger.error(f"  Full response saved to: {debug_file}")
                except:
                    pass

                return None

            finally:
                # Close file handles
                for file_obj in files_to_upload.values():
                    file_obj[1].close()

        except ImportError:
            logger.error("BeautifulSoup4 is required for form submission. Install with: pip install beautifulsoup4")
            return None
        except Exception as e:
            logger.error(f"Error creating AMI Set via webform: {str(e)}", exc_info=True)
            return None

    def create_ami_set(
        self,
        name: str,
        csv_path: str,
        zip_path: Optional[str] = None,
        collection_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create an AMI Set in Archipelago
        Tries Selenium webform first, then regular webform, then falls back to API method

        Args:
            name: Name for the AMI Set
            csv_path: Path to CSV file with metadata
            zip_path: Optional path to ZIP file with source files
            collection_id: Optional collection node ID for membership

        Returns:
            Dictionary with AMI Set info or None if failed
        """
        # METHOD 1: Try Selenium webform submission (handles JavaScript forms)
        logger.info("Attempting AMI Set creation method 1: Selenium webform submission")
        result = self.create_ami_set_via_selenium(name, csv_path, zip_path, collection_id)
        if result and result.get('success'):
            return result

        logger.warning("Selenium webform submission failed, trying regular webform method...")

        # METHOD 2: Try regular webform submission (for static forms)
        logger.info("Attempting AMI Set creation method 2: regular webform submission")
        result = self.create_ami_set_via_webform(name, csv_path, zip_path, collection_id)
        if result and result.get('success'):
            return result

        logger.warning("Regular webform submission failed, trying API method...")

        # METHOD 3: Original API method (upload files separately, then create entity)
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        if not self.csrf_token:
            self._login()

        if not self.csrf_token:
            return None

        try:
            # Upload CSV file
            logger.info(f"Uploading CSV file: {csv_path}")
            csv_fid = self.upload_file_to_archipelago(csv_path)
            if not csv_fid:
                logger.error("Failed to upload CSV file")
                return None

            # Upload ZIP file (REQUIRED - fail if missing or fails to upload)
            zip_fid = None
            if zip_path and os.path.exists(zip_path):
                zip_size = os.path.getsize(zip_path)
                logger.info(f"Uploading ZIP file: {zip_path}")
                logger.info(f"  ZIP file size: {zip_size:,} bytes ({zip_size / (1024*1024):.2f} MB)")
                
                zip_fid = self.upload_file_to_archipelago(zip_path)
                
                if not zip_fid:
                    error_msg = f"Failed to upload ZIP file ({zip_size:,} bytes) to Archipelago"
                    logger.error(f"❌ {error_msg}")
                    logger.error("  Cannot create AMI Set without source files")
                    return {
                        'success': False,
                        'error': error_msg,
                        'csv_fid': csv_fid,  # Return CSV FID for debugging
                        'details': {
                            'message': 'CSV uploaded but ZIP upload failed',
                            'csv_uploaded': True,
                            'zip_file_size': zip_size,
                            'recommendation': 'Check Archipelago JSON:API logs for file upload errors'
                        }
                    }
            else:
                error_msg = "ZIP file not found or not specified"
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'csv_fid': csv_fid,
                    'details': {'message': 'ZIP file required but missing'}
                }

            # Build AMI Set configuration per Archipelago documentation
            # Reference: https://docs.archipelago.nyc/1.4.0/ami_index/
            ami_config = {
                # File references (FIDs returned from upload_file_to_archipelago)
                'csv': str(csv_fid),
                'zip': str(zip_fid) if zip_fid else None,

                # Plugin configuration
                'plugin': 'spreadsheet',  # Use spreadsheet plugin for CSV-based import

                # Mapping configuration per Archipelago's requirements
                'mapping': {
                    'globalmapping': 'custom',  # Use custom mapping for per-type configuration
                    'custommapping_settings': {
                        'DigitalDocument': {
                            # Strawberry Field JSON storage location
                            'bundle': 'digital_object:field_descriptive_metadata',

                            # Data transformation mode (Direct = CSV columns cast directly to JSON)
                            # Per docs: Direct mode is best for simple ingestion
                            'metadata': 'direct',

                            # File field mappings - Archipelago will:
                            # 1. Extract file from ZIP by name
                            # 2. Create Drupal file entity
                            # 3. Assign dr:fid automatically
                            # 4. Populate documents array
                            'files': {
                                'documents': 'documents',  # PDF/document files
                                'images': 'images',        # Image files (JPG, PNG, TIF, etc)
                                'videos': 'videos',        # Video files
                                'audios': 'audios',        # Audio files
                                'model': 'model'           # 3D model files
                            }
                        }
                    }
                },

                # Processing configuration
                'pluginconfig': {
                    'op': 'create'  # Operation: create new ADOs (alternative: update, patch, delete)
                }
            }

            # Add collection parent mapping if provided
            # This ensures all created digital objects are linked to the collection
            if collection_id:
                ami_config['adomapping'] = {
                    'parents': str(collection_id)  # Collection node ID
                }

            # Create AMI Set entity via JSON:API
            # Per Archipelago docs: AMI Sets hold an ingest strategy (JSON) and reference CSV + ZIP files
            ami_set_data = {
                'data': {
                    'type': 'ami_set_entity--ami_set_entity',
                    'attributes': {
                        'name': name,  # Display name for the AMI Set
                        'set': {
                            'value': json.dumps(ami_config)  # JSON-encoded ingest strategy
                        }
                    },
                    'relationships': {
                        # Source data relationship (CSV file)
                        'source_data': {
                            'data': {
                                'type': 'file--file',
                                'meta': {
                                    'drupal_internal__target_id': csv_fid
                                }
                            }
                        }
                    }
                }
            }

            # Add ZIP file relationship if we have it
            # This contains the actual files to be imported
            if zip_fid:
                ami_set_data['data']['relationships']['zip_file'] = {
                    'data': {
                        'type': 'file--file',
                        'meta': {
                            'drupal_internal__target_id': zip_fid
                        }
                    }
                }

            logger.info(f"Creating AMI Set with configuration: {json.dumps(ami_config, indent=2)}")

            headers = {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json',
                'X-CSRF-Token': self.csrf_token
            }

            response = self.session.post(
                f"{self.base_url}/jsonapi/ami_set_entity/ami_set_entity",
                json=ami_set_data,
                headers=headers
            )

            if response.status_code not in [200, 201]:
                logger.error(f"AMI Set creation failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            result = response.json()
            ami_set_id = result.get('data', {}).get('attributes', {}).get('drupal_internal__id')

            logger.info(f"Created AMI Set: {name} (ID: {ami_set_id})")

            return {
                'success': True,
                'ami_set_id': ami_set_id,
                'name': name,
                'csv_fid': csv_fid,
                'zip_fid': zip_fid,
                'message': f'AMI Set created successfully. Process it at: {self.base_url}/amiset/{ami_set_id}/process'
            }

        except Exception as e:
            logger.error(f"Error creating AMI Set: {str(e)}", exc_info=True)
            return None

    def create_bulk_via_ami(
        self,
        ocr_data_list: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        collection_id: Optional[int] = None,
        job_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create bulk digital objects via AMI Sets workflow with comprehensive file package

        10-step process:
        1. Pre-validation: Check all source files exist
        2. Create dedicated AMI set directory
        3. Copy source files to staging
        4. Generate OCR text files
        5. Generate metadata JSON files
        6. Generate thumbnails
        7. Create enhanced CSV
        8. Create flat ZIP
        9. Upload to Archipelago
        10. Complete

        Args:
            ocr_data_list: List of OCR result dictionaries
            collection_name: Optional name for new collection
            collection_id: Optional existing collection ID
            job_id: Optional job ID for directory naming

        Returns:
            Dictionary with AMI Set creation info
        """
        import uuid
        import shutil

        try:
            # Generate job_id if not provided
            if not job_id:
                job_id = str(uuid.uuid4())

            # STEP 1: PRE-VALIDATION (Fail Fast)
            logger.info("Step 1/10: Validating source files...")
            validation = self.validate_source_files(ocr_data_list)

            if not validation.valid:
                error_msg = f"Validation failed: {len(validation.missing_files)} files missing"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'validation_report': validation.to_dict()
                }

            logger.info(f"Validation passed: {validation.total_files} files found")

            # STEP 2: Create dedicated AMI set directory
            logger.info("Step 2/10: Creating AMI set directory...")
            base_upload_dir = os.getenv('UPLOAD_FOLDER', '/app/uploads')
            ami_set_dir = os.path.join(base_upload_dir, 'ami_sets', job_id)
            os.makedirs(ami_set_dir, exist_ok=True)

            # STEP 3: Copy source files to staging
            logger.info("Step 3/10: Copying source files...")
            source_dir = os.path.join(ami_set_dir, 'source_files')
            os.makedirs(source_dir, exist_ok=True)

            for ocr_data in ocr_data_list:
                file_info = ocr_data.get('file_info', {})
                file_path = self._resolve_file_path(file_info.get('file_path', ''))
                filename = file_info.get('filename', '')

                if filename and os.path.exists(file_path):
                    dest_path = os.path.join(source_dir, filename)
                    shutil.copy2(file_path, dest_path)
                    logger.debug(f"Copied: {filename}")

            # STEP 4: Generate OCR text files
            logger.info("Step 4/10: Generating OCR text files...")
            text_files = self.generate_ocr_text_files(ocr_data_list, ami_set_dir)
            logger.info(f"Generated {len(text_files)} OCR text files")

            # STEP 5: Generate metadata JSON files
            logger.info("Step 5/10: Generating metadata JSON files...")
            metadata_files = self.generate_metadata_files(ocr_data_list, ami_set_dir)
            logger.info(f"Generated {len(metadata_files)} metadata files")

            # STEP 6: Generate thumbnails
            logger.info("Step 6/10: Generating thumbnails...")
            thumbnail_files = self.generate_thumbnails(ocr_data_list, ami_set_dir)
            logger.info(f"Generated {len(thumbnail_files)} thumbnails")

            # STEP 7: Create enhanced CSV
            logger.info("Step 7/10: Creating enhanced CSV...")
            csv_path = os.path.join(ami_set_dir, 'ami_set.csv')
            if not self.create_csv_from_ocr_data(ocr_data_list, csv_path, collection_id, ami_set_dir):
                logger.error(f"Failed to create CSV file at {csv_path}")
                return {
                    'success': False,
                    'error': 'Failed to create CSV file',
                    'step': 7
                }

            # STEP 8: Create flat ZIP
            logger.info("Step 8/10: Creating ZIP archive...")
            zip_path = os.path.join(ami_set_dir, 'ami_set.zip')
            if not self.create_zip_from_files(ocr_data_list, zip_path, ami_set_dir):
                logger.error(f"Failed to create ZIP file at {zip_path}")
                return {
                    'success': False,
                    'error': 'Failed to create ZIP file',
                    'step': 8
                }

            # STEP 9: Upload to Archipelago
            logger.info("Step 9/10: Uploading to Archipelago...")
            timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
            ami_set_name = collection_name or f"OCR Bulk Upload {timestamp}"

            try:
                result = self.create_ami_set(
                    name=ami_set_name,
                    csv_path=csv_path,
                    zip_path=zip_path,
                    collection_id=collection_id
                )

                if not result:
                    logger.error("create_ami_set returned None")
                    return {
                        'success': False,
                        'error': 'Failed to create AMI Set in Archipelago',
                        'step': 9
                    }

                # STEP 10: Complete
                logger.info("Step 10/10: AMI Set creation complete")
                # Keep ami_set_dir for debugging/manual inspection
                # Cleanup can be handled separately if configured

                return result
            except Exception as ami_error:
                logger.error(f"Error in create_ami_set at step 9: {str(ami_error)}", exc_info=True)
                return {
                    'success': False,
                    'error': f'Archipelago upload failed: {str(ami_error)}',
                    'step': 9
                }

        except Exception as e:
            logger.error(f"Error in create_bulk_via_ami: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Bulk AMI creation failed: {str(e)}'
            }
