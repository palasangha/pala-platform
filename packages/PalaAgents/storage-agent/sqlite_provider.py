"""
SQLite Storage Provider Implementation

Implements the StorageProvider interface using SQLite as metadata storage
and configurable file backend (local filesystem or S3).

This is the default provider for local development and single-machine deployments.
"""

import sqlite3
import json
import uuid
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from storage_provider import StorageProvider, Document, Extraction

logger = logging.getLogger(__name__)


class SQLiteProvider(StorageProvider):
    """SQLite-based storage provider"""

    def __init__(self, db_path: str = "./storage_metadata.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with new schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Documents table - Main content table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                original_file TEXT NOT NULL,
                file_format TEXT,
                file_size INTEGER,
                file_hash TEXT,
                
                -- Processed content (stored as JSON)
                processed_data TEXT NOT NULL DEFAULT '{}',
                
                -- Shared metadata (stored as JSON)
                metadata TEXT NOT NULL DEFAULT '{}',
                
                -- App-specific data (stored as JSON)
                app_data TEXT NOT NULL DEFAULT '{}',
                
                -- Provenance
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                -- Versioning
                version INTEGER NOT NULL DEFAULT 1,
                previous_version_id TEXT,
                
                -- Soft delete
                deleted_at TEXT
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_deleted_at ON documents(deleted_at) WHERE deleted_at IS NULL')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash)')

        # Relationships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                from_document_id TEXT NOT NULL,
                to_document_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                relationship_metadata TEXT DEFAULT '{}',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(from_document_id) REFERENCES documents(id),
                FOREIGN KEY(to_document_id) REFERENCES documents(id),
                UNIQUE(from_document_id, to_document_id, relationship_type)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type)')

        # Tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT
            )
        ''')

        # Document tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_tags (
                document_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                confidence REAL,
                created_by TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (document_id, tag_id),
                FOREIGN KEY(document_id) REFERENCES documents(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_tags_document ON document_tags(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag_id)')

        # Signatures table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signatures (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                signature_algorithm TEXT NOT NULL,
                signature_value TEXT NOT NULL,
                public_key TEXT NOT NULL,
                signed_content_hash TEXT NOT NULL,
                signed_fields TEXT NOT NULL,
                certificate_chain TEXT,
                verified BOOLEAN DEFAULT 0,
                verified_at TEXT,
                verified_by TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signatures_document ON signatures(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signatures_verified ON signatures(verified)')

        # Unified extractions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extractions (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                data TEXT NOT NULL,
                data_type TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                provider TEXT,
                confidence REAL,
                created_by TEXT DEFAULT 'api',
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_extractions_source_type ON extractions(source_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_extractions_source_id ON extractions(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_extractions_created_at ON extractions(created_at DESC)')

        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                changes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_document ON audit_log(document_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC)')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content).hexdigest()

    async def store_document(
        self,
        type: str,
        original_file: str,
        file_format: str,
        processed_data: Dict[str, Any],
        metadata: Dict[str, Any],
        app_data: Dict[str, Any],
        created_by: str,
        file_hash: Optional[str] = None,
    ) -> Document:
        """Store a document with deduplication and simulated redundancy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Deduplication: check for existing file_hash
            if file_hash:
                cursor.execute('SELECT id FROM documents WHERE file_hash = ? AND deleted_at IS NULL', (file_hash,))
                existing = cursor.fetchone()
                if existing:
                    conn.close()
                    logger.info(f"Duplicate detected for file_hash {file_hash}, returning existing document.")
                    # Optionally, fetch and return the existing document
                    cursor = sqlite3.connect(self.db_path).cursor()
                    cursor.execute('''
                        SELECT id, type, original_file, file_format, processed_data, metadata, app_data, created_by, created_at, updated_at, version, deleted_at, file_hash
                        FROM documents WHERE id = ?
                    ''', (existing[0],))
                    row = cursor.fetchone()
                    cursor.connection.close()
                    return Document(
                        id=row[0], type=row[1], original_file=row[2], file_format=row[3],
                        processed_data=json.loads(row[4]), metadata=json.loads(row[5]),
                        app_data=json.loads(row[6]), created_by=row[7], created_at=row[8],
                        updated_at=row[9], version=row[10], deleted_at=row[11], file_hash=row[12]
                    )

            doc_id = f"doc-{uuid.uuid4()}"
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute('''
                INSERT INTO documents (
                    id, type, original_file, file_format, processed_data,
                    metadata, app_data, created_by, created_at, updated_at, file_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                type,
                original_file,
                file_format,
                json.dumps(processed_data or {}),
                json.dumps(metadata or {}),
                json.dumps(app_data or {}),
                created_by,
                now,
                now,
                file_hash
            ))

            conn.commit()

            # Simulated redundancy: copy original_file_base64 to a secondary location (e.g., backup folder)
            # This is a simulation; in production, you would write to another storage backend
            original_file_base64 = processed_data.get('original_file_base64')
            if original_file_base64:
                backup_dir = Path('./redundant_backup')
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"{doc_id}.{file_format}.b64"
                with open(backup_path, 'w') as f:
                    f.write(original_file_base64)
                logger.info(f"Redundant copy written to {backup_path}")

            # Log the action
            cursor.execute('''
                INSERT INTO audit_log (id, document_id, action, actor, actor_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (f"audit-{uuid.uuid4()}", doc_id, 'CREATE', created_by, 'app', now))

            conn.commit()
            conn.close()

            return Document(
                id=doc_id,
                type=type,
                original_file=original_file,
                file_format=file_format,
                processed_data=processed_data or {},
                metadata=metadata or {},
                app_data=app_data or {},
                created_by=created_by,
                created_at=now,
                updated_at=now,
                file_hash=file_hash
            )

        except Exception as e:
            conn.close()
            logger.error(f"Error storing document: {e}", exc_info=True)
            raise

    async def retrieve_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, type, original_file, file_format, processed_data, metadata,
                   app_data, created_by, created_at, updated_at, version, deleted_at, file_hash
            FROM documents WHERE id = ? AND deleted_at IS NULL
        ''', (document_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Document(
            id=row[0],
            type=row[1],
            original_file=row[2],
            file_format=row[3],
            processed_data=json.loads(row[4]),
            metadata=json.loads(row[5]),
            app_data=json.loads(row[6]),
            created_by=row[7],
            created_at=row[8],
            updated_at=row[9],
            version=row[10],
            deleted_at=row[11],
            file_hash=row[12]
        )

    async def list_documents(
        self,
        doc_type: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List documents with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT id, type, original_file, file_format, processed_data, metadata, app_data, created_by, created_at, updated_at, version FROM documents WHERE deleted_at IS NULL'
        params = []

        if doc_type:
            query += ' AND type = ?'
            params.append(doc_type)

        if created_by:
            query += ' AND created_by = ?'
            params.append(created_by)

        # Get total count
        count_query = query.replace('SELECT id, type, original_file, file_format, processed_data, metadata, app_data, created_by, created_at, updated_at, version', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Get paginated results
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        documents = []
        for row in rows:
            documents.append(Document(
                id=row[0],
                type=row[1],
                original_file=row[2],
                file_format=row[3],
                processed_data=json.loads(row[4]),
                metadata=json.loads(row[5]),
                app_data=json.loads(row[6]),
                created_by=row[7],
                created_at=row[8],
                updated_at=row[9],
                version=row[10]
            ))

        return {
            'count': len(documents),
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'documents': documents
        }

    async def store_extraction(
        self,
        source_type: str,
        source_id: str,
        data: Any,
        data_type: str,
        metadata: Dict[str, Any],
        provider: str,
        confidence: Optional[float] = None,
        created_by: str = 'api',
    ) -> Extraction:
        """Store an extraction result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            ext_id = f"ext-{uuid.uuid4()}"
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute('''
                INSERT INTO extractions (
                    id, source_type, source_id, data, data_type, metadata,
                    provider, confidence, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ext_id,
                source_type,
                source_id,
                json.dumps(data) if isinstance(data, (dict, list)) else str(data),
                data_type,
                json.dumps(metadata or {}),
                provider,
                confidence,
                created_by,
                now
            ))

            conn.commit()
            conn.close()

            return Extraction(
                id=ext_id,
                source_type=source_type,
                source_id=source_id,
                data=data,
                data_type=data_type,
                metadata=metadata or {},
                provider=provider,
                confidence=confidence,
                created_by=created_by,
                created_at=now
            )

        except Exception as e:
            conn.close()
            logger.error(f"Error storing extraction: {e}", exc_info=True)
            raise

    async def retrieve_extraction(self, extraction_id: str) -> Optional[Extraction]:
        """Retrieve an extraction by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, source_type, source_id, data, data_type, metadata,
                   provider, confidence, created_by, created_at
            FROM extractions WHERE id = ?
        ''', (extraction_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Extraction(
            id=row[0],
            source_type=row[1],
            source_id=row[2],
            data=json.loads(row[3]) if row[3].startswith(('{', '[')) else row[3],
            data_type=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            provider=row[6],
            confidence=row[7],
            created_by=row[8],
            created_at=row[9]
        )

    async def list_extractions(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List extractions with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT id, source_type, source_id, data, data_type, metadata, provider, confidence, created_by, created_at FROM extractions WHERE 1=1'
        params = []

        if source_type:
            query += ' AND source_type = ?'
            params.append(source_type)

        if source_id:
            query += ' AND source_id = ?'
            params.append(source_id)

        # Get total count
        count_query = query.replace('SELECT id, source_type, source_id, data, data_type, metadata, provider, confidence, created_by, created_at', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Get paginated results
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        extractions = []
        for row in rows:
            extractions.append(Extraction(
                id=row[0],
                source_type=row[1],
                source_id=row[2],
                data=json.loads(row[3]) if row[3].startswith(('{', '[')) else row[3],
                data_type=row[4],
                metadata=json.loads(row[5]) if row[5] else {},
                provider=row[6],
                confidence=row[7],
                created_by=row[8],
                created_at=row[9]
            ))

        return {
            'count': len(extractions),
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'extractions': extractions
        }

    async def create_relationship(
        self,
        from_document_id: str,
        to_document_id: str,
        relationship_type: str,
        created_by: str = 'api',
    ) -> Dict[str, Any]:
        """Create a relationship between two documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            rel_id = f"rel-{uuid.uuid4()}"
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute('''
                INSERT INTO relationships (
                    id, from_document_id, to_document_id, relationship_type, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (rel_id, from_document_id, to_document_id, relationship_type, created_by, now))

            conn.commit()
            conn.close()

            return {
                'id': rel_id,
                'from_document_id': from_document_id,
                'to_document_id': to_document_id,
                'relationship_type': relationship_type,
                'created_by': created_by,
                'created_at': now
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error creating relationship: {e}", exc_info=True)
            raise

    async def add_tags(
        self,
        document_id: str,
        tags: Dict[str, str],
        created_by: str = 'api',
    ) -> Dict[str, Any]:
        """Add tags to a document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now(timezone.utc).isoformat()
            tag_ids = []

            for tag_name, category in tags.items():
                # Get or create tag
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                result = cursor.fetchone()

                if result:
                    tag_id = result[0]
                else:
                    tag_id = f"tag-{uuid.uuid4()}"
                    cursor.execute('''
                        INSERT INTO tags (id, name, category, created_at, created_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (tag_id, tag_name, category, now, created_by))

                tag_ids.append(tag_id)

                # Add document-tag relationship
                cursor.execute('''
                    INSERT OR IGNORE INTO document_tags (document_id, tag_id, created_by, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (document_id, tag_id, created_by, now))

            conn.commit()
            conn.close()

            return {
                'document_id': document_id,
                'tags_added': len(tag_ids),
                'created_at': now
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error adding tags: {e}", exc_info=True)
            raise

    async def create_signature(
        self,
        document_id: str,
        signature_algorithm: str,
        signature_value: str,
        public_key: str,
        signed_content_hash: str,
        signed_fields: List[str],
        created_by: str,
    ) -> Dict[str, Any]:
        """Create a digital signature for a document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            sig_id = f"sig-{uuid.uuid4()}"
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute('''
                INSERT INTO signatures (
                    id, document_id, signature_algorithm, signature_value, public_key,
                    signed_content_hash, signed_fields, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sig_id,
                document_id,
                signature_algorithm,
                signature_value,
                public_key,
                signed_content_hash,
                json.dumps(signed_fields),
                created_by,
                now
            ))

            conn.commit()
            conn.close()

            return {
                'id': sig_id,
                'document_id': document_id,
                'signature_algorithm': signature_algorithm,
                'created_by': created_by,
                'created_at': now
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error creating signature: {e}", exc_info=True)
            raise

    async def search_full_text(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Document]:
        """Full-text search across documents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Simple search in processed_data and metadata
        search_query = f"%{query}%"

        cursor.execute('''
            SELECT id, type, original_file, file_format, processed_data, metadata,
                   app_data, created_by, created_at, updated_at, version
            FROM documents
            WHERE (processed_data LIKE ? OR metadata LIKE ?)
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT ?
        ''', (search_query, search_query, limit))

        rows = cursor.fetchall()
        conn.close()

        documents = []
        for row in rows:
            documents.append(Document(
                id=row[0],
                type=row[1],
                original_file=row[2],
                file_format=row[3],
                processed_data=json.loads(row[4]),
                metadata=json.loads(row[5]),
                app_data=json.loads(row[6]),
                created_by=row[7],
                created_at=row[8],
                updated_at=row[9],
                version=row[10]
            ))

        return documents

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count by type
        cursor.execute('''
            SELECT type, COUNT(*) as count
            FROM documents
            WHERE deleted_at IS NULL
            GROUP BY type
        ''')
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Count by app
        cursor.execute('''
            SELECT created_by, COUNT(*) as count
            FROM documents
            WHERE deleted_at IS NULL
            GROUP BY created_by
        ''')
        app_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Total documents
        cursor.execute('SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL')
        total_docs = cursor.fetchone()[0]

        # Total extractions
        cursor.execute('SELECT COUNT(*) FROM extractions')
        total_extractions = cursor.fetchone()[0]

        conn.close()

        return {
            'total_documents': total_docs,
            'total_extractions': total_extractions,
            'documents_by_type': type_counts,
            'documents_by_app': app_counts
        }

    async def delete_all_documents(self) -> int:
        """Delete all documents (for testing/reset)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM documents')
        cursor.execute('DELETE FROM extractions')
        cursor.execute('DELETE FROM relationships')
        cursor.execute('DELETE FROM document_tags')
        cursor.execute('DELETE FROM signatures')
        cursor.execute('DELETE FROM audit_log')

        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()

        logger.info(f"Deleted all documents (count: {deleted_count})")
        return deleted_count

    async def find_by_hash(self, file_hash: str) -> Optional[Document]:
        """Find document by file hash (for deduplication)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, type, original_file, file_format, processed_data, metadata,
                   app_data, created_by, created_at, updated_at, version, deleted_at, file_hash
            FROM documents
            WHERE file_hash = ? AND deleted_at IS NULL
            LIMIT 1
        ''', (file_hash,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Document(
            id=row[0],
            type=row[1],
            original_file=row[2],
            file_format=row[3],
            processed_data=json.loads(row[4]),
            metadata=json.loads(row[5]),
            app_data=json.loads(row[6]),
            created_by=row[7],
            created_at=row[8],
            updated_at=row[9],
            version=row[10],
            deleted_at=row[11],
            file_hash=row[12]
        )
