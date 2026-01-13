"""
Data mapper for converting OCR data format to Archipelago Commons format
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid
import logging
import os
import json
from urllib.parse import quote

logger = logging.getLogger(__name__)


class DataMapper:
    """Maps data from input OCR format to Archipelago template format"""

    @staticmethod
    def upload_file_to_minio(
        file_path: str,
        object_name: Optional[str] = None
    ) -> Optional[Tuple[str, str, int]]:
        """
        Upload a file to MinIO and return S3 URL

        Args:
            file_path: Path to the file to upload
            object_name: Name for the object in MinIO (uses filename if not provided)

        Returns:
            Tuple of (s3_url, mime_type, file_size) or None if upload failed
        """
        try:
            from app.services.minio_service import MinIOService

            minio_service = MinIOService()

            if not minio_service.enabled:
                logger.warning("MinIO is disabled, cannot upload file")
                return None

            # Resolve file path
            if not os.path.isabs(file_path):
                gvpocr_path = os.getenv('GVPOCR_PATH', '/mnt/sda1/mango1_home/Bhushanji')
                gvpocr_basename = os.path.basename(gvpocr_path.rstrip('/'))

                if file_path.startswith(gvpocr_basename + '/') or file_path.startswith(gvpocr_basename + os.sep):
                    file_path = file_path[len(gvpocr_basename) + 1:]

                file_path = os.path.join(gvpocr_path, file_path)

            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found for MinIO upload: {file_path}")
                return None

            # Use provided object name or generate from file path
            if not object_name:
                object_name = os.path.basename(file_path)

            # Check if already uploaded
            if minio_service.file_exists(object_name):
                logger.info(f"File already exists in MinIO: {object_name}")
                file_info = minio_service.get_file_info(object_name)
                if file_info:
                    return (file_info['s3_url'], file_info['content_type'], file_info['size'])

            # Upload the file
            result = minio_service.upload_file(
                file_path=file_path,
                object_name=object_name
            )

            if result and result.get('success'):
                logger.info(f"Successfully uploaded file to MinIO: {result['s3_url']}")
                return (result['s3_url'], result['content_type'], result['size'])
            else:
                logger.error(f"Failed to upload file to MinIO: {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error uploading file to MinIO: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def map_ocr_to_archipelago(
        ocr_data: Dict[str, Any],
        collection_id: Optional[str] = None,
        file_id: Optional[int] = None,
        include_file_reference: bool = False
    ) -> Dict[str, Any]:
        """
        Map OCR data format to Archipelago template format

        Args:
            ocr_data: Input data in OCR format (from input_ocr_data.json)
            collection_id: Optional collection ID to link the document to
            file_id: Optional file ID for the document reference
            include_file_reference: Whether to include as:document S3 file references
                                   (only set True if Archipelago has S3 storage configured)

        Returns:
            Data in Archipelago template format
        """
        print("DataMapper.map_ocr_to_archipelago method called.")
        print(f"Input OCR data for mapping: {json.dumps(ocr_data, indent=2)}")
        try:
            # Extract basic information from OCR data
            name = ocr_data.get('name', '')
            text = ocr_data.get('text', '')
            label = ocr_data.get('label', name)
            description = ocr_data.get('description', '')

            # Extract file information
            file_info = ocr_data.get('file_info', {})
            filename = file_info.get('filename', name)
            file_path = file_info.get('file_path', '')

            # Extract OCR metadata
            ocr_metadata = ocr_data.get('ocr_metadata', {})
            language_code = ocr_metadata.get('language', 'en')

            # Map language codes to full names
            language_map = {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ar': 'Arabic',
                'ru': 'Russian',
                'pt': 'Portuguese',
                'it': 'Italian'
            }
            language = [language_map.get(language_code, language_code)]

            # Extract source info
            source_info = ocr_data.get('source_info', {})
            collection_folder = source_info.get('folder_path', '')

            # Extract generator info
            generator_info = ocr_data.get('as:generator', {})
            if not generator_info:
                generator_info = {
                    'type': 'Update',
                    'actor': {
                        'url': 'http://localhost:8001/form/descriptive-metadata',
                        'name': 'descriptive_metadata',
                        'type': 'Service'
                    },
                    'endTime': datetime.utcnow().isoformat() + 'Z',
                    'summary': 'Generator',
                    '@context': 'https://www.w3.org/ns/activitystreams'
                }

            # Build the as:document structure if we have file information
            # If include_file_reference=True, upload file to MinIO and get real S3 URL
            as_document = {}
            if filename and include_file_reference:
                doc_uuid = str(uuid.uuid4())

                # Default values
                file_size = 0
                mime_type = 'application/octet-stream'
                s3_url = f"s3://files/{filename}"  # Default S3 URL

                # Try to upload file to MinIO and get real S3 URL
                if file_path:
                    logger.info(f"Uploading file to MinIO: {file_path}")
                    upload_result = DataMapper.upload_file_to_minio(
                        file_path=file_path,
                        object_name=filename
                    )

                    if upload_result:
                        s3_url, mime_type, file_size = upload_result
                        logger.info(f"File uploaded to MinIO successfully: {s3_url}")
                    else:
                        logger.warning(f"MinIO upload failed, using default values for {filename}")
                        # Fall back to guessing mime type from filename
                        if filename.lower().endswith('.pdf'):
                            mime_type = 'application/pdf'
                        elif filename.lower().endswith(('.jpg', '.jpeg')):
                            mime_type = 'image/jpeg'
                        elif filename.lower().endswith('.png'):
                            mime_type = 'image/png'
                        elif filename.lower().endswith('.tif'):
                            mime_type = 'image/tiff'
                else:
                    # No file path provided, guess mime type from filename
                    if filename.lower().endswith('.pdf'):
                        mime_type = 'application/pdf'
                    elif filename.lower().endswith(('.jpg', '.jpeg')):
                        mime_type = 'image/jpeg'
                    elif filename.lower().endswith('.png'):
                        mime_type = 'image/png'
                    elif filename.lower().endswith('.tif'):
                        mime_type = 'image/tiff'

                # Extract PDF metadata if it's a PDF
                flv_exif = {}
                flv_pdfinfo = {}
                flv_pronom = {}
                checksum = ''

                if mime_type == 'application/pdf' and file_path and os.path.exists(file_path):
                    try:
                        import PyPDF2
                        import hashlib

                        # Calculate MD5 checksum
                        with open(file_path, 'rb') as f:
                            checksum = hashlib.md5(f.read()).hexdigest()

                        # Extract PDF info
                        with open(file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            page_count = len(pdf_reader.pages)

                            # Build flv:exif metadata
                            flv_exif = {
                                'MIMEType': 'application/pdf',
                                'PageCount': page_count,
                                'FileSize': f"{file_size / 1024:.1f} kB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                            }

                            # Try to get PDF metadata
                            if pdf_reader.metadata:
                                if pdf_reader.metadata.title:
                                    flv_exif['Title'] = pdf_reader.metadata.title
                                if pdf_reader.metadata.author:
                                    flv_exif['Author'] = pdf_reader.metadata.author
                                if pdf_reader.metadata.creator:
                                    flv_exif['Creator'] = pdf_reader.metadata.creator
                                if pdf_reader.metadata.producer:
                                    flv_exif['Producer'] = pdf_reader.metadata.producer

                            # Build flv:pdfinfo with page dimensions
                            flv_pdfinfo = {}
                            for i, page in enumerate(pdf_reader.pages, 1):
                                box = page.mediabox
                                width = int(float(box.width))
                                height = int(float(box.height))
                                flv_pdfinfo[str(i)] = {
                                    'width': str(width),
                                    'height': str(height),
                                    'rotation': '0',
                                    'orientation': 'TopLeft'
                                }

                            # Add pronom info
                            flv_pronom = {
                                'label': 'Acrobat PDF - Portable Document Format',
                                'mimetype': 'application/pdf',
                                'pronom_id': 'info:pronom/fmt/18',
                                'detection_type': 'signature'
                            }

                            logger.info(f"Extracted PDF metadata: {page_count} pages, checksum: {checksum}")
                    except Exception as e:
                        logger.warning(f"Could not extract PDF metadata: {str(e)}")

                # Create as:document structure with real S3 URL and metadata
                doc_entry = {
                    'url': quote(s3_url, safe=':/'),  # Real S3 URL from MinIO
                    'name': filename,
                    'tags': [],
                    'type': 'Document',
                    'dr:for': 'documents',
                    'dr:uuid': doc_uuid,
                    'checksum': checksum,
                    'sequence': 1,
                    'dr:filesize': file_size,
                    'dr:mimetype': mime_type,
                    'crypHashFunc': 'md5'
                }

                # Only add dr:fid if we have a valid Drupal file entity ID
                # Note: file_id can be 0, so check for None explicitly
                if file_id is not None:
                    doc_entry['dr:fid'] = file_id

                # Add PDF-specific metadata if available
                if flv_exif:
                    doc_entry['flv:exif'] = flv_exif
                if flv_pdfinfo:
                    doc_entry['flv:pdfinfo'] = flv_pdfinfo
                if flv_pronom:
                    doc_entry['flv:pronom'] = flv_pronom

                as_document = {f"urn:uuid:{doc_uuid}": doc_entry}

            # Build the Archipelago template structure
            logger.info(f"Building Archipelago data with collection_id={collection_id}, file_id={file_id}")
            archipelago_data = {
                'note': '',
                'type': ocr_data.get('@type', 'DigitalDocument'),
                'viaf': '',
                'label': label,
                'model': [],
                'owner': 'Vipassana Research Institute',  # Can be filled with organization info
                'audios': [],
                'images': [],
                'models': [],
                'rights': "All rights Owned by Vipassana Research Institute",
                'videos': [],
                'creator': 'VRI',
                'ap:tasks': {
                    'ap:sortfiles': 'index'
                },
                'duration': '',
                'ispartof': [],
                'language': language,
                'documents': [file_id] if file_id is not None else [],
                'edm_agent': '',
                'publisher': '',
                'ismemberof': [collection_id] if collection_id else [],
                'as:document': as_document,
                'creator_lod': [],
                'description': description,
                'interviewee': '',
                'interviewer': '',
                'pubmed_mesh': None,
                'sequence_id': '',
                'subject_loc': [],
                'website_url': '',
                'as:generator': generator_info,
                'date_created': ocr_data.get('dateCreated', datetime.utcnow().isoformat()),
                'issue_number': None,
                'date_published': '',
                'subjects_local': None,
                'term_aat_getty': '',
                'ap:entitymapping': {
                    'entity:file': [
                        'model',
                        'audios',
                        'images',
                        'videos',
                        'documents',
                        'upload_associated_warcs'
                    ],
                    'entity:node': [
                        'ispartof',
                        'ismemberof'
                    ]
                },
                'europeana_agents': '',
                'europeana_places': [],
                'local_identifier': '',
                'subject_wikidata': [],
                'date_created_edtf': '',
                'date_created_free': None,
                'date_embargo_lift': None,
                'physical_location': None,
                'related_item_note': None,
                'rights_statements': '',
                'europeana_concepts': [],
                'geographic_location': {},
                'note_publishinginfo': None,
                'subject_lcgft_terms': '',
                'upload_associated_warcs': [],
                'physical_description_extent': '',
                'subject_lcnaf_personal_names': '',
                'subject_lcnaf_corporate_names': '',
                'subjects_local_personal_names': '',
                'related_item_host_location_url': None,
                'subject_lcnaf_geographic_names': [],
                'related_item_host_display_label': None,
                'related_item_host_local_identifier': None,
                'related_item_host_title_info_title': '',
                'related_item_host_type_of_resource': None,
                'physical_description_note_condition': None
            }

            # Add keywords if present
            keywords = ocr_data.get('keywords', [])
            if keywords:
                # Convert keywords to subject_local format
                archipelago_data['subjects_local'] = ', '.join(keywords)

            # Add OCR-specific metadata to description if not already present
            if not description:
                ocr_desc_parts = []

                # Add OCR provider info
                provider = ocr_metadata.get('provider', '')
                if provider:
                    ocr_desc_parts.append(f"Processed using {provider.replace('_', ' ').title()} OCR")

                # Add confidence info
                confidence = ocr_metadata.get('confidence')
                if confidence:
                    ocr_desc_parts.append(f"Confidence: {confidence*100:.1f}%")

                # Add word count
                word_count = ocr_metadata.get('word_count')
                if word_count:
                    ocr_desc_parts.append(f"{word_count} words")

                # Add character count
                char_count = ocr_metadata.get('character_count')
                if char_count:
                    ocr_desc_parts.append(f"{char_count} characters")

                if ocr_desc_parts:
                    archipelago_data['description'] = '. '.join(ocr_desc_parts) + '.'

            # Store the full OCR text in multiple fields for better preservation and searchability
            if text:
                # Store full text in a dedicated field (Archipelago supports custom fields in SBF)
                archipelago_data['ocr_full_text'] = text
                # Also store in note field (truncated for display)
                archipelago_data['note'] = text[:5000]  # Limit to first 5000 chars for note field display

            logger.info(f"Successfully mapped OCR data to Archipelago format: {label}")
            logger.info(f"OCR text preserved: {len(text)} characters")
            return archipelago_data

        except Exception as e:
            logger.error(f"Error mapping OCR data to Archipelago format: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def map_bulk_ocr_to_archipelago(
        ocr_data_list: List[Dict[str, Any]],
        collection_id: Optional[str] = None,
        start_file_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Map a list of OCR data items to Archipelago format

        Args:
            ocr_data_list: List of OCR data items
            collection_id: Optional collection ID to link documents to
            start_file_id: Starting file ID for documents

        Returns:
            List of mapped Archipelago data
        """
        mapped_items = []

        for idx, ocr_data in enumerate(ocr_data_list):
            try:
                file_id = start_file_id + idx
                mapped_item = DataMapper.map_ocr_to_archipelago(
                    ocr_data,
                    collection_id=collection_id,
                    file_id=file_id
                )
                mapped_items.append(mapped_item)
            except Exception as e:
                logger.error(f"Error mapping item {idx}: {str(e)}")
                continue

        return mapped_items

    @staticmethod
    def create_archipelago_collection_metadata(
        collection_name: str,
        ocr_data_list: List[Dict[str, Any]],
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create collection-level metadata for Archipelago

        Args:
            collection_name: Name of the collection
            ocr_data_list: List of OCR data items in the collection
            additional_metadata: Optional additional metadata

        Returns:
            Collection metadata dictionary
        """
        additional_metadata = additional_metadata or {}

        # Calculate collection statistics
        total_items = len(ocr_data_list)
        total_words = sum(
            item.get('ocr_metadata', {}).get('word_count', 0)
            for item in ocr_data_list
        )
        total_chars = sum(
            item.get('ocr_metadata', {}).get('character_count', 0)
            for item in ocr_data_list
        )

        # Get unique languages
        languages = set()
        for item in ocr_data_list:
            lang = item.get('ocr_metadata', {}).get('language', '')
            if lang:
                languages.add(lang)

        description = f"Collection of {total_items} digitized documents"
        if total_words:
            description += f" containing {total_words:,} words"
        if languages:
            description += f". Languages: {', '.join(sorted(languages))}"

        collection_metadata = {
            'type': 'Collection',
            'label': collection_name,
            'description': additional_metadata.get('description', description),
            'date_created': datetime.utcnow().isoformat(),
            'language': list(languages),
            'rights': additional_metadata.get('rights', ''),
            'publisher': additional_metadata.get('publisher', ''),
            'note': f"Total items: {total_items}, Total words: {total_words:,}, Total characters: {total_chars:,}",
            'as:generator': {
                'type': 'Create',
                'actor': {
                    'url': 'http://localhost:8001/gvpocr',
                    'name': 'gvpocr',
                    'type': 'Service'
                },
                'endTime': datetime.utcnow().isoformat() + 'Z',
                'summary': 'Collection Generator',
                '@context': 'https://www.w3.org/ns/activitystreams'
            }
        }

        return collection_metadata
