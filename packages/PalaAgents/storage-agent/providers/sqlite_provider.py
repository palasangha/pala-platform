"""
SQLite Content Storage Provider

Stores content BLOBS directly in SQLite database.
This is for CONTENT storage only - metadata is handled separately by metadata_db.py

Useful for:
- Testing without file I/O
- Single-file deployments
- Embedded systems
- Development environments

Note: This is different from the metadata database.
The metadata DB tracks all content across providers.
This provider stores actual content as BLOBs in SQLite.
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base_provider import BaseStorageProvider

logger = logging.getLogger(__name__)


class SQLiteProvider(BaseStorageProvider):
    """SQLite content storage provider"""
    
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        """
        Initialize SQLite storage provider
        
        Args:
            provider_id: Provider identifier (e.g., 'sqlite-provider')
            config: Configuration dict with:
                - db_path: Path to SQLite database (default: ./content_storage.db)
                - enable_wal: Use WAL mode for better concurrency (default: True)
                - timeout: Connection timeout in seconds (default: 5.0)
                - journal_mode: Journal mode (default: WAL)
        """
        super().__init__(provider_id, config)
        
        self.db_path = config.get('db_path', './content_storage.db')
        self.enable_wal = config.get('enable_wal', True)
        self.timeout = config.get('timeout', 5.0)
        self.journal_mode = config.get('journal_mode', 'WAL')
        
        # Create directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"SQLiteProvider initialized: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimizations"""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.isolation_level = None  # Autocommit mode
        
        if self.enable_wal:
            conn.execute(f'PRAGMA journal_mode = {self.journal_mode}')
        
        # Enable foreign keys
        conn.execute('PRAGMA foreign_keys = ON')
        
        # Performance optimizations
        conn.execute('PRAGMA cache_size = 10000')
        conn.execute('PRAGMA synchronous = NORMAL')
        
        return conn
    
    def _init_db(self):
        """Initialize SQLite database schema for content storage"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_blobs (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                content BLOB NOT NULL,
                file_size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create index on content_type for queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_type ON content_blobs(content_type)
        ''')
        
        # Create index on created_at for sorting
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON content_blobs(created_at)
        ''')
        
        conn.close()
        logger.info(f"Content storage database initialized: {self.db_path}")
    
    async def write(
        self,
        content_id: str,
        content: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Write content to SQLite database
        
        Args:
            content_id: Content identifier
            content: Binary content
            metadata: Content metadata
            
        Returns:
            Storage location (content_id for SQLite)
        """
        try:
            content_type = metadata.get('content_type', 'unknown')
            created_at = metadata.get('created_at', datetime.now(timezone.utc).isoformat())
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO content_blobs (
                    content_id, content_type, content, file_size, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                content_type,
                content,
                len(content),
                created_at,
                datetime.now(timezone.utc).isoformat()
            ))
            
            conn.close()
            logger.info(f"Content {content_id} stored in SQLite ({len(content)} bytes)")
            
            # Return content_id as the location
            return content_id
        except Exception as e:
            logger.error(f"Error writing content {content_id}: {e}")
            raise
    
    async def read(
        self,
        content_id: str,
        location: str
    ) -> bytes:
        """
        Read content from SQLite database
        
        Args:
            content_id: Content identifier
            location: Storage location (content_id for SQLite)
            
        Returns:
            Binary content
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT content FROM content_blobs WHERE content_id = ?',
                (location,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise FileNotFoundError(f"Content not found: {location}")
            
            content = row[0]
            logger.info(f"Content {content_id} read from SQLite ({len(content)} bytes)")
            
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id}: {e}")
            raise
    
    async def delete(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Delete content from SQLite database
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            True if deleted, False if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM content_blobs WHERE content_id = ?',
                (location,)
            )
            
            deleted = cursor.rowcount > 0
            conn.close()
            
            if deleted:
                logger.info(f"Content {content_id} deleted from SQLite")
            
            return deleted
        except Exception as e:
            logger.error(f"Error deleting content {content_id}: {e}")
            raise
    
    async def exists(
        self,
        content_id: str,
        location: str
    ) -> bool:
        """
        Check if content exists in SQLite
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            True if exists
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT 1 FROM content_blobs WHERE content_id = ? LIMIT 1',
                (location,)
            )
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            return exists
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return False
    
    async def get_size(
        self,
        content_id: str,
        location: str
    ) -> int:
        """
        Get content size from SQLite
        
        Args:
            content_id: Content identifier
            location: Storage location
            
        Returns:
            Size in bytes
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT file_size FROM content_blobs WHERE content_id = ?',
                (location,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting size: {e}")
            return 0
    
    async def list_content(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all content in SQLite
        
        Args:
            prefix: Optional prefix filter for content_id
            
        Returns:
            List of content IDs
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if prefix:
                cursor.execute(
                    'SELECT content_id FROM content_blobs WHERE content_id LIKE ? ORDER BY created_at DESC',
                    (f'{prefix}%',)
                )
            else:
                cursor.execute(
                    'SELECT content_id FROM content_blobs ORDER BY created_at DESC'
                )
            
            content_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"Listed {len(content_ids)} content items from SQLite")
            return content_ids
        except Exception as e:
            logger.error(f"Error listing content: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check SQLite provider health
        
        Returns:
            True if provider is healthy
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Simple query to check connection
            cursor.execute('SELECT COUNT(*) FROM content_blobs')
            cursor.fetchone()
            
            conn.close()
            logger.debug(f"Health check passed for {self.provider_id}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get SQLite provider statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total count and size
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(file_size), 0)
                FROM content_blobs
            ''')
            total_count, total_size = cursor.fetchone()
            
            # By content type
            cursor.execute('''
                SELECT content_type, COUNT(*), COALESCE(SUM(file_size), 0)
                FROM content_blobs
                GROUP BY content_type
            ''')
            by_type = {
                row[0]: {'count': row[1], 'size': row[2]}
                for row in cursor.fetchall()
            }
            
            # Database file size
            db_file_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            conn.close()
            
            stats = {
                'provider_type': self.provider_type,
                'provider_id': self.provider_id,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'db_file_size': db_file_size,
                'db_path': self.db_path,
                'journal_mode': self.journal_mode
            }
            
            logger.debug(f"Stats for {self.provider_id}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def _cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec_a: First vector
            vec_b: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        try:
            if not vec_a or not vec_b or len(vec_a) != len(vec_b):
                return 0.0
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
            
            # Calculate magnitudes
            mag_a = sum(a * a for a in vec_a) ** 0.5
            mag_b = sum(b * b for b in vec_b) ** 0.5
            
            if mag_a == 0 or mag_b == 0:
                return 0.0
            
            return dot_product / (mag_a * mag_b)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
