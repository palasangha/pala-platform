"""
Service for integrating with Archipelago Commons
https://archipelago.nyc/
"""

import requests
import logging
import base64
import mimetypes
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.config import Config
from app.services.data_mapper import DataMapper

logger = logging.getLogger(__name__)


class ArchipelagoService:
    """Service for pushing documents to Archipelago Commons"""

    def __init__(self):
        self.base_url = Config.ARCHIPELAGO_BASE_URL.rstrip('/')
        self.username = Config.ARCHIPELAGO_USERNAME
        self.password = Config.ARCHIPELAGO_PASSWORD
        self.enabled = Config.ARCHIPELAGO_ENABLED
        self.session = None

    def _should_verify_ssl(self) -> bool:
        """Determine if SSL verification should be enabled based on URL"""
        # Disable SSL verification for private IP addresses
        return not (self.base_url.startswith('https://172.') or
                   self.base_url.startswith('https://10.') or
                   self.base_url.startswith('https://192.168.'))

    def _get_session(self) -> requests.Session:
        """Get or create session (without Basic Auth - we use JSON login instead)"""
        if self.session is None:
            self.session = requests.Session()
            # Don't use Basic Auth - Archipelago uses cookie-based sessions
        return self.session

    def _login(self) -> Optional[str]:
        """
        Authenticate with Archipelago and get CSRF token
        Returns the CSRF token if successful
        """
        try:
            # Create a fresh session for each login to avoid stale session issues
            self.session = requests.Session()
            session = self.session

            # Login to Drupal - this returns csrf_token in the response and sets session cookie
            login_url = f"{self.base_url}/user/login?_format=json"
            login_data = {
                "name": self.username,
                "pass": self.password
            }
            headers = {
                "Content-Type": "application/json"
            }

            login_response = session.post(login_url, json=login_data, headers=headers, verify=self._should_verify_ssl())
            login_response.raise_for_status()

            # Extract CSRF token from login response
            login_result = login_response.json()
            csrf_token = login_result.get('csrf_token')

            if not csrf_token:
                logger.error("No CSRF token in login response")
                return None

            logger.info(f"Successfully logged in to Archipelago as {self.username}")
            return csrf_token

        except Exception as e:
            logger.error(f"Failed to authenticate with Archipelago: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            return None

    def create_digital_object(
        self,
        title: str,
        file_path: str,
        ocr_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        collection_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a digital object in Archipelago Commons

        Args:
            title: Title of the digital object
            file_path: Path to the file to upload
            ocr_text: OCR extracted text
            metadata: Additional metadata dictionary
            tags: List of tags/keywords
            collection_id: Optional collection ID to link the document to

        Returns:
            Dictionary with created node information or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        try:
            csrf_token = self._login()
            if not csrf_token:
                return None

            session = self._get_session()

            # Prepare the JSON:API payload for Archipelago
            # Archipelago uses Strawberry Field (SBF) format
            sbf_data = self._prepare_sbf_metadata(
                title=title,
                ocr_text=ocr_text,
                metadata=metadata,
                tags=tags
            )

            # Add collection reference if provided
            if collection_id:
                sbf_data['ismemberof'] = collection_id
                logger.info(f"Linking document to collection: {collection_id}")

            # STEP 1: Create the Digital Object node (without file attachment initially)
            # Archipelago uses field_descriptive_metadata for the Strawberry Field JSON
            # The SBF field expects data in a 'value' property as JSON string
            import json as json_lib
            import os

            # Add source file info to metadata for reference
            sbf_data['source_file_path'] = file_path
            sbf_data['source_filename'] = os.path.basename(file_path)

            node_data = {
                'data': {
                    'type': 'node--digital_object',
                    'attributes': {
                        'title': title,
                        # Don't set 'status' when content moderation is enabled
                        # Use 'moderation_state' instead if needed
                        'field_descriptive_metadata': {
                            'value': json_lib.dumps(sbf_data, ensure_ascii=False)
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json; charset=utf-8',
                'X-CSRF-Token': csrf_token
            }

            # Manually serialize to preserve Unicode characters
            import json as json_module
            json_payload = json_module.dumps(node_data, ensure_ascii=False).encode('utf-8')

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object",
                data=json_payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            node_id = result.get('data', {}).get('id')
            node_uuid = result.get('data', {}).get('id')  # In JSON:API, 'id' is the UUID

            logger.info(f"Successfully created digital object in Archipelago: {node_id}")

            # NOTE: Binary file uploads are not supported via Archipelago's JSON:API
            # Archipelago requires files to be uploaded through webforms, which are not accessible via API
            # The digital object has been created with:
            # - Full OCR text in the 'text' field
            # - File metadata (path, name, size) in the Strawberry Field JSON
            # - All OCR metadata (provider, confidence, language, etc.)
            # This provides full searchability and metadata even without the binary attachment

            logger.info(f"Digital object created with OCR text and metadata (file path: {file_path})")

            return {
                'success': True,
                'node_id': node_id,
                'node_uuid': node_uuid,
                'url': f"{self.base_url}/do/{node_id}",
                'file_attached': False,  # Binary files require webform upload
                'note': 'OCR text and metadata stored; binary file upload requires webform (not available via API)'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error creating digital object: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating digital object in Archipelago: {str(e)}", exc_info=True)
            return None

    def upload_file_before_metadata(self, file_path: str, csrf_token: str) -> Optional[Dict]:
        """
        Upload file BEFORE creating metadata (AMI pattern from PHP example)

        This matches the Drupal AMI workflow:
        1. Upload file first with application/octet-stream
        2. Get drupal_internal__fid back
        3. Use fid in metadata JSON when creating digital object

        Args:
            file_path: Path to file to upload
            csrf_token: CSRF token for authentication

        Returns:
            Dictionary with fid, mime_type, filesize, and field_name for mapping
        """
        try:
            import os
            import mimetypes
            session = self._get_session()

            # Resolve file path
            if not os.path.isabs(file_path):
                gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')
                gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))
                if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                    file_path = file_path[len(gvpocr_basename) + 1:]
                file_path = os.path.join(gvpocr_path, file_path)

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            logger.info(f"=== Uploading file BEFORE metadata (AMI pattern) ===")
            logger.info(f"File: {filename}")
            logger.info(f"Size: {file_size} bytes")
            logger.info(f"MIME: {mime_type}")

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Upload with application/octet-stream as per PHP example
            headers = {
                'Accept': 'application/vnd.api+json',
                'Content-Type': 'application/octet-stream',
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-CSRF-Token': csrf_token
            }

            # Try the file field endpoint first
            endpoint = f"{self.base_url}/jsonapi/node/digital_object/field_file_drop"

            logger.info(f"→ POST {endpoint}")
            response = session.post(
                endpoint,
                data=file_content,
                headers=headers,
                timeout=300
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()

                # Extract FID from response
                fid = self._extract_fid_from_response(result)

                if fid:
                    # Map MIME type to Archipelago field name
                    field_name = self._map_mime_to_field(mime_type)

                    logger.info(f"✓ File uploaded successfully!")
                    logger.info(f"  FID: {fid}")
                    logger.info(f"  MIME type: {mime_type}")
                    logger.info(f"  Mapped field: {field_name}")

                    return {
                        'fid': fid,
                        'filename': filename,
                        'filesize': file_size,
                        'filemime': mime_type,
                        'field_name': field_name,  # For mapping to documents/images/etc
                        'uri': self._extract_uri_from_response(result)
                    }
                else:
                    logger.warning(f"Response missing FID")
            else:
                logger.warning(f"Upload failed with status {response.status_code}")
                logger.debug(f"Response: {response.text[:500]}")

            return None

        except Exception as e:
            logger.error(f"Error uploading file before metadata: {str(e)}", exc_info=True)
            return None

    def _map_mime_to_field(self, mime_type: str) -> str:
        """
        Map MIME type to Archipelago field name (matching PHP logic)

        Based on PHP code:
        $as_file_type = explode('/', $mime_type);
        $as_file_type = count($as_file_type) == 2 ? $as_file_type[0] : 'document';
        $as_file_type = ($as_file_type != 'application') ? $as_file_type : 'document';

        Args:
            mime_type: MIME type (e.g., 'image/jpeg', 'application/pdf')

        Returns:
            Field name in plural (e.g., 'images', 'documents', 'videos')
        """
        parts = mime_type.split('/')

        if len(parts) != 2:
            return 'documents'

        file_type = parts[0]  # image, video, audio, application, etc.
        specific_type = parts[1]  # jpeg, pdf, mp4, etc.

        # Map application to document
        if file_type == 'application':
            file_type = 'document'

        # Try specific type first (e.g., 'jpegs', 'pdfs')
        # Then fall back to general type (e.g., 'images', 'documents')
        # This matches the PHP logic

        # Check if specific type should be used
        specific_plural = specific_type + 's'

        # For now, use general type mapping
        type_map = {
            'image': 'images',
            'video': 'videos',
            'audio': 'audios',
            'document': 'documents',
            'model': 'models',
            'text': 'documents'
        }

        return type_map.get(file_type, 'documents')

    def _upload_file_rest_api(self, file_path: str, csrf_token: str) -> Optional[Dict]:
        """
        Upload file using Drupal REST API (alternative to JSON:API)
        Implements comprehensive upload strategy:
        1. Multipart/form-data (most compatible with Drupal webforms)
        2. Binary upload with application/octet-stream

        Based on Archipelago AMI service implementation.

        Args:
            file_path: Path to file to upload
            csrf_token: CSRF token for authentication

        Returns:
            Dictionary with file info including fid, or None if failed
        """
        try:
            import os
            import json as json_lib
            session = self._get_session()

            # Resolve file path
            if not os.path.isabs(file_path):
                gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')
                gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))
                if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                    file_path = file_path[len(gvpocr_basename) + 1:]
                file_path = os.path.join(gvpocr_path, file_path)

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            logger.info(f"=== REST API Upload: {filename} ({file_size / (1024*1024):.2f} MB) ===")

            # STRATEGY 1: Try multipart/form-data upload (most compatible)
            logger.info("→ Strategy 1: Multipart/form-data upload")

            multipart_endpoints = [
                # Generic file upload
                f"{self.base_url}/file/upload",
                # Digital object field upload
                f"{self.base_url}/file/upload/node/digital_object/field_file_drop",
                # File entity upload
                f"{self.base_url}/file/upload/file/file",
            ]

            for endpoint_url in multipart_endpoints:
                logger.info(f"  → Trying multipart: {endpoint_url}")

                try:
                    with open(file_path, 'rb') as f:
                        # Multipart/form-data format
                        files = {
                            'files[]': (filename, f, 'application/octet-stream')
                        }
                        headers = {
                            'X-CSRF-Token': csrf_token,
                            # Let requests library set Content-Type with boundary
                        }

                        response = session.post(
                            f"{endpoint_url}?_format=json",
                            files=files,
                            headers=headers,
                            timeout=300
                        )

                        logger.info(f"    Response status: {response.status_code}")

                        if response.status_code in [200, 201]:
                            logger.info(f"    ✓ Multipart upload succeeded!")

                            try:
                                result = response.json()
                                logger.debug(f"    Response: {json_lib.dumps(result, indent=2)}")

                                # Extract FID
                                fid = self._extract_fid_from_response(result)

                                if fid:
                                    logger.info(f"    ✓ File uploaded successfully!")
                                    logger.info(f"      FID: {fid}")
                                    logger.info(f"      Endpoint: {endpoint_url}")

                                    return {
                                        'fid': fid,
                                        'uuid': result.get('uuid', [{}])[0].get('value') if 'uuid' in result else None,
                                        'filename': filename,
                                        'uri': self._extract_uri_from_response(result),
                                        'filesize': file_size,
                                        'filemime': result.get('filemime', [{}])[0].get('value', 'application/octet-stream') if 'filemime' in result else 'application/octet-stream'
                                    }
                                else:
                                    logger.warning(f"    Response missing FID")

                            except ValueError as e:
                                logger.warning(f"    Invalid JSON response: {e}")
                                logger.debug(f"    Response text: {response.text[:500]}")
                        else:
                            logger.debug(f"    Status {response.status_code}")

                except Exception as e:
                    logger.debug(f"    Error: {str(e)}")
                    continue

            # STRATEGY 2: Try binary upload with application/octet-stream
            logger.info("→ Strategy 2: Binary upload (application/octet-stream)")

            # Read file content for binary upload
            with open(file_path, 'rb') as f:
                file_content = f.read()

            binary_endpoints = [
                {
                    'url': f"{self.base_url}/file/upload",
                    'name': 'Generic file upload'
                },
                {
                    'url': f"{self.base_url}/file/upload/file/file",
                    'name': 'File entity upload'
                },
                {
                    'url': f"{self.base_url}/file/upload/node/digital_object/field_file_drop",
                    'name': 'Digital object field upload'
                },
            ]

            for endpoint_config in binary_endpoints:
                endpoint_url = endpoint_config['url']
                endpoint_name = endpoint_config['name']

                logger.info(f"  → Trying binary: {endpoint_name}")

                headers = {
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'file; filename="{filename}"',
                    'X-CSRF-Token': csrf_token
                }

                try:
                    response = session.post(
                        f"{endpoint_url}?_format=json",
                        data=file_content,
                        headers=headers,
                        timeout=300
                    )

                    logger.info(f"    Response status: {response.status_code}")

                    if response.status_code in [200, 201]:
                        logger.info(f"    ✓ Binary upload succeeded!")

                        try:
                            result = response.json()
                            logger.debug(f"    Response: {json_lib.dumps(result, indent=2)}")

                            fid = self._extract_fid_from_response(result)

                            if fid:
                                logger.info(f"    ✓ File uploaded successfully!")
                                logger.info(f"      FID: {fid}")
                                logger.info(f"      Endpoint: {endpoint_url}")

                                return {
                                    'fid': fid,
                                    'uuid': result.get('uuid', [{}])[0].get('value') if 'uuid' in result else None,
                                    'filename': filename,
                                    'uri': self._extract_uri_from_response(result),
                                    'filesize': file_size,
                                    'filemime': result.get('filemime', [{}])[0].get('value', 'application/octet-stream') if 'filemime' in result else 'application/octet-stream'
                                }
                            else:
                                logger.warning(f"    Response missing FID")

                        except ValueError as e:
                            logger.warning(f"    Invalid JSON response: {e}")
                            logger.debug(f"    Response text: {response.text[:500]}")
                    else:
                        logger.debug(f"    Status {response.status_code}: {response.text[:200]}")

                except Exception as e:
                    logger.debug(f"    Error: {str(e)}")
                    continue

            logger.warning("✗ All REST API upload attempts failed")
            return None

        except Exception as e:
            logger.error(f"Error in REST API upload: {str(e)}", exc_info=True)
            return None

    def _extract_fid_from_response(self, result: Dict) -> Optional[int]:
        """
        Extract file ID (fid) from various Drupal REST API response formats

        Handles:
        - {"data": {"attributes": {"drupal_internal__fid": 123}}}  ← JSON:API with data wrapper
        - {"attributes": {"drupal_internal__fid": 123}}  ← JSON:API direct
        - {"fid": [{"value": 123}]}
        - {"fid": 123}
        - {"drupal_internal__fid": 123}
        - {"id": 123}
        """
        # Format 1: JSON:API format with 'data' wrapper
        # Example: {"data": {"type": "file--file", "attributes": {"drupal_internal__fid": 108}}}
        if 'data' in result and isinstance(result['data'], dict):
            data = result['data']
            if 'attributes' in data and isinstance(data['attributes'], dict):
                attributes = data['attributes']
                if 'drupal_internal__fid' in attributes:
                    fid = attributes['drupal_internal__fid']
                    if isinstance(fid, int):
                        logger.info(f"✓ Extracted FID from data.attributes: {fid}")
                        return fid

        # Format 2: JSON:API format with attributes directly at top level
        # Example: {'type': 'file--file', 'attributes': {'drupal_internal__fid': 98, ...}}
        if 'attributes' in result:
            attributes = result['attributes']
            if isinstance(attributes, dict) and 'drupal_internal__fid' in attributes:
                fid = attributes['drupal_internal__fid']
                if isinstance(fid, int):
                    logger.info(f"✓ Extracted FID from attributes: {fid}")
                    return fid

        # Format 3: {"fid": [{"value": 123}]}
        if 'fid' in result:
            fid_data = result['fid']
            if isinstance(fid_data, list) and len(fid_data) > 0:
                fid = fid_data[0].get('value')
                if fid:
                    logger.info(f"✓ Extracted FID from fid array: {fid}")
                    return fid
            elif isinstance(fid_data, int):
                logger.info(f"✓ Extracted FID from fid: {fid_data}")
                return fid_data

        # Format 4: Other common field names at top level
        for field in ['drupal_internal__fid', 'id', 'file_id', 'entity_id']:
            if field in result:
                value = result[field]
                if isinstance(value, int):
                    logger.info(f"✓ Extracted FID from {field}: {value}")
                    return value
                elif isinstance(value, list) and len(value) > 0:
                    fid = value[0].get('value')
                    if fid:
                        logger.info(f"✓ Extracted FID from {field} array: {fid}")
                        return fid

        logger.warning(f"⚠ Could not extract FID from response. Available keys: {list(result.keys())}")
        return None

    def _extract_uri_from_response(self, result: Dict) -> str:
        """
        Extract file URI from Drupal REST API response

        Handles:
        - {"data": {"attributes": {"uri": {"url": "https://..."}}}}  ← JSON:API with data wrapper
        - {"attributes": {"uri": {"url": "https://..."}}}  ← JSON:API direct
        - {"uri": "s3://..."}
        - {"uri": [{"value": "s3://..."}]}
        - {"url": "https://..."}
        """
        # Format 1: JSON:API format with 'data' wrapper
        if 'data' in result and isinstance(result['data'], dict):
            data = result['data']
            if 'attributes' in data and isinstance(data['attributes'], dict):
                attributes = data['attributes']
                if 'uri' in attributes:
                    uri_data = attributes['uri']
                    # Check if it's a nested object with 'url' key
                    if isinstance(uri_data, dict) and 'url' in uri_data:
                        return uri_data['url']
                    # Or a direct string
                    elif isinstance(uri_data, str):
                        return uri_data

        # Format 2: JSON:API format with attributes at top level
        if 'attributes' in result:
            attributes = result['attributes']
            if isinstance(attributes, dict) and 'uri' in attributes:
                uri_data = attributes['uri']
                # Check if it's a nested object with 'url' key
                if isinstance(uri_data, dict) and 'url' in uri_data:
                    return uri_data['url']
                # Or a direct string
                elif isinstance(uri_data, str):
                    return uri_data

        # Format 3: Top level uri or url
        uri = result.get('uri', result.get('url', ''))
        if isinstance(uri, list) and len(uri) > 0:
            uri_value = uri[0].get('value', '')
            return uri_value if uri_value else ''
        elif isinstance(uri, dict) and 'url' in uri:
            return uri['url']
        elif isinstance(uri, str):
            return uri

        return ''

    def _create_file_entity_from_url(self, file_url: str, filename: str, filesize: int, mime_type: str, csrf_token: str) -> Optional[Dict]:
        """
        Create a Drupal file entity via JSON:API that references an external URL
        This doesn't upload the binary - it creates a file entity pointing to the URL

        Args:
            file_url: URL where the file is accessible (e.g., MinIO URL)
            filename: Original filename
            filesize: File size in bytes
            mime_type: MIME type
            csrf_token: CSRF token

        Returns:
            Dictionary with fid and other file info, or None if failed
        """
        try:
            import json as json_lib
            session = self._get_session()

            logger.info(f"→ Creating file entity via JSON:API for: {filename}")
            logger.info(f"  External URL: {file_url}")

            # Create file entity via JSON:API POST
            # This creates a "managed file" in Drupal that references the external URL
            file_data = {
                'data': {
                    'type': 'file--file',
                    'attributes': {
                        'uri': file_url,  # External URL (MinIO)
                        'filename': filename,
                        'filesize': filesize,
                        'filemime': mime_type,
                        'status': True  # Permanent file
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json',
                'X-CSRF-Token': csrf_token
            }

            logger.debug(f"  Request data: {json_lib.dumps(file_data, indent=2)}")

            response = session.post(
                f"{self.base_url}/jsonapi/file/file",
                json=file_data,
                headers=headers,
                timeout=60
            )

            logger.info(f"  Response status: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                logger.debug(f"  Response: {json_lib.dumps(result, indent=2)}")

                file_data_response = result.get('data', {})
                file_attributes = file_data_response.get('attributes', {})

                # Extract file ID
                fid = file_attributes.get('drupal_internal__fid')
                file_uuid = file_data_response.get('id')

                if fid:
                    logger.info(f"  ✓ File entity created successfully!")
                    logger.info(f"    FID: {fid}")
                    logger.info(f"    UUID: {file_uuid}")

                    return {
                        'fid': fid,
                        'uuid': file_uuid,
                        'filename': filename,
                        'uri': file_url,
                        'filesize': filesize,
                        'filemime': mime_type
                    }
                else:
                    logger.warning(f"  Response missing FID")
                    logger.debug(f"  Attributes: {file_attributes.keys()}")
            else:
                logger.warning(f"  Failed with status {response.status_code}")
                logger.debug(f"  Response: {response.text[:500]}")

            return None

        except Exception as e:
            logger.error(f"Error creating file entity from URL: {str(e)}", exc_info=True)
            return None

    def get_digital_object_file_ids(self, node_id: str) -> Optional[Dict]:
        """
        Retrieve all file IDs (dr:fid) from a digital object's as:document structure

        Args:
            node_id: Digital object node ID or UUID

        Returns:
            Dictionary with file information including dr:fid values
        """
        try:
            session = self._get_session()

            logger.info(f"Retrieving file IDs for digital object: {node_id}")

            # Determine if node_id is UUID or numeric ID
            if '-' in str(node_id):
                # It's a UUID
                endpoint = f"{self.base_url}/jsonapi/node/digital_object/{node_id}"
            else:
                # It's a numeric ID, need to fetch by filter
                endpoint = f"{self.base_url}/jsonapi/node/digital_object?filter[drupal_internal__nid]={node_id}"

            response = session.get(endpoint)

            if response.status_code != 200:
                logger.error(f"Failed to fetch digital object: {response.status_code}")
                return None

            result = response.json()

            # Handle both single object and list response
            if 'data' in result:
                data = result['data']
                if isinstance(data, list):
                    if not data:
                        logger.error("Digital object not found")
                        return None
                    node_data = data[0]
                else:
                    node_data = data
            else:
                logger.error("Invalid response format")
                return None

            # Extract metadata
            attributes = node_data.get('attributes', {})
            metadata_field = attributes.get('field_descriptive_metadata', {})

            if isinstance(metadata_field, dict):
                metadata = metadata_field.get('value')
            else:
                metadata = metadata_field

            # Parse JSON metadata
            if isinstance(metadata, str):
                import json as json_lib
                metadata = json_lib.loads(metadata)

            # Extract as:document structure
            as_document = metadata.get('as:document', {})
            documents_array = metadata.get('documents', [])

            # Build result with all file information
            file_info = {
                'node_id': attributes.get('drupal_internal__nid'),
                'node_uuid': node_data.get('id'),
                'label': metadata.get('label', ''),
                'documents_array': documents_array,
                'files': []
            }

            # Extract dr:fid from each file in as:document
            for doc_uuid, doc_data in as_document.items():
                file_entry = {
                    'uuid': doc_uuid,
                    'dr:fid': doc_data.get('dr:fid'),
                    'url': doc_data.get('url', ''),
                    'name': doc_data.get('name', ''),
                    'dr:filesize': doc_data.get('dr:filesize', 0),
                    'dr:mimetype': doc_data.get('dr:mimetype', ''),
                    'sequence': doc_data.get('sequence', 1)
                }
                file_info['files'].append(file_entry)

            logger.info(f"Retrieved {len(file_info['files'])} file(s) from digital object")
            for f in file_info['files']:
                logger.info(f"  - {f['name']}: dr:fid={f['dr:fid']}")

            return file_info

        except Exception as e:
            logger.error(f"Error retrieving file IDs: {str(e)}", exc_info=True)
            return None

    def _get_file_fid_from_uuid(self, file_uuid: str) -> Optional[int]:
        """
        Fetch the Drupal internal file ID (fid) from a file UUID

        Args:
            file_uuid: UUID of the file entity

        Returns:
            Drupal internal file ID (integer) or None if not found
        """
        try:
            session = self._get_session()

            # Query the file entity by UUID to get the fid
            logger.info(f"Fetching file entity details for UUID: {file_uuid}")
            response = session.get(
                f"{self.base_url}/jsonapi/file/file/{file_uuid}"
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch file entity. Status: {response.status_code}")
                return None

            result = response.json()
            file_data = result.get('data', {})
            file_attributes = file_data.get('attributes', {})

            drupal_fid = file_attributes.get('drupal_internal__fid')

            if drupal_fid:
                logger.info(f"Successfully fetched fid from file UUID: {file_uuid} -> fid: {drupal_fid}")
            else:
                logger.warning(f"drupal_internal__fid not found in file entity attributes")
                logger.info(f"Available keys: {list(file_attributes.keys())}")

            return drupal_fid

        except Exception as e:
            logger.error(f"Error fetching file fid from UUID: {str(e)}")
            return None

    def _upload_file_to_node(self, file_path: str, node_uuid: str, csrf_token: str) -> Optional[Dict]:
        """
        Upload file to an existing digital object node via JSON:API field endpoint

        Args:
            file_path: Path to file to upload (can be relative or absolute)
            node_uuid: UUID of the digital object node to attach file to
            csrf_token: CSRF token for authentication

        Returns:
            Dictionary with file UUID and info if successful, None otherwise
        """
        try:
            import os
            import json as json_lib
            session = self._get_session()

            # Resolve file path - if relative, prepend GVPOCR_PATH
            if not os.path.isabs(file_path):
                gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')

                # Handle case where relative path starts with basename of GVPOCR_PATH
                # e.g., file_path="Bhushanji/eng-typed/file.pdf" and GVPOCR_PATH="/mnt/.../Bhushanji"
                gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))
                if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                    # Strip the duplicate basename
                    file_path = file_path[len(gvpocr_basename) + 1:]

                file_path = os.path.join(gvpocr_path, file_path)

            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            # Read file
            with open(file_path, 'rb') as f:
                file_content = f.read()

            filename = os.path.basename(file_path)

            # Detect the actual MIME type of the file
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            logger.info(f"Detected MIME type: {content_type} for file: {filename}")

            # Upload file to node's field_file_drop using JSON:API
            # Use the actual file's MIME type
            headers = {
                'Content-Type': content_type,
                'Accept': 'application/vnd.api+json',
                'Content-Disposition': f'file; filename="{filename}"',
                'X-CSRF-Token': csrf_token
            }

            # POST to the node's field_file_drop endpoint
            # field_file_drop is Archipelago's computed entity reference field for file uploads
            logger.info(f"Uploading file to field endpoint: {filename} ({len(file_content)} bytes)")
            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object/{node_uuid}/field_file_drop",
                data=file_content,
                headers=headers
            )

            # ENHANCED LOGGING
            logger.info(f"Upload response status: {response.status_code}")
            logger.info(f"Upload response headers: {dict(response.headers)}")

            if response.status_code not in [200, 201]:
                logger.error(f"File upload failed. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                response.raise_for_status()

            result = response.json()
            logger.info(f"=== UPLOAD RESPONSE DEBUG ===")
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response type: {type(result)}")
            logger.info(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            logger.info(f"Full response body: {json_lib.dumps(result, indent=2)}")

            # Parse response - handle multiple possible formats
            file_data = None

            # Format 1: Standard JSON:API with 'data' key
            if 'data' in result:
                data_content = result['data']
                logger.info(f"Found 'data' key, type: {type(data_content)}")

                # Check if data is a list or single object
                if isinstance(data_content, list):
                    if len(data_content) > 0:
                        file_data = data_content[0]
                        logger.info(f"Using first element from data array")
                    else:
                        logger.error("data array is empty")
                elif isinstance(data_content, dict):
                    file_data = data_content
                    logger.info(f"Using data object directly")
                else:
                    logger.error(f"Unexpected data type: {type(data_content)}")

            # Format 2: Response is the file object directly (no 'data' wrapper)
            elif 'id' in result and 'type' in result:
                file_data = result
                logger.info(f"Response is a direct file object (no 'data' wrapper)")

            # Format 3: Check if there's a 'file' key
            elif 'file' in result:
                file_data = result['file']
                logger.info(f"Found 'file' key in response")

            else:
                logger.error(f"Unrecognized response format. Keys: {list(result.keys())}")

            # Validate we got file data
            if not file_data:
                logger.error("Could not extract file data from upload response")
                return None

            logger.info(f"Extracted file_data keys: {list(file_data.keys()) if isinstance(file_data, dict) else 'not a dict'}")

            # Extract file UUID
            file_uuid = file_data.get('id')
            if not file_uuid:
                logger.error(f"Upload response missing file UUID (id field)")
                logger.error(f"File data: {json_lib.dumps(file_data, indent=2)}")
                return None

            logger.info(f"File UUID: {file_uuid}")

            # Extract attributes
            file_attributes = file_data.get('attributes', {})

            # DEBUG: Log all available attributes to see what fields are present
            logger.info(f"=== FILE ATTRIBUTES DEBUG ===")
            logger.info(f"Available attribute keys: {list(file_attributes.keys())}")
            logger.info(f"Full attributes: {json_lib.dumps(file_attributes, indent=2)}")

            # Extract Drupal internal file ID (integer ID used by Drupal)
            drupal_fid = file_attributes.get('drupal_internal__fid')

            logger.info(f"Successfully uploaded file to node {node_uuid}: {filename} -> {file_uuid}")
            logger.info(f"Drupal internal file ID from upload response: {drupal_fid}")

            # If fid not in upload response, query the file entity separately
            if drupal_fid is None:
                logger.warning(f"⚠ drupal_internal__fid not found in upload response attributes!")
                logger.info(f"→ Attempting to fetch fid by querying file entity...")
                drupal_fid = self._get_file_fid_from_uuid(file_uuid)

            if drupal_fid:
                logger.info(f"✓ Final Drupal file ID: {drupal_fid}")
            else:
                logger.error(f"✗ Could not obtain Drupal file ID for file {file_uuid}")

            return {
                'uuid': file_uuid,
                'fid': drupal_fid,  # Drupal internal file ID
                'filename': filename,
                'uri': file_attributes.get('uri', {}).get('url', ''),
                'filesize': file_attributes.get('filesize'),
                'filemime': file_attributes.get('filemime')
            }

        except Exception as e:
            logger.error(f"Error uploading file to Archipelago node {node_uuid}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            return None

    def _upload_file_standalone(self, file_path: str, csrf_token: str) -> Optional[Dict]:
        """
        Upload file as standalone file entity (alternative method)

        This creates a file entity first, which can then be referenced by a node.
        Use this as a fallback if direct upload to field_file_drop fails.

        Args:
            file_path: Path to file to upload
            csrf_token: CSRF token for authentication

        Returns:
            Dictionary with file UUID and info if successful, None otherwise
        """
        try:
            import os
            import json as json_lib
            session = self._get_session()

            # Resolve file path
            if not os.path.isabs(file_path):
                gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')
                gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))
                if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                    file_path = file_path[len(gvpocr_basename) + 1:]
                file_path = os.path.join(gvpocr_path, file_path)

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            # Read file
            with open(file_path, 'rb') as f:
                file_content = f.read()

            filename = os.path.basename(file_path)

            # Detect the actual MIME type of the file
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            logger.info(f"Detected MIME type: {content_type} for file: {filename}")

            # Upload to standalone file endpoint
            # Use the actual file's MIME type instead of application/octet-stream
            headers = {
                'Content-Type': content_type,
                'Accept': 'application/vnd.api+json',
                'Content-Disposition': f'file; filename="{filename}"',
                'X-CSRF-Token': csrf_token
            }

            logger.info(f"Uploading file as standalone entity: {filename} ({len(file_content)} bytes)")
            response = session.post(
                f"{self.base_url}/jsonapi/file/file",
                data=file_content,
                headers=headers
            )

            logger.info(f"Standalone upload response status: {response.status_code}")

            if response.status_code not in [200, 201]:
                logger.error(f"Standalone file upload failed. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            result = response.json()
            logger.info(f"=== STANDALONE UPLOAD RESPONSE DEBUG ===")
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response type: {type(result)}")
            logger.info(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            logger.info(f"Full response: {json_lib.dumps(result, indent=2)}")

            # Parse response - handle multiple possible formats
            file_data = None

            # Format 1: Standard JSON:API with 'data' key
            if 'data' in result:
                data_content = result['data']
                logger.info(f"Found 'data' key, type: {type(data_content)}")

                if isinstance(data_content, list):
                    if len(data_content) > 0:
                        file_data = data_content[0]
                        logger.info(f"Using first element from data array")
                    else:
                        logger.error("data array is empty")
                elif isinstance(data_content, dict):
                    file_data = data_content
                    logger.info(f"Using data object directly")
                else:
                    logger.error(f"Unexpected data type: {type(data_content)}")

            # Format 2: Response is the file object directly (no 'data' wrapper)
            elif 'id' in result and 'type' in result:
                file_data = result
                logger.info(f"Response is a direct file object (no 'data' wrapper)")

            # Format 3: Check if there's a 'file' key
            elif 'file' in result:
                file_data = result['file']
                logger.info(f"Found 'file' key in response")

            else:
                logger.error(f"Unrecognized response format. Keys: {list(result.keys())}")

            # Validate we got file data
            if not file_data:
                logger.error("Could not extract file data from standalone upload response")
                return None

            logger.info(f"Extracted file_data keys: {list(file_data.keys()) if isinstance(file_data, dict) else 'not a dict'}")

            # Extract file UUID
            file_uuid = file_data.get('id')
            if not file_uuid:
                logger.error(f"Standalone upload response missing file UUID (id field)")
                logger.error(f"File data: {json_lib.dumps(file_data, indent=2)}")
                return None

            logger.info(f"File UUID: {file_uuid}")

            # Extract attributes
            file_attributes = file_data.get('attributes', {})

            # Extract Drupal internal file ID (integer ID used by Drupal)
            drupal_fid = file_attributes.get('drupal_internal__fid')

            logger.info(f"Successfully uploaded standalone file: {filename} -> {file_uuid}")
            logger.info(f"Drupal internal file ID from upload response: {drupal_fid}")

            # If fid not in upload response, query the file entity separately
            if drupal_fid is None:
                logger.warning(f"⚠ drupal_internal__fid not found in standalone upload response!")
                logger.info(f"→ Attempting to fetch fid by querying file entity...")
                drupal_fid = self._get_file_fid_from_uuid(file_uuid)

            if drupal_fid:
                logger.info(f"✓ Final Drupal file ID: {drupal_fid}")
            else:
                logger.error(f"✗ Could not obtain Drupal file ID for standalone file {file_uuid}")

            return {
                'uuid': file_uuid,
                'fid': drupal_fid,  # Drupal internal file ID
                'filename': filename,
                'uri': file_attributes.get('uri', {}).get('url', ''),
                'filesize': file_attributes.get('filesize'),
                'filemime': file_attributes.get('filemime')
            }

        except Exception as e:
            logger.error(f"Error uploading standalone file: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            return None

    def _attach_file_to_node(self, node_uuid: str, file_uuid: str, csrf_token: str) -> bool:
        """
        Attach an existing file entity to a digital object node via PATCH

        Args:
            node_uuid: UUID of the digital object node
            file_uuid: UUID of the file entity to attach
            csrf_token: CSRF token for authentication

        Returns:
            True if successful, False otherwise
        """
        try:
            import json as json_lib
            session = self._get_session()

            # PATCH the node to add file reference
            patch_data = {
                'data': {
                    'type': 'node--digital_object',
                    'id': node_uuid,
                    'relationships': {
                        'field_file_drop': {
                            'data': [{
                                'type': 'file--file',
                                'id': file_uuid
                            }]
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json',
                'X-CSRF-Token': csrf_token
            }

            logger.info(f"Attaching file {file_uuid} to node {node_uuid}")
            response = session.patch(
                f"{self.base_url}/jsonapi/node/digital_object/{node_uuid}",
                json=patch_data,
                headers=headers
            )

            logger.info(f"PATCH response status: {response.status_code}")

            if response.status_code not in [200, 204]:
                logger.error(f"File attachment failed. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

            logger.info(f"Successfully attached file {file_uuid} to node {node_uuid}")
            return True

        except Exception as e:
            logger.error(f"Error attaching file to node: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            return False

    def _verify_file_attachment(self, node_uuid: str) -> Optional[Dict]:
        """
        Verify that files are attached to a digital object node

        Args:
            node_uuid: UUID of the digital object node

        Returns:
            Dictionary with file attachment info or None if verification fails
        """
        try:
            session = self._get_session()

            # Query the node with file relationship included
            response = session.get(
                f"{self.base_url}/jsonapi/node/digital_object/{node_uuid}?include=field_file_drop"
            )

            if response.status_code != 200:
                logger.error(f"Verification failed. Status: {response.status_code}")
                return None

            result = response.json()
            node_data = result.get('data', {})
            relationships = node_data.get('relationships', {})
            field_file_drop = relationships.get('field_file_drop', {})
            files_data = field_file_drop.get('data', [])

            if isinstance(files_data, list):
                file_count = len(files_data)
            elif files_data:
                file_count = 1
            else:
                file_count = 0

            logger.info(f"Verification: Node {node_uuid} has {file_count} file(s) attached")

            return {
                'node_uuid': node_uuid,
                'file_count': file_count,
                'files': files_data
            }

        except Exception as e:
            logger.error(f"Error verifying file attachment: {str(e)}")
            return None

    def _prepare_sbf_metadata(
        self,
        title: str,
        ocr_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Prepare Strawberry Field (SBF) metadata structure

        Args:
            title: Title of the object
            ocr_text: OCR extracted text
            metadata: Additional metadata
            tags: List of tags

        Returns:
            SBF-formatted metadata dictionary
        """
        metadata = metadata or {}
        tags = tags or []

        # Generate rich description from available metadata
        description_parts = []

        # Start with file type info
        if metadata.get('is_pdf'):
            pages = metadata.get('pages_processed')
            if pages:
                description_parts.append(f"PDF document ({pages} page{'s' if pages != 1 else ''})")
            else:
                description_parts.append("PDF document")
        elif metadata.get('file_extension'):
            description_parts.append(f"{metadata['file_extension'].upper()} document")
        else:
            description_parts.append("Digital document")

        # Add file size if available
        if metadata.get('file_size'):
            size_kb = metadata['file_size'] / 1024
            if size_kb < 1024:
                description_parts.append(f"{size_kb:.0f}KB")
            else:
                description_parts.append(f"{size_kb/1024:.1f}MB")

        # Add source collection info
        if metadata.get('folder_path'):
            folder_name = metadata['folder_path'].rstrip('/').split('/')[-1]
            description_parts[0] += f" from {folder_name} collection"

        description = ", ".join(description_parts) + "."

        # Add processing information
        processing_info = []
        if metadata.get('processed_at'):
            try:
                from datetime import datetime as dt
                proc_date = dt.fromisoformat(metadata['processed_at'].replace('Z', '+00:00'))
                processing_info.append(f"Processed on {proc_date.strftime('%B %d, %Y')}")
            except:
                pass

        if metadata.get('provider'):
            provider_name = metadata['provider'].replace('_', ' ').title()
            processing_info.append(f"using {provider_name} OCR")

        if processing_info:
            description += " " + " ".join(processing_info) + "."

        # Add content statistics
        text_len = metadata.get('text_length') or len(ocr_text)
        word_count = metadata.get('words_count') or len(ocr_text.split()) if ocr_text else 0
        confidence = metadata.get('confidence', 0.0)

        if text_len and word_count:
            stats = f"Contains {text_len:,} characters across {word_count:,} words"
            if confidence > 0:
                stats += f" with {confidence*100:.0f}% confidence"
            description += f" {stats}."

        # Add language info
        language = metadata.get('language', 'unknown')
        if language and language != 'unknown':
            lang_names = {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'en-hi': 'English-Hindi Mixed'
            }
            description += f" Language: {lang_names.get(language, language)}."

        # Build comprehensive SBF structure based on schema.org and Archipelago conventions
        sbf_data = {
            '@context': 'http://schema.org',
            '@type': 'DigitalDocument',
            'label': title,
            'name': title,
            'description': metadata.get('description', description),
            'text': ocr_text,  # Full OCR text
            'dateCreated': datetime.utcnow().isoformat(),
            'keywords': tags,

            # OCR specific metadata - enhanced with all available fields
            'ocr_metadata': {
                'provider': metadata.get('provider', 'unknown'),
                'confidence': metadata.get('confidence', 0.0),
                'language': metadata.get('language', 'unknown'),
                'processing_date': metadata.get('processed_at') or datetime.utcnow().isoformat(),
                'character_count': text_len,
                'word_count': word_count,
                'text_length': metadata.get('text_length'),
                'blocks_count': metadata.get('blocks_count'),
                'status': metadata.get('status', 'success')
            },

            # File information
            'file_info': {
                'filename': metadata.get('filename'),
                'file_path': metadata.get('file_path'),
                'file_size': metadata.get('file_size'),
                'file_extension': metadata.get('file_extension'),
                'is_pdf': metadata.get('is_pdf'),
                'pages_processed': metadata.get('pages_processed')
            },

            # Source information
            'source_info': {
                'collection': metadata.get('source_collection'),
                'folder_path': metadata.get('folder_path')
            }
        }

        # Clean up None values from nested objects
        sbf_data['ocr_metadata'] = {k: v for k, v in sbf_data['ocr_metadata'].items() if v is not None}
        sbf_data['file_info'] = {k: v for k, v in sbf_data['file_info'].items() if v is not None}
        sbf_data['source_info'] = {k: v for k, v in sbf_data['source_info'].items() if v is not None}

        # Add standard metadata fields
        if metadata.get('file_type'):
            sbf_data['encodingFormat'] = metadata['file_type']

        if metadata.get('original_filename'):
            sbf_data['alternateName'] = metadata['original_filename']

        if metadata.get('file_size'):
            sbf_data['contentSize'] = str(metadata['file_size'])

        # Add custom metadata fields
        if metadata.get('custom_fields'):
            sbf_data.update(metadata['custom_fields'])

        return sbf_data

    def create_bulk_collection(
        self,
        collection_title: str,
        document_results: List[Dict],
        collection_metadata: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create a collection in Archipelago for bulk processed documents

        Args:
            collection_title: Title for the collection
            document_results: List of processed document results
            collection_metadata: Additional metadata for the collection

        Returns:
            Dictionary with collection info and created document IDs
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        try:
            csrf_token = self._login()
            if not csrf_token:
                return None

            # Create collection node
            collection_metadata = collection_metadata or {}

            # Collections don't have field_sbf_json - only basic fields
            # The collection metadata will be in the individual digital objects
            session = self._get_session()
            headers = {
                'Content-Type': 'application/vnd.api+json',
                'X-CSRF-Token': csrf_token
            }

            # Prepare collection description
            description = collection_metadata.get('description', f'Bulk OCR processed collection: {collection_title}')
            summary = collection_metadata.get('summary', {})
            if summary:
                description += f"\n\nSummary: {summary.get('total_files', 0)} files processed, " \
                              f"{summary.get('successful', 0)} successful, {summary.get('failed', 0)} failed."

            collection_data = {
                'data': {
                    'type': 'node--digital_object_collection',
                    'attributes': {
                        'title': collection_title
                        # Don't set 'status' when content moderation is enabled
                        # Use 'moderation_state' instead if needed
                        # Note: Collections may have a body/description field, but it varies by Archipelago setup
                        # For now, we'll use the minimal required field (title) only
                    }
                }
            }

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object_collection",
                json=collection_data,
                headers=headers
            )

            if response.status_code != 201:
                logger.error(f"Failed to create collection. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")

                # Check if it's an S3 storage issue
                if 's3://' in response.text or 'storage' in response.text.lower():
                    logger.warning("Archipelago S3 storage not configured. Creating documents without collection.")
                    collection_id = None  # Skip collection, create documents only
                else:
                    response.raise_for_status()
            else:
                collection_result = response.json()
                # Get the internal node ID (integer), not the UUID
                collection_id = collection_result.get('data', {}).get('attributes', {}).get('drupal_internal__nid')
                collection_uuid = collection_result.get('data', {}).get('id')
                logger.info(f"Created collection in Archipelago: node_id={collection_id}, uuid={collection_uuid}")

            # Create individual documents and link to collection
            created_documents = []
            logger.info(f"Creating documents with collection_id: {collection_id}")
            for idx, doc_ in enumerate(document_results):
                try:
                    # LOG: Check what's in the doc object from document_results
                    doc_text = doc_.get('text', '')
                    logger.info(f"=== DOCUMENT {idx+1} FROM document_results ===")
                    logger.info(f"File: {doc_.get('file')}")
                    logger.info(f"File path: {doc_.get('file_path')}")
                    logger.info(f"Text length from doc: {len(doc_text)}")
                    logger.info(f"Text preview (first 200 chars): {doc_text[:200]}")

                    # Prepare ocr_data for the mapper
                    ocr_data = {
                        'name': doc_.get('file', f'Document {idx + 1}'),
                        'text': doc_text,#doc.get('text', ''),
                        'label': doc_.get('file', f'Document {idx + 1}'),
                        'description': f"OCR processed document: {doc_.get('file')}",
                        'file_info': {
                            'filename': doc_.get('file'),
                            'file_path': doc_.get('file_path'),
                        },
                        'ocr_metadata': {
                            'provider': doc_.get('provider'),
                            'confidence': doc_.get('confidence'),
                            'language': doc_.get('detected_language') or doc_.get('language'),
                            'processing_date': doc_.get('processed_at'),
                            'character_count': doc_.get('text_length'),
                            'word_count': doc_.get('words_count'),
                        },
                        'source_info': {
                            'collection': collection_metadata.get('job_id'),
                            'folder_path': collection_metadata.get('summary', {}).get('folder_path')
                        }
                    }

                    # LOG: Verify ocr_data has correct text
                    logger.info(f"OCR data text length: {len(ocr_data.get('text', ''))}")

                    # Use the mapper-based creation method
                    # Generate unique file IDs based on file path hash to ensure documents array and dr:fid are populated
                    import hashlib
                    file_path = doc_.get('file_path', '') or doc_.get('file', '')
                    unique_string = f"{collection_metadata.get('job_id', '')}:{file_path}:{idx}"
                    file_id = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
                    logger.info(f"Calling create_digital_object_from_ocr_data with collection_id={collection_id}, file_id={file_id}")
                    doc_result = self.create_digital_object_from_ocr_data(
                        ocr_data=ocr_data,
                        collection_id=collection_id,
                        file_id=file_id
                    )
                    if doc_result:
                        created_documents.append(doc_result)
                        logger.info(f"Created document {idx+1}/{len(document_results)}: {doc_.get('file')}")
                except Exception as e:
                    logger.error(f"Failed to create document {doc_.get('file')}: {str(e)}", exc_info=True)

            return {
                'success': True,
                'collection_id': collection_id,
                'collection_url': f"{self.base_url}/do/{collection_id}" if collection_id else None,
                'created_documents': len(created_documents),
                'total_documents': len(document_results),
                'document_ids': [d['node_id'] for d in created_documents],
                'warning': 'Collection creation skipped due to Archipelago storage configuration' if not collection_id else None
            }

        except Exception as e:
            logger.error(f"Error creating bulk collection in Archipelago: {str(e)}", exc_info=True)
            return None

    def create_digital_object_from_ocr_data(
        self,
        ocr_data: Dict[str, Any],
        collection_id: Optional[str] = None,
        file_id: Optional[int] = None,
        use_ami_pattern: bool = True
    ) -> Optional[Dict]:
        """
        Create a digital object from OCR data format using the data mapper

        Args:
            ocr_data: OCR data in input format (from input_ocr_data.json)
            collection_id: Optional collection ID to link the document to
            file_id: Optional file ID for document reference
            use_ami_pattern: If True, upload files FIRST using AMI pattern (recommended)

        Returns:
            Dictionary with created node information or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        logger.info("create_digital_object_from_ocr_data method called.")
        logger.info(f"AMI pattern enabled: {use_ami_pattern}")

        try:
            # LOG: Check input OCR text
            input_text = ocr_data.get('text', '')
            logger.info(f"=== INPUT OCR TEXT DEBUG ===")
            logger.info(f"Input text length: {len(input_text)}")
            logger.info(f"Input text preview (first 200 chars): {input_text[:200]}")
            logger.info(f"Input text preview (last 100 chars): {input_text[-100:]}")

            # Map OCR data to Archipelago format
            # Disable file upload in DataMapper - we'll upload after node creation
            logger.info("Mapping OCR data to Archipelago format...")
            archipelago_data = DataMapper.map_ocr_to_archipelago(
                ocr_data=ocr_data,
                collection_id=collection_id,
                file_id=file_id,
                include_file_reference=False  # Don't upload yet - will upload after node creation
            )

            # LOG: Check mapped text
            mapped_note = archipelago_data.get('note', '')
            mapped_full_text = archipelago_data.get('ocr_full_text', '')
            logger.info(f"=== MAPPED TEXT DEBUG ===")
            logger.info(f"Mapped note length: {len(mapped_note)}")
            logger.info(f"Mapped full text length: {len(mapped_full_text)}")
            logger.info(f"Mapped note preview (first 200 chars): {mapped_note[:200]}")

            #logger.info(f"Archipelago data: {json.dumps(archipelago_data, indent=2)}")

            csrf_token = self._login()
            if not csrf_token:
                return None

            session = self._get_session()
            import json as json_lib
            import os

            # Get file path from OCR data
            file_info = ocr_data.get('file_info', {})
            file_path = file_info.get('file_path', '')

            # ====================================================================
            # NEW: AMI PATTERN - Upload files FIRST, get FID, then create metadata
            # ====================================================================
            if use_ami_pattern and file_path and os.path.exists(file_path):
                logger.info("=== Using AMI Pattern: Upload file BEFORE creating metadata ===")

                # Upload file first using AMI pattern
                upload_result = self.upload_file_before_metadata(
                    file_path=file_path,
                    csrf_token=csrf_token
                )

                if upload_result:
                    drupal_file_id = upload_result['fid']
                    field_name = upload_result['field_name']

                    logger.info(f"✓ File uploaded successfully (AMI pattern)")
                    logger.info(f"  FID: {drupal_file_id}")
                    logger.info(f"  Field: {field_name}")

                    # Add FID to metadata BEFORE creating node
                    if field_name in archipelago_data:
                        if isinstance(archipelago_data[field_name], list):
                            archipelago_data[field_name].append(drupal_file_id)
                        else:
                            archipelago_data[field_name] = [drupal_file_id]
                    else:
                        archipelago_data[field_name] = [drupal_file_id]

                    logger.info(f"  Added FID to metadata['{field_name}']: {archipelago_data[field_name]}")

                    # Also update as:document with real FID
                    import uuid as uuid_lib
                    doc_uuid = str(uuid_lib.uuid4())
                    file_basename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)

                    archipelago_data['as:document'] = {
                        f'urn:uuid:{doc_uuid}': {
                            'url': upload_result.get('uri', ''),
                            'name': file_basename,
                            'tags': [],
                            'type': 'Document',
                            'dr:for': field_name,
                            'dr:uuid': doc_uuid,
                            'dr:fid': drupal_file_id,  # REAL FID, not hardcoded 49
                            'checksum': '',
                            'sequence': 1,
                            'dr:filesize': file_size,
                            'dr:mimetype': upload_result['filemime'],
                            'crypHashFunc': 'md5'
                        }
                    }

                    logger.info(f"✓ Updated as:document with real FID: {drupal_file_id} (not hardcoded 49)")
                else:
                    logger.warning("⚠ AMI file upload failed, continuing without file")
            else:
                if not use_ami_pattern:
                    logger.info("AMI pattern disabled, will use old method")
                elif not file_path:
                    logger.info("No file path provided")
                elif not os.path.exists(file_path):
                    logger.warning(f"File not found: {file_path}")
            # ====================================================================
            # END AMI PATTERN
            # ====================================================================")

            # Create the node with mapped Archipelago data
            node_data = {
                'data': {
                    'type': 'node--digital_object',
                    'attributes': {
                        'title': archipelago_data.get('label', 'Untitled'),
                        # Don't set 'status' when content moderation is enabled
                        # Use 'moderation_state' instead if needed
                        'field_descriptive_metadata': {
                            'value': json_lib.dumps(archipelago_data, ensure_ascii=False)
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json; charset=utf-8',
                'X-CSRF-Token': csrf_token
            }

            # Manually serialize to preserve Unicode characters
            import json as json_module
            json_payload = json_module.dumps(node_data, ensure_ascii=False).encode('utf-8')

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object",
                data=json_payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            node_id = result.get('data', {}).get('id')
            node_uuid = result.get('data', {}).get('id')

            logger.info(f"Successfully created digital object in Archipelago: {node_id}")

            # ====================================================================
            # OLD METHOD: Upload file AFTER node creation (only if AMI pattern not used)
            # ====================================================================
            file_uploaded = False
            minio_url = None
            drupal_file_id = None
            archipelago_file_url = None

            if not use_ami_pattern:
                logger.info("=== Using OLD method: Upload file AFTER node creation ===")

                # Log OCR data to understand what file we're working with
                logger.info(f"=== FILE UPLOAD DEBUG ===")
                logger.info(f"OCR data name: {ocr_data.get('name', 'N/A')}")
                logger.info(f"OCR data label: {ocr_data.get('label', 'N/A')}")
                logger.info(f"File info from ocr_data: {file_info}")
                logger.info(f"File path extracted: {file_path}")
                logger.info(f"File exists: {os.path.exists(file_path) if file_path else False}")

                # Clear any existing as:document entries to avoid wrong file associations
                if 'as:document' in archipelago_data:
                    logger.info(f"⚠ Clearing existing as:document entries: {list(archipelago_data['as:document'].keys())}")
                    archipelago_data['as:document'] = {}

            # Upload file to both Archipelago (creates Drupal file entity) and MinIO (backup/CDN)
            if not use_ami_pattern and file_path and os.path.exists(file_path):
                try:
                    from app.services.minio_service import MinIOService
                    import uuid as uuid_lib

                    # Get file info
                    file_basename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)

                    logger.info(f"✓ Starting file upload process:")
                    logger.info(f"  Full path: {file_path}")
                    logger.info(f"  Basename: {file_basename}")
                    logger.info(f"  Size: {file_size} bytes")

                    # STEP 2A: Try to upload to Archipelago to create Drupal file entity (OPTIONAL)
                    # Tries multiple methods: REST API → JSON:API standalone → JSON:API field
                    # If all fail, we'll rely on MinIO URLs only
                    logger.info(f"→ Attempting to upload file to Archipelago (creates Drupal file entity)...")
                    logger.info(f"   Will try multiple upload methods for maximum compatibility")

                    archipelago_upload_result = None
                    drupal_file_id = None
                    archipelago_file_url = None
                    file_uuid_from_archipelago = None
                    content_type = None

                    try:
                        # METHOD 1: Try REST API first (most compatible)
                        logger.info(f"→ Method 1: Drupal REST API")
                        archipelago_upload_result = self._upload_file_rest_api(
                            file_path=file_path,
                            csrf_token=csrf_token
                        )

                        # METHOD 2: If REST API fails, try JSON:API standalone upload
                        if not archipelago_upload_result:
                            logger.info(f"→ Method 2: JSON:API standalone upload")
                            archipelago_upload_result = self._upload_file_standalone(
                                file_path=file_path,
                                csrf_token=csrf_token
                            )

                        # Store result for later use
                        if archipelago_upload_result:
                            drupal_file_id = archipelago_upload_result.get('fid')
                            archipelago_file_url = archipelago_upload_result.get('uri')
                            file_uuid_from_archipelago = archipelago_upload_result.get('uuid')
                            content_type = archipelago_upload_result.get('filemime')

                            logger.info(f"✓ File uploaded to Archipelago successfully:")
                            logger.info(f"  Drupal file ID (fid): {drupal_file_id}")
                            logger.info(f"  File UUID: {file_uuid_from_archipelago}")
                            logger.info(f"  Archipelago URI: {archipelago_file_url}")
                            logger.info(f"  Content-Type: {content_type}")

                            # Now attach the file to the node
                            if file_uuid_from_archipelago:
                                logger.info(f"→ Attaching file to digital object node...")
                                attach_success = self._attach_file_to_node(
                                    node_uuid=node_uuid,
                                    file_uuid=file_uuid_from_archipelago,
                                    csrf_token=csrf_token
                                )
                                if attach_success:
                                    logger.info(f"✓ File successfully attached to node")
                                else:
                                    logger.warning(f"⚠ Failed to attach file to node (file exists but not linked)")
                        else:
                            logger.warning(f"⚠ Archipelago file upload returned no result")
                    except Exception as arch_error:
                        logger.warning(f"⚠ Archipelago file upload failed: {str(arch_error)}")
                        logger.warning(f"   This is OK - will use MinIO URL instead")
                        # Continue with MinIO upload

                    # STEP 2B: Upload to MinIO as backup/CDN
                    logger.info(f"→ Uploading file to MinIO (backup/CDN)...")
                    minio_service = MinIOService()

                    # Generate UUID and add it to filename for MinIO
                    file_uuid = str(uuid_lib.uuid4())
                    name_parts = os.path.splitext(file_basename)
                    file_basename_with_uuid = f"{name_parts[0]}_{file_uuid}{name_parts[1]}"

                    upload_result = minio_service.upload_file(
                        file_path=file_path,
                        object_name=file_basename_with_uuid
                    )

                    if upload_result and upload_result.get('success'):
                        minio_url = upload_result.get('s3_url')
                        http_url = upload_result.get('http_url')
                        if not content_type:
                            content_type = upload_result.get('content_type')

                        logger.info(f"✓ File successfully uploaded to MinIO:")
                        logger.info(f"  S3 URL: {minio_url}")
                        logger.info(f"  HTTP URL: {http_url}")
                        logger.info(f"  Content-Type: {content_type}")
                        logger.info(f"  File size: {file_size} bytes")

                        # METHOD 3: If binary uploads failed, try creating file entity from MinIO URL
                        if not archipelago_upload_result and http_url:
                            logger.info(f"→ Method 3: Create file entity from MinIO URL")
                            archipelago_upload_result = self._create_file_entity_from_url(
                                file_url=http_url,
                                filename=file_basename_with_uuid,
                                filesize=file_size,
                                mime_type=content_type,
                                csrf_token=csrf_token
                            )

                            if archipelago_upload_result:
                                drupal_file_id = archipelago_upload_result.get('fid')
                                file_uuid_from_archipelago = archipelago_upload_result.get('uuid')
                                logger.info(f"✓ File entity created from MinIO URL")
                                logger.info(f"  FID: {drupal_file_id}")
                                logger.info(f"  This file entity points to MinIO URL")

                        # Create proper as:document structure with UUID key
                        # Use the UUID from Archipelago file upload if available
                        doc_uuid = file_uuid_from_archipelago if archipelago_upload_result else str(uuid_lib.uuid4())

                        doc_entry = {
                            'url': http_url,  # MinIO HTTP URL for CDN/backup access
                            'name': file_basename_with_uuid,
                            'tags': [],
                            'type': 'Document',
                            'dr:for': 'documents',
                            'dr:uuid': doc_uuid,
                            'checksum': '',
                            'sequence': 1,
                            'dr:filesize': file_size,
                            'dr:mimetype': content_type,
                            'crypHashFunc': 'md5'
                        }

                        # Add the real Drupal file ID if we successfully uploaded to Archipelago
                        if drupal_file_id is not None:
                            doc_entry['dr:fid'] = drupal_file_id
                            logger.info(f"✓ Using real Drupal file ID in as:document: {drupal_file_id}")
                        else:
                            # Fallback: Use hardcoded file ID 49 when upload fails
                            # This ensures metadata structure is complete
                            doc_entry['dr:fid'] = 49
                            logger.info(f"ℹ No Drupal file ID available (all upload methods failed)")
                            logger.info(f"  Using hardcoded fallback dr:fid: 49")
                            logger.info(f"  File will be accessible via MinIO URL")

                        # Update archipelago_data with proper as:document structure (replacing any existing entries)
                        archipelago_data['as:document'] = {
                            f'urn:uuid:{doc_uuid}': doc_entry
                        }

                        # Populate documents array with Drupal file entity ID if available
                        if drupal_file_id is not None:
                            archipelago_data['documents'] = [drupal_file_id]
                            logger.info(f"✓ Added Drupal file ID to documents array: [{drupal_file_id}]")
                        else:
                            # Use hardcoded file ID 49 in documents array as fallback
                            archipelago_data['documents'] = [49]
                            logger.info(f"ℹ Added hardcoded fallback to documents array: [49]")

                        logger.info(f"✓ Created as:document entry:")
                        logger.info(f"  UUID: {doc_uuid}")
                        logger.info(f"  File name: {file_basename_with_uuid}")
                        logger.info(f"  MinIO URL: {http_url}")
                        if drupal_file_id:
                            logger.info(f"  Drupal file entity: {drupal_file_id} (created via Archipelago)")
                        else:
                            logger.info(f"  Using URL-based access only (no Drupal file entity)")

                        # PATCH the node to update metadata with file links
                        patch_data = {
                            'data': {
                                'type': 'node--digital_object',
                                'id': node_uuid,
                                'attributes': {
                                    'field_descriptive_metadata': {
                                        'value': json_lib.dumps(archipelago_data, ensure_ascii=False)
                                    }
                                }
                            }
                        }

                        # Manually serialize PATCH data to preserve Unicode
                        import json as json_module
                        patch_payload = json_module.dumps(patch_data, ensure_ascii=False).encode('utf-8')

                        patch_response = session.patch(
                            f"{self.base_url}/jsonapi/node/digital_object/{node_uuid}",
                            data=patch_payload,
                            headers=headers
                        )

                        if patch_response.status_code in [200, 204]:
                            logger.info(f"✓ Updated node {node_id} with file links (Archipelago + MinIO)")
                            file_uploaded = True

                            # LOG: Verify text is preserved after PATCH
                            final_note = archipelago_data.get('note', '')
                            final_full_text = archipelago_data.get('ocr_full_text', '')
                            logger.info(f"=== FINAL TEXT DEBUG (after PATCH) ===")
                            logger.info(f"Final note length: {len(final_note)}")
                            logger.info(f"Final full text length: {len(final_full_text)}")
                            logger.info(f"Final note preview (first 200 chars): {final_note[:200]}")
                        else:
                            logger.warning(f"⚠ Failed to update node with file links. Status: {patch_response.status_code}")
                            logger.warning(f"Response: {patch_response.text[:500]}")
                    else:
                        logger.warning(f"⚠ Failed to upload file to MinIO (Archipelago upload may have succeeded)")

                except Exception as e:
                    logger.error(f"✗ Error during file upload process: {str(e)}", exc_info=True)
            else:
                logger.warning(f"⚠ File not found or not specified: {file_path}")

            # Build result message based on upload success
            upload_details = []
            upload_method = None

            # Check if AMI pattern was used and successful
            if use_ami_pattern and 'documents' in archipelago_data and archipelago_data['documents']:
                # AMI pattern was used - check for real FID in metadata
                ami_fid = archipelago_data['documents'][0] if archipelago_data['documents'] else None
                if ami_fid and ami_fid != 49:  # Real FID obtained
                    drupal_file_id = ami_fid
                    upload_details.append(f"File uploaded via AMI pattern (FID: {drupal_file_id})")
                    upload_method = "AMI Pattern (file uploaded BEFORE metadata)"
                    file_uploaded = True
                    logger.info(f"✓✓✓ SUCCESS: Real FID {drupal_file_id} used (NOT hardcoded 49)")
                elif ami_fid == 49:
                    logger.warning("⚠ Hardcoded FID 49 detected - AMI upload may have failed")
                    upload_details.append("AMI upload failed, using fallback")
            elif drupal_file_id:
                upload_details.append(f"Drupal file entity created (ID: {drupal_file_id})")
                upload_method = "Old Method (file uploaded AFTER metadata)"

            if minio_url:
                upload_details.append("MinIO uploaded")

            note = 'OCR text and metadata stored'
            if upload_details:
                note += '; ' + ', '.join(upload_details)
            elif minio_url:
                note += '; file uploaded to MinIO (URL-based access)'
            else:
                note += '; file upload skipped'

            return {
                'success': True,
                'node_id': node_id,
                'node_uuid': node_uuid,
                'url': f"{self.base_url}/do/{node_id}",
                'file_attached': file_uploaded,
                'drupal_file_id': drupal_file_id,
                'archipelago_file_url': archipelago_file_url,
                'minio_url': minio_url,
                'upload_method': upload_method,  # NEW: Shows which method was used
                'ami_pattern_used': use_ami_pattern,  # NEW: Shows if AMI pattern was enabled
                'note': note
            }

        except Exception as e:
            logger.error(f"Error creating digital object from OCR data: {str(e)}", exc_info=True)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None

    def create_digital_object_with_files(
        self,
        metadata: Dict[str, Any],
        file_paths: List[str]
    ) -> Optional[Dict]:
        """
        Create a digital object with files uploaded FIRST (AMI pattern from PHP)

        This implements the workflow from your PHP example:
        1. Upload each file first
        2. Get FID for each file
        3. Map FIDs to appropriate metadata arrays (documents, images, etc.)
        4. Create digital object with file IDs included in metadata

        Args:
            metadata: Base metadata dictionary for the digital object
            file_paths: List of file paths to upload

        Returns:
            Dictionary with created node information or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        try:
            # Step 1: Login and get CSRF token
            csrf_token = self._login()
            if not csrf_token:
                return None

            session = self._get_session()
            import json as json_lib

            logger.info("=== Creating Digital Object with Files (AMI Pattern) ===")
            logger.info(f"Files to upload: {len(file_paths)}")

            # Step 2: Upload all files FIRST and collect FIDs
            uploaded_files = []
            file_id_mapping = {}  # Maps field names to arrays of FIDs

            for file_path in file_paths:
                logger.info(f"\n→ Uploading file: {file_path}")

                upload_result = self.upload_file_before_metadata(
                    file_path=file_path,
                    csrf_token=csrf_token
                )

                if upload_result:
                    uploaded_files.append(upload_result)

                    # Map to appropriate field based on MIME type
                    field_name = upload_result['field_name']  # e.g., 'documents', 'images'
                    fid = upload_result['fid']

                    if field_name not in file_id_mapping:
                        file_id_mapping[field_name] = []

                    file_id_mapping[field_name].append(fid)

                    logger.info(f"  ✓ Mapped FID {fid} to field '{field_name}'")
                else:
                    logger.warning(f"  ✗ Failed to upload file: {file_path}")

            if not uploaded_files:
                logger.error("No files were uploaded successfully")
                return None

            logger.info(f"\n✓ Uploaded {len(uploaded_files)} file(s)")
            logger.info(f"File ID mapping: {file_id_mapping}")

            # Step 3: Add file IDs to metadata
            # Following PHP logic:
            # if (isset($data[$as_specific . 's']) && ($data[$as_specific . 's'] == NULL || is_array($data[$as_specific . 's']))) {
            #     $data[$as_specific . 's'][] = $fid;
            # } else {
            #     $data[$as_file_type . 's'][] = $fid;
            # }

            for field_name, fids in file_id_mapping.items():
                if field_name in metadata:
                    # Field exists - append if it's a list, otherwise make it a list
                    if isinstance(metadata[field_name], list):
                        metadata[field_name].extend(fids)
                    elif metadata[field_name] is None:
                        metadata[field_name] = fids
                    else:
                        metadata[field_name] = [metadata[field_name]] + fids
                else:
                    # Field doesn't exist - create it
                    metadata[field_name] = fids

            logger.info(f"\n→ Creating digital object with file IDs included")

            # Step 4: Create the digital object with file IDs in metadata
            title = metadata.get('label', metadata.get('title', 'Untitled'))

            node_data = {
                'data': {
                    'type': 'node--digital_object',
                    'attributes': {
                        'title': title,
                        'field_descriptive_metadata': {
                            'value': json_lib.dumps(metadata, ensure_ascii=False)
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json; charset=utf-8',
                'X-CSRF-Token': csrf_token
            }

            json_payload = json_lib.dumps(node_data, ensure_ascii=False).encode('utf-8')

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object",
                data=json_payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            node_id = result.get('data', {}).get('id')
            node_uuid = result.get('data', {}).get('id')

            logger.info(f"✓ Successfully created digital object: {node_id}")
            logger.info(f"  Title: {title}")
            logger.info(f"  Files attached: {len(uploaded_files)}")
            for field_name, fids in file_id_mapping.items():
                logger.info(f"  {field_name}: {fids}")

            return {
                'success': True,
                'node_id': node_id,
                'node_uuid': node_uuid,
                'url': f"{self.base_url}/do/{node_id}",
                'files_attached': len(uploaded_files),
                'file_mapping': file_id_mapping,
                'uploaded_files': uploaded_files
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error creating digital object with files: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating digital object with files: {str(e)}", exc_info=True)
            return None

    def create_digital_object_from_raw(self, metadata: Dict[str, Any]) -> Optional[Dict]:
        """
        Create a digital object from raw metadata.

        Args:
            metadata: A dictionary of the metadata.

        Returns:
            Dictionary with created node information or None if failed
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        try:
            csrf_token = self._login()
            if not csrf_token:
                return None

            session = self._get_session()
            import json as json_lib

            title = metadata.get('label', 'Untitled')

            node_data = {
                'data': {
                    'type': 'node--digital_object',
                    'attributes': {
                        'title': title,
                        'field_descriptive_metadata': {
                            'value': json_lib.dumps(metadata, ensure_ascii=False)
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json; charset=utf-8',
                'X-CSRF-Token': csrf_token
            }

            json_payload = json_lib.dumps(node_data, ensure_ascii=False).encode('utf-8')

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object",
                data=json_payload,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            node_id = result.get('data', {}).get('id')

            logger.info(f"Successfully created digital object from raw metadata: {node_id}")

            return {
                'success': True,
                'node_id': node_id,
                'node_url': f"{self.base_url}/do/{node_id}",
                'message': 'Digital object created successfully from raw metadata.'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error creating digital object from raw metadata: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating digital object from raw metadata: {str(e)}", exc_info=True)
            return None

    def create_bulk_from_ocr_data(
        self,
        ocr_data_list: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        collection_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict]:
        """
        Create a collection and bulk upload documents from OCR data format

        Args:
            ocr_data_list: List of OCR data items
            collection_name: Optional name for the collection
            collection_metadata: Optional metadata for the collection

        Returns:
            Dictionary with collection info and created document IDs
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return None

        try:
            # Create collection metadata
            if not collection_name:
                collection_name = f"OCR Collection {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

            collection_meta = DataMapper.create_archipelago_collection_metadata(
                collection_name=collection_name,
                ocr_data_list=ocr_data_list,
                additional_metadata=collection_metadata
            )

            csrf_token = self._login()
            if not csrf_token:
                return None

            session = self._get_session()
            headers = {
                'Content-Type': 'application/vnd.api+json',
                'X-CSRF-Token': csrf_token
            }

            # Create collection node
            collection_data = {
                'data': {
                    'type': 'node--digital_object_collection',
                    'attributes': {
                        'title': collection_name
                        # Don't set 'status' when content moderation is enabled
                        # Use 'moderation_state' instead if needed
                    }
                }
            }

            response = session.post(
                f"{self.base_url}/jsonapi/node/digital_object_collection",
                json=collection_data,
                headers=headers
            )

            collection_id = None
            if response.status_code == 201:
                collection_result = response.json()
                # Get the internal node ID (integer), not the UUID
                collection_id = collection_result.get('data', {}).get('attributes', {}).get('drupal_internal__nid')
                collection_uuid = collection_result.get('data', {}).get('id')
                logger.info(f"Created collection in Archipelago: node_id={collection_id}, uuid={collection_uuid}")
            else:
                logger.warning(f"Collection creation returned status {response.status_code}, proceeding without collection")

            # Create individual documents using mapper
            created_documents = []
            for idx, ocr_data in enumerate(ocr_data_list):
                try:
                    # Generate unique file ID based on file path hash
                    import hashlib
                    file_path = ocr_data.get('file_info', {}).get('file_path', '') or ocr_data.get('name', '')
                    unique_string = f"{collection_name}:{file_path}:{idx}"
                    file_id = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)

                    doc_result = self.create_digital_object_from_ocr_data(
                        ocr_data=ocr_data,
                        collection_id=collection_id,
                        file_id=file_id
                    )
                    if doc_result:
                        created_documents.append(doc_result)
                        logger.info(f"Created document {idx+1}/{len(ocr_data_list)}: {ocr_data.get('name', 'unnamed')}")
                except Exception as e:
                    logger.error(f"Failed to create document {idx+1}: {str(e)}", exc_info=True)

            return {
                'success': True,
                'collection_id': collection_id,
                'collection_url': f"{self.base_url}/do/{collection_id}" if collection_id else None,
                'created_documents': len(created_documents),
                'total_documents': len(ocr_data_list),
                'document_ids': [d['node_id'] for d in created_documents],
                'warning': 'Collection creation skipped due to Archipelago storage configuration' if not collection_id else None
            }

        except Exception as e:
            logger.error(f"Error creating bulk collection from OCR data: {str(e)}", exc_info=True)
            return None

    def update_descriptive_metadata(
        self,
        node_uuid: str,
        metadata_json: str
    ) -> bool:
        """
        Update the descriptive metadata of a digital object in Archipelago.

        Args:
            node_uuid: UUID of the digital object node to update.
            metadata_json: A JSON string of the new descriptive metadata.

        Returns:
            True if the update was successful, False otherwise.
        """
        if not self.enabled:
            logger.warning("Archipelago integration is disabled")
            return False

        try:
            csrf_token = self._login()
            if not csrf_token:
                return False

            session = self._get_session()

            patch_data = {
                'data': {
                    'type': 'node--digital_object',
                    'id': node_uuid,
                    'attributes': {
                        'field_descriptive_metadata': {
                            'value': metadata_json
                        }
                    }
                }
            }

            headers = {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json',
                'X-CSRF-Token': csrf_token
            }

            logger.info(f"Updating descriptive metadata for node {node_uuid}")
            response = session.patch(
                f"{self.base_url}/jsonapi/node/digital_object/{node_uuid}",
                json=patch_data,
                headers=headers
            )

            if response.status_code not in [200, 204]:
                logger.error(f"Metadata update failed for node {node_uuid}. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

            logger.info(f"Successfully updated metadata for node {node_uuid}")
            return True

        except Exception as e:
            logger.error(f"Error updating metadata for node {node_uuid}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:500]}")
            return False

    def check_connection(self) -> bool:
        """
        Test connection to Archipelago Commons

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.enabled:
                return False

            # First, authenticate with Archipelago to ensure we have a valid session
            csrf_token = self._login()
            if not csrf_token:
                logger.error("Could not authenticate with Archipelago")
                return False

            # Then test the JSON API endpoint with authenticated session
            session = self._get_session()
            response = session.get(f"{self.base_url}/jsonapi", verify=self._should_verify_ssl())
            response.raise_for_status()

            logger.info("Successfully connected to Archipelago Commons")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Archipelago: {str(e)}")
            return False
