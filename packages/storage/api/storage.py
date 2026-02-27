"""
Pala Platform Storage API

Unified interface for all storage operations.
Supports multiple backends: local filesystem, S3, GCS, PostgreSQL metadata.

Architecture:
- Storage API provides unified interface
- Backends handle specific storage implementations
- Metadata stored in PostgreSQL
- Content stored in object storage (S3/local)
"""

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class StoredContent:
    """Represents stored content metadata"""
    content_id: str
    content_type: str  # document, audio, video, etc.
    file_hash: str
    file_size: int
    storage_path: str
    metadata: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    signature: Optional[str] = None


class StorageAPI:
    """
    Unified storage API for Pala Platform
    
    Features:
    - Content deduplication via hash
    - Version control
    - Metadata storage in SQLite/PostgreSQL
    - Content storage in local/S3/GCS
    """
    
    def __init__(
        self,
        db_path: str = "./pala_storage.db",
        content_dir: str = "./content"
    ):
        """
        Initialize storage API
        
        Args:
            db_path: Path to SQLite database for metadata
            content_dir: Directory for content storage
        """
        self.db_path = db_path
        self.content_dir = Path(content_dir)
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"Storage API initialized - DB: {db_path}, Content: {content_dir}")
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                storage_path TEXT NOT NULL,
                metadata TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                signature TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create index on file_hash for deduplication
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_hash ON content(file_hash)
        ''')
        
        # Create index on content_type for queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_type ON content(content_type)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Database schema initialized")
    
    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _generate_content_id(self) -> str:
        """Generate unique content ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_suffix = hashlib.sha256(os.urandom(32)).hexdigest()[:8]
        return f"content-{timestamp}-{random_suffix}"
    
    def store_content(
        self,
        content: bytes,
        content_type: str,
        metadata: Dict[str, Any],
        signature: Optional[str] = None
    ) -> StoredContent:
        """
        Store content with metadata
        
        Args:
            content: Binary content to store
            content_type: Type of content (document, audio, video, etc.)
            metadata: Associated metadata
            signature: Digital signature (optional)
        
        Returns:
            StoredContent object with storage details
        """
        # Calculate hash for deduplication
        file_hash = self._calculate_hash(content)
        file_size = len(content)
        
        # Check if content already exists
        existing = self.find_by_hash(file_hash)
        if existing:
            logger.info(f"Content already exists with hash {file_hash}, returning existing")
            return existing
        
        # Generate content ID
        content_id = self._generate_content_id()
        
        # Determine storage path (organize by date and type)
        date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        storage_subdir = self.content_dir / content_type / date_path
        storage_subdir.mkdir(parents=True, exist_ok=True)
        
        storage_filename = f"{content_id}.bin"
        storage_path = storage_subdir / storage_filename
        
        # Write content to filesystem
        storage_path.write_bytes(content)
        
        # Store metadata in database
        now = datetime.now(timezone.utc).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO content (
                content_id, content_type, file_hash, file_size,
                storage_path, metadata, version, signature,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            content_id,
            content_type,
            file_hash,
            file_size,
            str(storage_path.relative_to(self.content_dir)),
            json.dumps(metadata),
            1,
            signature,
            now,
            now
        ))
        
        conn.commit()
        conn.close()
        
        stored = StoredContent(
            content_id=content_id,
            content_type=content_type,
            file_hash=file_hash,
            file_size=file_size,
            storage_path=str(storage_path),
            metadata=metadata,
            version=1,
            created_at=now,
            updated_at=now,
            signature=signature
        )
        
        logger.info(f"Stored content {content_id} ({file_size} bytes) at {storage_path}")
        
        return stored
    
    def get_content(self, content_id: str) -> Optional[StoredContent]:
        """
        Retrieve content metadata by ID
        
        Args:
            content_id: Content identifier
        
        Returns:
            StoredContent object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content_id, content_type, file_hash, file_size,
                   storage_path, metadata, version, signature,
                   created_at, updated_at
            FROM content
            WHERE content_id = ?
        ''', (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return StoredContent(
            content_id=row[0],
            content_type=row[1],
            file_hash=row[2],
            file_size=row[3],
            storage_path=str(self.content_dir / row[4]),
            metadata=json.loads(row[5]),
            version=row[6],
            signature=row[7],
            created_at=row[8],
            updated_at=row[9]
        )
    
    def read_content(self, content_id: str) -> Optional[bytes]:
        """
        Read content data by ID
        
        Args:
            content_id: Content identifier
        
        Returns:
            Binary content or None if not found
        """
        stored = self.get_content(content_id)
        if not stored:
            return None
        
        return Path(stored.storage_path).read_bytes()
    
    def find_by_hash(self, file_hash: str) -> Optional[StoredContent]:
        """
        Find content by file hash (for deduplication)
        
        Args:
            file_hash: SHA-256 hash of content
        
        Returns:
            StoredContent object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content_id, content_type, file_hash, file_size,
                   storage_path, metadata, version, signature,
                   created_at, updated_at
            FROM content
            WHERE file_hash = ?
            LIMIT 1
        ''', (file_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return StoredContent(
            content_id=row[0],
            content_type=row[1],
            file_hash=row[2],
            file_size=row[3],
            storage_path=str(self.content_dir / row[4]),
            metadata=json.loads(row[5]),
            version=row[6],
            signature=row[7],
            created_at=row[8],
            updated_at=row[9]
        )
    
    def list_content(
        self,
        content_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredContent]:
        """
        List stored content
        
        Args:
            content_type: Filter by content type (optional)
            limit: Maximum number of results
            offset: Pagination offset
        
        Returns:
            List of StoredContent objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if content_type:
            cursor.execute('''
                SELECT content_id, content_type, file_hash, file_size,
                       storage_path, metadata, version, signature,
                       created_at, updated_at
                FROM content
                WHERE content_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (content_type, limit, offset))
        else:
            cursor.execute('''
                SELECT content_id, content_type, file_hash, file_size,
                       storage_path, metadata, version, signature,
                       created_at, updated_at
                FROM content
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append(StoredContent(
                content_id=row[0],
                content_type=row[1],
                file_hash=row[2],
                file_size=row[3],
                storage_path=str(self.content_dir / row[4]),
                metadata=json.loads(row[5]),
                version=row[6],
                signature=row[7],
                created_at=row[8],
                updated_at=row[9]
            ))
        
        return results
    
    def update_metadata(
        self,
        content_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[StoredContent]:
        """
        Update content metadata (creates new version)
        
        Args:
            content_id: Content identifier
            metadata: New metadata
        
        Returns:
            Updated StoredContent object or None if not found
        """
        existing = self.get_content(content_id)
        if not existing:
            return None
        
        now = datetime.now(timezone.utc).isoformat()
        new_version = existing.version + 1
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE content
            SET metadata = ?, version = ?, updated_at = ?
            WHERE content_id = ?
        ''', (json.dumps(metadata), new_version, now, content_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated metadata for {content_id}, version {new_version}")
        
        return self.get_content(content_id)
    
    def delete_content(self, content_id: str) -> bool:
        """
        Delete content and metadata
        
        Args:
            content_id: Content identifier
        
        Returns:
            True if deleted, False if not found
        """
        stored = self.get_content(content_id)
        if not stored:
            return False
        
        # Delete file
        try:
            Path(stored.storage_path).unlink()
        except FileNotFoundError:
            logger.warning(f"File not found: {stored.storage_path}")
        
        # Delete from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM content WHERE content_id = ?', (content_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted content {content_id}")
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute('SELECT COUNT(*) FROM content')
        total_count = cursor.fetchone()[0]
        
        # Total size
        cursor.execute('SELECT SUM(file_size) FROM content')
        total_size = cursor.fetchone()[0] or 0
        
        # By content type
        cursor.execute('''
            SELECT content_type, COUNT(*), SUM(file_size)
            FROM content
            GROUP BY content_type
        ''')
        by_type = {row[0]: {'count': row[1], 'size': row[2]} for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_count': total_count,
            'total_size': total_size,
            'by_type': by_type
        }
