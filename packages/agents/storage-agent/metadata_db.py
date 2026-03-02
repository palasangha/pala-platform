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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ContentMetadata:
    """Metadata for stored content"""
    content_id: str
    content_type: str
    file_hash: str
    file_size: int
    provider_id: str  # Which provider stores this
    storage_location: str  # Location within that provider
    metadata: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
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
        
        # Content metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_metadata (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                provider_id TEXT NOT NULL,
                storage_location TEXT NOT NULL,
                metadata TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                signature TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Deduplication index on hash (CRITICAL for cross-provider dedup)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_hash ON content_metadata(file_hash)
        ''')
        
        # Content type index for filtering
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_type ON content_metadata(content_type)
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
                SELECT content_id FROM content_metadata WHERE file_hash = ? LIMIT 1
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
        content_id: str,
        content_type: str,
        file_hash: str,
        file_size: int,
        provider_id: str,
        storage_location: str,
        metadata: Dict[str, Any],
        signature: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ContentMetadata:
        """
        Insert new content metadata
        
        Args:
            content_id: Unique content identifier
            content_type: Type of content
            file_hash: SHA-256 hash
            file_size: Size in bytes
            provider_id: Storage provider ID
            storage_location: Location within provider
            metadata: Additional metadata
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
                    content_id, content_type, file_hash, file_size,
                    provider_id, storage_location, metadata,
                    version, signature, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                content_type,
                file_hash,
                file_size,
                provider_id,
                storage_location,
                json.dumps(metadata),
                1,
                signature,
                json.dumps(tags) if tags else None,
                timestamp,
                timestamp
            ))
            
            # Add to version history
            cursor.execute('''
                INSERT INTO content_versions (
                    content_id, version, metadata, updated_at
                ) VALUES (?, ?, ?, ?)
            ''', (
                content_id,
                1,
                json.dumps(metadata),
                timestamp
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Metadata inserted: {content_id} (provider={provider_id}, hash={file_hash[:16]}...)")
            
            return ContentMetadata(
                content_id=content_id,
                content_type=content_type,
                file_hash=file_hash,
                file_size=file_size,
                provider_id=provider_id,
                storage_location=storage_location,
                metadata=metadata,
                version=1,
                created_at=timestamp,
                updated_at=timestamp,
                signature=signature,
                tags=tags
            )
        except Exception as e:
            logger.error(f"Error inserting metadata: {e}")
            raise
    
    def get_metadata(self, content_id: str) -> Optional[ContentMetadata]:
        """
        Get metadata for content
        
        Args:
            content_id: Content identifier
            
        Returns:
            ContentMetadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT content_id, content_type, file_hash, file_size,
                       provider_id, storage_location, metadata, version,
                       signature, tags, created_at, updated_at
                FROM content_metadata WHERE content_id = ?
            ''', (content_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return ContentMetadata(
                content_id=row[0],
                content_type=row[1],
                file_hash=row[2],
                file_size=row[3],
                provider_id=row[4],
                storage_location=row[5],
                metadata=json.loads(row[6]),
                version=row[7],
                signature=row[8],
                tags=json.loads(row[9]) if row[9] else None,
                created_at=row[10],
                updated_at=row[11]
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {content_id}: {e}")
            return None
    
    def list_all(
        self,
        content_type: Optional[str] = None,
        provider_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContentMetadata]:
        """
        List content metadata with filters
        
        Args:
            content_type: Filter by content type
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
            query = 'SELECT content_id, content_type, file_hash, file_size, provider_id, storage_location, metadata, version, signature, tags, created_at, updated_at FROM content_metadata WHERE 1=1'
            params = []
            
            if content_type:
                query += ' AND content_type = ?'
                params.append(content_type)
            
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
                    content_id=row[0],
                    content_type=row[1],
                    file_hash=row[2],
                    file_size=row[3],
                    provider_id=row[4],
                    storage_location=row[5],
                    metadata=json.loads(row[6]),
                    version=row[7],
                    signature=row[8],
                    tags=json.loads(row[9]) if row[9] else None,
                    created_at=row[10],
                    updated_at=row[11]
                ))
            
            logger.debug(f"Listed {len(results)} metadata records")
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
