"""
SQLite Storage Backend

Stores content directly in SQLite database.
Useful for:
- Testing without file I/O
- Single-file deployments
- Embedded systems
- Development environments

Schema:
storage_content:
  - content_id TEXT PRIMARY KEY
  - content_type TEXT
  - content BLOB
  - file_hash TEXT
  - file_size INTEGER
  - metadata TEXT (JSON)
  - created_at TEXT
  - updated_at TEXT
"""

import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .base import StorageBackend

logger = logging.getLogger(__name__)


class SQLiteStorageBackend(StorageBackend):
    """SQLite database storage backend"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize SQLite storage backend
        
        Args:
            name: Backend name (e.g., 'sqlite-primary')
            config: Configuration dict with:
                - db_path: Path to SQLite database (default: ./storage.db)
                - enable_wal: Use WAL mode for better concurrency (default: True)
                - timeout: Connection timeout in seconds (default: 5.0)
                - journal_mode: Journal mode (default: WAL)
        """
        super().__init__(name, config)
        
        self.db_path = config.get('db_path', './storage.db')
        self.enable_wal = config.get('enable_wal', True)
        self.timeout = config.get('timeout', 5.0)
        self.journal_mode = config.get('journal_mode', 'WAL')
        
        # Create directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info(f"SQLiteStorageBackend initialized: {self.db_path}")
    
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
        """Initialize SQLite database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storage_content (
                content_id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                content BLOB NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create index on file_hash for deduplication
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_hash ON storage_content(file_hash)
        ''')
        
        # Create index on content_type for queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_type ON storage_content(content_type)
        ''')
        
        # Create index on created_at for sorting
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON storage_content(created_at)
        ''')
        
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
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
                INSERT INTO storage_content (
                    content_id, content_type, content, file_hash,
                    file_size, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                content_type,
                content,
                metadata.get('file_hash', ''),
                len(content),
                json.dumps(metadata.get('metadata', {})),
                created_at,
                created_at
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
                'SELECT content FROM storage_content WHERE content_id = ?',
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
                'DELETE FROM storage_content WHERE content_id = ?',
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
                'SELECT 1 FROM storage_content WHERE content_id = ? LIMIT 1',
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
                'SELECT file_size FROM storage_content WHERE content_id = ?',
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
                    'SELECT content_id FROM storage_content WHERE content_id LIKE ? ORDER BY created_at DESC',
                    (f'{prefix}%',)
                )
            else:
                cursor.execute(
                    'SELECT content_id FROM storage_content ORDER BY created_at DESC'
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
        Check SQLite backend health
        
        Returns:
            True if backend is healthy
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Simple query to check connection
            cursor.execute('SELECT COUNT(*) FROM storage_content')
            cursor.fetchone()
            
            conn.close()
            logger.debug(f"Health check passed for {self.name}")
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get SQLite backend statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total count and size
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(file_size), 0)
                FROM storage_content
            ''')
            total_count, total_size = cursor.fetchone()
            
            # By content type
            cursor.execute('''
                SELECT content_type, COUNT(*), COALESCE(SUM(file_size), 0)
                FROM storage_content
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
                'backend_type': self.backend_type,
                'backend_name': self.name,
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'db_file_size': db_file_size,
                'db_path': self.db_path,
                'journal_mode': self.journal_mode
            }
            
            logger.debug(f"Stats for {self.name}: {total_count} items, {total_size} bytes")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def vacuum(self) -> bool:
        """
        Optimize database (run VACUUM)
        
        Reclaims space from deleted content.
        
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            conn.execute('VACUUM')
            conn.close()
            logger.info(f"Database vacuumed: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            return False
    
    async def compact(self) -> Dict[str, Any]:
        """
        Compact database (removes deleted content permanently)
        
        Returns:
            Statistics before and after compaction
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get size before
            cursor.execute('SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()')
            size_before = cursor.fetchone()[0]
            
            # Vacuum
            conn.execute('VACUUM')
            
            # Get size after
            cursor.execute('SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()')
            size_after = cursor.fetchone()[0]
            
            conn.close()
            
            result = {
                'size_before': size_before,
                'size_after': size_after,
                'space_freed': size_before - size_after
            }
            
            logger.info(f"Database compacted. Freed: {result['space_freed']} bytes")
            return result
        except Exception as e:
            logger.error(f"Error compacting database: {e}")
            return {'error': str(e)}
    
    def get_db_info(self) -> Dict[str, Any]:
        """
        Get detailed database information
        
        Returns:
            Database statistics and info
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Page info
            cursor.execute('PRAGMA page_count')
            page_count = cursor.fetchone()[0]
            
            cursor.execute('PRAGMA page_size')
            page_size = cursor.fetchone()[0]
            
            # Journal mode
            cursor.execute('PRAGMA journal_mode')
            journal_mode = cursor.fetchone()[0]
            
            # Synchronous mode
            cursor.execute('PRAGMA synchronous')
            sync_mode = cursor.fetchone()[0]
            
            # Cache size
            cursor.execute('PRAGMA cache_size')
            cache_size = cursor.fetchone()[0]
            
            # Foreign keys
            cursor.execute('PRAGMA foreign_keys')
            foreign_keys = cursor.fetchone()[0]
            
            conn.close()
            
            db_file_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            return {
                'db_path': self.db_path,
                'file_size': db_file_size,
                'page_count': page_count,
                'page_size': page_size,
                'total_pages_size': page_count * page_size,
                'journal_mode': journal_mode,
                'sync_mode': sync_mode,
                'cache_size': cache_size,
                'foreign_keys_enabled': bool(foreign_keys)
            }
        except Exception as e:
            logger.error(f"Error getting DB info: {e}")
            return {'error': str(e)}
