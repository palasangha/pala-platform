"""
Pala Platform Storage API - Unified Interface

This is the main API for all storage operations.
It abstracts away backend complexity and provides a single interface
for clients to store and retrieve content.

Architecture:
- StorageAPI: Unified interface
- StorageBackendManager: Manages multiple backends
- Individual Backends: Specific implementations (local, S3, GCS, Azure)
- Metadata DB: SQLite/PostgreSQL for metadata and versioning

Features:
- Multiple backend support (local, S3, GCS, Azure)
- Content deduplication via SHA-256
- Version control for metadata
- Automatic backend selection
- Failover support (planned)
- Comprehensive statistics
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import asyncio
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backends import (
    StorageBackendManager,
    StorageBackendFactory,
    StorageMetadata,
    StorageStats
)

logger = logging.getLogger(__name__)


@dataclass
class StoredContent:
    """Represents stored content with all metadata"""
    content_id: str
    content_type: str
    file_hash: str
    file_size: int
    backend_name: str
    backend_location: str
    metadata: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    signature: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class StorageAPI:
    """
    Unified Storage API for Pala Platform
    
    Provides a single interface for all storage operations regardless
    of backend (local, S3, GCS, Azure).
    
    Features:
    - Content deduplication via hash
    - Version control
    - Multi-backend support
    - Automatic backend selection
    - Comprehensive statistics
    
    Usage:
        storage = StorageAPI(
            db_path="./pala_storage.db",
            backends_config={
                'local': {
                    'enabled': True,
                    'default': True,
                    'config': {'base_path': './content'}
                },
                's3': {
                    'enabled': True,
                    'default': False,
                    'config': {
                        'bucket_name': 'pala-content',
                        'aws_access_key_id': '...'
                    }
                }
            }
        )
        
        # Store content
        stored = storage.store_content(
            content=b'...',
            content_type='document',
            metadata={'source': 'scan.jpg'}
        )
        
        # Retrieve content
        content = storage.read_content(stored.content_id)
        
        # Get statistics
        stats = storage.get_stats()
    """
    
    def __init__(
        self,
        db_path: str = "./pala_storage.db",
        backends_config: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialize Storage API
        
        Args:
            db_path: Path to SQLite database for metadata
            backends_config: Backend configuration dict
                {
                    'local': {
                        'enabled': True,
                        'default': True,
                        'config': {...}
                    },
                    's3': {
                        'enabled': True,
                        'default': False,
                        'config': {...}
                    }
                }
        """
        self.db_path = db_path
        self.backend_manager = StorageBackendManager()
        
        # Initialize backends
        if backends_config is None:
            backends_config = {
                'local': {
                    'enabled': True,
                    'default': True,
                    'config': {'base_path': './content'}
                }
            }
        
        self._init_backends(backends_config)
        
        # Initialize metadata database
        self._init_db()
        
        logger.info(f"Storage API initialized - DB: {db_path}")
    
    def _init_backends(self, backends_config: Dict[str, Dict[str, Any]]):
        """Initialize and register backends"""
        for backend_type, config in backends_config.items():
            if not config.get('enabled', True):
                logger.info(f"Backend {backend_type} is disabled")
                continue
            
            try:
                backend = StorageBackendFactory.create(
                    backend_type=backend_type,
                    name=f"{backend_type}-{config.get('name', 'primary')}",
                    config=config.get('config', {})
                )
                
                is_default = config.get('default', False)
                self.backend_manager.register_backend(backend, default=is_default)
                logger.info(f"Backend {backend_type} registered (default={is_default})")
            except Exception as e:
                logger.error(f"Failed to initialize backend {backend_type}: {e}")
    
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
                backend_name TEXT NOT NULL,
                backend_location TEXT NOT NULL,
                metadata TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                signature TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Deduplication index on hash
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_hash ON content_metadata(file_hash)
        ''')
        
        # Content type index
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_type ON content_metadata(content_type)
        ''')
        
        # Backend index for querying by backend
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_backend ON content_metadata(backend_name)
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
        logger.info(f"Database initialized: {self.db_path}")
    
    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()
    
    async def store_content(
        self,
        content: bytes,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        backend_name: Optional[str] = None
    ) -> StoredContent:
        """
        Store content with deduplication
        
        Args:
            content: Binary content to store
            content_type: Type of content (document, audio, video, etc.)
            metadata: Additional metadata
            signature: Digital signature
            tags: Tags for content
            backend_name: Specific backend (uses default if not specified)
            
        Returns:
            StoredContent object with all metadata
        """
        try:
            # Calculate hash for deduplication
            file_hash = self._calculate_hash(content)
            
            # Check for existing content
            existing = self._find_by_hash(file_hash)
            if existing:
                logger.info(f"Content already stored: {existing.content_id}")
                return existing
            
            # Generate content ID
            timestamp = datetime.now(timezone.utc).isoformat()
            content_id = f"content-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{hash(file_hash) % 1000000:06d}"
            
            # Prepare metadata for backend
            backend_metadata = {
                'content_type': content_type,
                'created_at': timestamp,
                'file_hash': file_hash,
                **(metadata or {})
            }
            
            # Write to backend
            backend_name_result, location = await self.backend_manager.write(
                content_id=content_id,
                content=content,
                metadata=backend_metadata,
                backend_name=backend_name
            )
            
            # Store metadata in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO content_metadata (
                    content_id, content_type, file_hash, file_size,
                    backend_name, backend_location, metadata,
                    version, signature, tags, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id,
                content_type,
                file_hash,
                len(content),
                backend_name_result,
                location,
                json.dumps(metadata or {}),
                1,
                signature,
                json.dumps(tags or {}),
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
                json.dumps(metadata or {}),
                timestamp
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Content stored: {content_id} ({len(content)} bytes, {file_hash[:16]}...)")
            
            return StoredContent(
                content_id=content_id,
                content_type=content_type,
                file_hash=file_hash,
                file_size=len(content),
                backend_name=backend_name_result,
                backend_location=location,
                metadata=metadata or {},
                version=1,
                created_at=timestamp,
                updated_at=timestamp,
                signature=signature,
                tags=tags
            )
        except Exception as e:
            logger.error(f"Error storing content: {e}")
            raise
    
    async def read_content(self, content_id: str) -> bytes:
        """
        Read content from storage
        
        Args:
            content_id: Content identifier
            
        Returns:
            Binary content
        """
        try:
            # Get metadata from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT backend_name, backend_location
                FROM content_metadata WHERE content_id = ?
            ''', (content_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                raise ValueError(f"Content not found: {content_id}")
            
            backend_name, location = row
            
            # Read from backend
            content = await self.backend_manager.read(
                content_id=content_id,
                backend_name=backend_name,
                location=location
            )
            
            logger.info(f"Content read: {content_id} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Error reading content {content_id}: {e}")
            raise
    
    def get_content_metadata(self, content_id: str) -> Optional[StoredContent]:
        """
        Get metadata for content without reading the full content
        
        Args:
            content_id: Content identifier
            
        Returns:
            StoredContent metadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT content_id, content_type, file_hash, file_size,
                       backend_name, backend_location, metadata, version,
                       signature, tags, created_at, updated_at
                FROM content_metadata WHERE content_id = ?
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
                backend_name=row[4],
                backend_location=row[5],
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
    
    def _find_by_hash(self, file_hash: str) -> Optional[StoredContent]:
        """Find content by hash (deduplication)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT content_id FROM content_metadata WHERE file_hash = ? LIMIT 1
            ''', (file_hash,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self.get_content_metadata(row[0])
            return None
        except Exception as e:
            logger.error(f"Error finding by hash: {e}")
            return None
    
    async def delete_content(self, content_id: str) -> bool:
        """
        Delete content from storage
        
        Args:
            content_id: Content identifier
            
        Returns:
            True if deleted
        """
        try:
            # Get metadata
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT backend_name, backend_location FROM content_metadata WHERE content_id = ?
            ''', (content_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return False
            
            backend_name, location = row
            
            # Delete from backend
            await self.backend_manager.delete(
                content_id=content_id,
                backend_name=backend_name,
                location=location
            )
            
            # Delete from database
            cursor.execute('DELETE FROM content_metadata WHERE content_id = ?', (content_id,))
            cursor.execute('DELETE FROM content_versions WHERE content_id = ?', (content_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Content deleted: {content_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting content {content_id}: {e}")
            raise
    
    def list_content(
        self,
        content_type: Optional[str] = None,
        backend_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StoredContent]:
        """
        List content with optional filters
        
        Args:
            content_type: Filter by content type
            backend_name: Filter by backend
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of StoredContent
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM content_metadata WHERE 1=1'
            params = []
            
            if content_type:
                query += ' AND content_type = ?'
                params.append(content_type)
            
            if backend_name:
                query += ' AND backend_name = ?'
                params.append(backend_name)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [
                StoredContent(
                    content_id=row[0],
                    content_type=row[1],
                    file_hash=row[2],
                    file_size=row[3],
                    backend_name=row[4],
                    backend_location=row[5],
                    metadata=json.loads(row[6]),
                    version=row[7],
                    signature=row[8],
                    tags=json.loads(row[9]) if row[9] else None,
                    created_at=row[10],
                    updated_at=row[11]
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error listing content: {e}")
            return []
    
    def update_metadata(
        self,
        content_id: str,
        metadata: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> bool:
        """
        Update metadata for content (creates new version)
        
        Args:
            content_id: Content identifier
            metadata: New metadata
            updated_by: User who updated
            
        Returns:
            True if updated
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current version
            cursor.execute('''
                SELECT version FROM content_metadata WHERE content_id = ?
            ''', (content_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            current_version = row[0]
            new_version = current_version + 1
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Update metadata
            cursor.execute('''
                UPDATE content_metadata
                SET metadata = ?, version = ?, updated_at = ?
                WHERE content_id = ?
            ''', (
                json.dumps(metadata),
                new_version,
                timestamp,
                content_id
            ))
            
            # Add to version history
            cursor.execute('''
                INSERT INTO content_versions (
                    content_id, version, metadata, updated_by, updated_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                content_id,
                new_version,
                json.dumps(metadata),
                updated_by,
                timestamp
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Metadata updated for {content_id}: v{new_version}")
            return True
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics
        
        Returns:
            Statistics across all backends
        """
        try:
            # Database stats
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM content_metadata')
            total_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(file_size) FROM content_metadata')
            total_size = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT content_type, COUNT(*), SUM(file_size)
                FROM content_metadata GROUP BY content_type
            ''')
            by_type = {
                row[0]: {'count': row[1], 'size': row[2]}
                for row in cursor.fetchall()
            }
            
            conn.close()
            
            # Backend stats
            backend_stats = await self.backend_manager.get_backend_stats()
            backend_health = await self.backend_manager.health_check()
            
            return {
                'total_count': total_count,
                'total_size': total_size,
                'by_type': by_type,
                'backends': {
                    name: {
                        'stats': backend_stats.get(name, {}),
                        'healthy': backend_health.get(name, False)
                    }
                    for name in self.backend_manager.list_backends()
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
