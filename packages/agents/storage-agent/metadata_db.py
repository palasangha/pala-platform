"""
Metadata Database Module

Centralized metadata management for storage-agent.
Tracks all content across ALL providers with:
- SHA-256 hash-based deduplication
- Version history
- Cross-provider search and querying
- Provider-agnostic metadata storage

This is the coordination layer that enables:
1. Finding duplicates across all providers
2. Searching content regardless of storage location
3. Tracking which provider stores what content
"""

import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ContentMetadata:
    """Metadata for stored content - unified schema"""
    # Core identification
    document_id: str
    type: str
    file_hash: str
    
    # File information
    original_file: str
    file_format: str
    file_size: int
    
    # Content storage
    processed_data: Dict[str, Any]  # The actual content
    metadata: Dict[str, Any]
    app_data: Dict[str, Any]
    
    # Tracking
    created_by: str
    created_at: str
    updated_at: str
    version: int = 1
    deleted_at: Optional[str] = None
    
    # Provider information
    provider_id: str = "local-provider"
    storage_location: str = ""
    signature: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class MetadataDB:
    """
    Metadata database manager
    
    Maintains a unified index of all content across all storage providers.
    Enables deduplication, search, and cross-provider coordination.
    """
    
    def __init__(self, db_path: str = "./storage_metadata.db"):
        """
        Initialize metadata database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create parent directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_db()
        
        logger.info(f"MetadataDB initialized: {db_path}")
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop old schema if it exists (for migration from old to new schema)
        try:
            cursor.execute('DROP TABLE IF EXISTS content_versions')
            cursor.execute('DROP INDEX IF EXISTS idx_content_type')
            cursor.execute('DROP TABLE IF EXISTS content_metadata')
            conn.commit()
            logger.info("Dropped old schema tables for migration")
        except Exception as e:
            logger.debug(f"No old schema to drop: {e}")
        
        # Content metadata table - unified schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_metadata (
                document_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                original_file TEXT,
                file_format TEXT,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                processed_data TEXT NOT NULL,
                metadata TEXT NOT NULL,
                app_data TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT,
                provider_id TEXT NOT NULL,
                storage_location TEXT,
                signature TEXT,
                tags TEXT
            )
        ''')
        
        # Deduplication index on hash (CRITICAL for cross-provider dedup)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_hash ON content_metadata(file_hash)
        ''')
        
        # Type index for filtering
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_type ON content_metadata(type)
        ''')
        
        # Created by index for filtering
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_by ON content_metadata(created_by)
        ''')
        
        # Unified extractions table (generic schema for all extraction tools)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unified_extractions (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                data TEXT NOT NULL,
                data_type TEXT NOT NULL,
                metadata TEXT,
                provider TEXT,
                confidence REAL,
                created_by TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Indexes for unified extractions
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source_type ON unified_extractions(source_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source_id ON unified_extractions(source_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON unified_extractions(created_at)
        ''')
        
        # Provider index for provider-specific queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_provider ON content_metadata(provider_id)
        ''')
        
        # Created timestamp index for sorting
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON content_metadata(created_at)
        ''')
        
        # Version history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                metadata TEXT NOT NULL,
                updated_by TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(content_id) REFERENCES content_metadata(content_id),
                UNIQUE(content_id, version)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Metadata database initialized: {self.db_path}")
    
    def calculate_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of content
        
        Args:
            content: Binary content
            
        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(content).hexdigest()
    
    def find_by_hash(self, file_hash: str) -> Optional[ContentMetadata]:
        """
        Find content by hash (for deduplication across ALL providers)
        
        Args:
            file_hash: SHA-256 hash
            
        Returns:
            ContentMetadata if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT document_id FROM content_metadata WHERE file_hash = ? LIMIT 1
            ''', (file_hash,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self.get_metadata(row[0])
            return None
        except Exception as e:
            logger.error(f"Error finding by hash: {e}")
            return None
    
    def insert(
        self,
        document_id: str,
        type: str,
        file_hash: str,
        original_file: str,
        file_format: str,
        file_size: int,
        processed_data: Dict[str, Any],
        metadata: Dict[str, Any],
        app_data: Dict[str, Any],
        created_by: str,
        provider_id: str = "local-provider",
        storage_location: str = "",
        signature: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ContentMetadata:
        """
        Insert new content metadata with unified schema
        
        Args:
            document_id: Unique document identifier
            type: Document type (ocr, transcription, etc)
            file_hash: SHA-256 hash
            original_file: Original file name/path
            file_format: File format (pdf, txt, json)
            file_size: Size in bytes
            processed_data: The actual content/extracted data
            metadata: Document metadata
            app_data: Application-specific data
            created_by: Creator identifier
            provider_id: Storage provider ID
            storage_location: Location within provider
            signature: Digital signature
            tags: Content tags
            
        Returns:
            ContentMetadata object
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO content_metadata (
                    document_id, type, file_hash, original_file, file_format,
                    file_size, processed_data, metadata, app_data,
                    created_by, created_at, updated_at, version,
                    provider_id, storage_location, signature, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                document_id,
                type,
                file_hash,
                original_file,
                file_format,
                file_size,
                json.dumps(processed_data) if isinstance(processed_data, dict) else processed_data,
                json.dumps(metadata),
                json.dumps(app_data) if app_data else None,
                created_by,
                timestamp,
                timestamp,
                1,
                provider_id,
                storage_location,
                signature,
                json.dumps(tags) if tags else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Document inserted: {document_id} (type={type}, created_by={created_by}, hash={file_hash[:16]}...)")
            
            return ContentMetadata(
                document_id=document_id,
                type=type,
                file_hash=file_hash,
                original_file=original_file,
                file_format=file_format,
                file_size=file_size,
                processed_data=processed_data,
                metadata=metadata,
                app_data=app_data,
                created_by=created_by,
                created_at=timestamp,
                updated_at=timestamp,
                version=1,
                provider_id=provider_id,
                storage_location=storage_location,
                signature=signature,
                tags=tags
            )
        except Exception as e:
            logger.error(f"Error inserting metadata: {e}")
            raise
    
    def get_metadata(self, document_id: str) -> Optional[ContentMetadata]:
        """
        Get metadata for document
        
        Args:
            document_id: Document identifier
            
        Returns:
            ContentMetadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT document_id, type, file_hash, original_file, file_format,
                       file_size, processed_data, metadata, app_data,
                       created_by, created_at, updated_at, version,
                       provider_id, storage_location, signature, tags, deleted_at
                FROM content_metadata WHERE document_id = ?
            ''', (document_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return ContentMetadata(
                document_id=row[0],
                type=row[1],
                file_hash=row[2],
                original_file=row[3],
                file_format=row[4],
                file_size=row[5],
                processed_data=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                metadata=json.loads(row[7]),
                app_data=json.loads(row[8]) if row[8] else {},
                created_by=row[9],
                created_at=row[10],
                updated_at=row[11],
                version=row[12],
                provider_id=row[13],
                storage_location=row[14],
                signature=row[15],
                tags=json.loads(row[16]) if row[16] else None,
                deleted_at=row[17]
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {document_id}: {e}")
            return None
    
    def list_all(
        self,
        type: Optional[str] = None,
        created_by: Optional[str] = None,
        provider_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContentMetadata]:
        """
        List documents with filters
        
        Args:
            type: Filter by document type
            created_by: Filter by creator
            provider_id: Filter by provider
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of ContentMetadata
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query
            query = '''SELECT document_id, type, file_hash, original_file, file_format,
                       file_size, processed_data, metadata, app_data,
                       created_by, created_at, updated_at, version,
                       provider_id, storage_location, signature, tags, deleted_at
                       FROM content_metadata WHERE deleted_at IS NULL'''
            params = []
            
            if type:
                query += ' AND type = ?'
                params.append(type)
            
            if created_by:
                query += ' AND created_by = ?'
                params.append(created_by)
            
            if provider_id:
                query += ' AND provider_id = ?'
                params.append(provider_id)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append(ContentMetadata(
                    document_id=row[0],
                    type=row[1],
                    file_hash=row[2],
                    original_file=row[3],
                    file_format=row[4],
                    file_size=row[5],
                    processed_data=json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    metadata=json.loads(row[7]),
                    app_data=json.loads(row[8]) if row[8] else {},
                    created_by=row[9],
                    created_at=row[10],
                    updated_at=row[11],
                    version=row[12],
                    provider_id=row[13],
                    storage_location=row[14],
                    signature=row[15],
                    tags=json.loads(row[16]) if row[16] else None,
                    deleted_at=row[17]
                ))
            
            logger.debug(f"Listed {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error listing metadata: {e}")
            return []
    
    def delete(self, content_id: str) -> bool:
        """
        Delete content metadata
        
        Args:
            content_id: Content identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete versions first (foreign key constraint)
            cursor.execute('DELETE FROM content_versions WHERE content_id = ?', (content_id,))
            
            # Delete metadata
            cursor.execute('DELETE FROM content_metadata WHERE content_id = ?', (content_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if deleted:
                logger.info(f"Metadata deleted: {content_id}")
            
            return deleted
        except Exception as e:
            logger.error(f"Error deleting metadata: {e}")
            raise
    
    def delete_all(self) -> int:
        """
        Delete all metadata (for testing/reset)
        
        Returns:
            Number of records deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM content_versions')
            cursor.execute('DELETE FROM content_metadata')
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"All metadata deleted: {deleted} records")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting all metadata: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total count and size
            cursor.execute('SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM content_metadata')
            total_count, total_size = cursor.fetchone()
            
            # By content type
            cursor.execute('''
                SELECT content_type, COUNT(*), COALESCE(SUM(file_size), 0)
                FROM content_metadata
                GROUP BY content_type
            ''')
            by_type = {row[0]: {'count': row[1], 'size': row[2]} for row in cursor.fetchall()}
            
            # By provider
            cursor.execute('''
                SELECT provider_id, COUNT(*), COALESCE(SUM(file_size), 0)
                FROM content_metadata
                GROUP BY provider_id
            ''')
            by_provider = {row[0]: {'count': row[1], 'size': row[2]} for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'by_provider': by_provider,
                'db_path': self.db_path
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}

    # Unified Extractions methods
    
    def store_extraction(self, source_type: str, source_id: str, data: str | dict, 
                        data_type: str, metadata: Dict[str, Any], provider: str,
                        confidence: float = None, created_by: str = None) -> str:
        """
        Store a generic extraction result to unified table
        
        Args:
            source_type: Type of extraction (ocr, transcription, translation, custom, etc)
            source_id: ID of the source file/input
            data: The actual extracted content
            data_type: Type of data (text, json, binary)
            metadata: Additional metadata about the extraction
            provider: Which model/service performed extraction
            confidence: Confidence score if applicable
            created_by: Which UI/service stored this
        
        Returns:
            extraction_id
        """
        try:
            extraction_id = f"ext-{uuid.uuid4()}"
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Convert data to string if dict
            data_str = json.dumps(data) if isinstance(data, dict) else str(data)
            metadata_str = json.dumps(metadata) if isinstance(metadata, dict) else str(metadata)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO unified_extractions 
                (id, source_type, source_id, data, data_type, metadata, provider, confidence, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (extraction_id, source_type, source_id, data_str, data_type, metadata_str, provider, confidence, created_by, timestamp))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Extraction stored: {extraction_id} (type={source_type}, provider={provider})")
            return extraction_id
        except Exception as e:
            logger.error(f"Error storing extraction: {e}")
            raise
    
    def get_extraction(self, extraction_id: str) -> Dict[str, Any]:
        """Get a single extraction by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, source_type, source_id, data, data_type, metadata, provider, confidence, created_by, created_at
                FROM unified_extractions
                WHERE id = ?
            ''', (extraction_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'source_type': row[1],
                'source_id': row[2],
                'data': json.loads(row[3]) if row[3].startswith('{') or row[3].startswith('[') else row[3],
                'data_type': row[4],
                'metadata': json.loads(row[5]) if row[5] else {},
                'provider': row[6],
                'confidence': row[7],
                'created_by': row[8],
                'created_at': row[9]
            }
        except Exception as e:
            logger.error(f"Error getting extraction: {e}")
            raise
    
    def list_extractions(self, source_type: str = None, source_id: str = None, 
                        limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List extractions with optional filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT id, source_type, source_id, data, data_type, metadata, provider, confidence, created_by, created_at FROM unified_extractions WHERE 1=1'
            params = []
            
            if source_type:
                query += ' AND source_type = ?'
                params.append(source_type)
            
            if source_id:
                query += ' AND source_id = ?'
                params.append(source_id)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'source_type': row[1],
                    'source_id': row[2],
                    'data': json.loads(row[3]) if row[3] and (row[3].startswith('{') or row[3].startswith('[')) else row[3],
                    'data_type': row[4],
                    'metadata': json.loads(row[5]) if row[5] else {},
                    'provider': row[6],
                    'confidence': row[7],
                    'created_by': row[8],
                    'created_at': row[9]
                })
            
            return results
        except Exception as e:
            logger.error(f"Error listing extractions: {e}")
            raise

