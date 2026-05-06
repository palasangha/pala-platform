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
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from storage_provider import StorageProvider, Document, Extraction
from metadata_utils import deep_merge_dict

logger = logging.getLogger(__name__)


def _resolve_storage_db_path(path_value: Optional[str], default_name: str) -> str:
    """Resolve storage DB paths relative to the storage-agent package directory.

    This keeps the SQLite files stable regardless of the current working directory,
    so store and search always read and write the same database files.
    """
    base_dir = Path(__file__).resolve().parent
    candidate = Path(path_value or default_name)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return str(candidate.resolve())


class SQLiteProvider(StorageProvider):
    """SQLite-based storage provider"""

    def __init__(self, db_path: str = "./storage_metadata.db"):
        self.db_path = _resolve_storage_db_path(db_path, "storage_metadata.db")
        
        # Replica config
        self.replica_enabled = os.getenv('SQLITE_ENABLE_REPLICA', 'false').lower() == 'true'
        self.replica_db_path = _resolve_storage_db_path(
            os.getenv('SQLITE_REPLICA_DB_PATH', './storage_metadata_replica.db'),
            'storage_metadata_replica.db',
        )
        
        logger.info(f"[SQLiteProvider] PRIMARY: db_path={self.db_path}")
        if self.replica_enabled:
            logger.info(f"[SQLiteProvider] REPLICA: db_path={self.replica_db_path}")
        
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with new schema"""
        self._init_db_schema(self.db_path)
        if self.replica_enabled:
            self._init_db_schema(self.replica_db_path)
    
    def _init_db_schema(self, db_path: str):
        """Initialize database schema for given path"""
        conn = sqlite3.connect(db_path)
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
                deleted_at TEXT,
                
                -- Replication and S3 information (stored as JSON)
                replication TEXT DEFAULT NULL,
                s3_result TEXT DEFAULT NULL,
                message TEXT DEFAULT NULL
            )
        ''')
        
        # Add migration for new columns if they don't exist
        try:
            cursor.execute('PRAGMA table_info(documents)')
            columns = {col[1] for col in cursor.fetchall()}
            
            if 'replication' not in columns:
                logger.info(f"[SQLITE-MIGRATE] Adding 'replication' column to {db_path}")
                cursor.execute('ALTER TABLE documents ADD COLUMN replication TEXT DEFAULT NULL')
            
            if 's3_result' not in columns:
                logger.info(f"[SQLITE-MIGRATE] Adding 's3_result' column to {db_path}")
                cursor.execute('ALTER TABLE documents ADD COLUMN s3_result TEXT DEFAULT NULL')
            
            if 'message' not in columns:
                logger.info(f"[SQLITE-MIGRATE] Adding 'message' column to {db_path}")
                cursor.execute('ALTER TABLE documents ADD COLUMN message TEXT DEFAULT NULL')
            
            conn.commit()
        except Exception as e:
            logger.warning(f"[SQLITE-MIGRATE] Migration error (may be non-critical): {e}")
            conn.rollback()

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
        file_blob: Optional[bytes] = None,
        file_mime: Optional[str] = None,
        replication: Optional[Dict[str, Any]] = None,
        s3_result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> tuple[Document, bool]:
        """Store a document with file content as BLOB. Returns (Document, duplicate: bool)"""
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
                    logger.debug(f"store_document (DUP): doc.id={existing[0]}, storage_location will be set to row[2], provider_id=sqlite")
                    # Optionally, fetch and return the existing document
                    cursor = sqlite3.connect(self.db_path).cursor()
                    cursor.execute('''
                        SELECT id, type, original_file, file_format, processed_data, metadata, app_data, created_by, created_at, updated_at, version, deleted_at, file_hash, replication, s3_result, message
                        FROM documents WHERE id = ?
                    ''', (existing[0],))
                    row = cursor.fetchone()
                    cursor.connection.close()
                    logger.debug(f"store_document (DUP): row[0]={row[0]}, row[2]={row[2]}")
                    return (
                        Document(
                            id=row[0], type=row[1], original_file=row[2], file_format=row[3],
                            processed_data=json.loads(row[4]), metadata=json.loads(row[5]),
                            app_data=json.loads(row[6]), created_by=row[7], created_at=row[8],
                            updated_at=row[9], version=row[10], deleted_at=row[11], file_hash=row[12],
                            storage_location=row[2], provider_id='sqlite',
                            replication=json.loads(row[13]) if row[13] else None,
                            s3_result=json.loads(row[14]) if row[14] else None,
                            message=row[15],
                            duplicate=True
                        ),
                        True
                    )

            doc_id = f"doc-{uuid.uuid4()}"
            now = datetime.now(timezone.utc).isoformat()

            # Store file as BLOB in a separate table
            if file_blob is not None:
                logger.info(f"[SQLITE] Storing file_blob for doc_id={doc_id}, size={len(file_blob)} bytes, mime={file_mime}")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS document_files (
                        document_id TEXT PRIMARY KEY,
                        file_blob BLOB,
                        file_mime TEXT,
                        created_at TEXT,
                        FOREIGN KEY(document_id) REFERENCES documents(id)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO document_files (document_id, file_blob, file_mime, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (doc_id, file_blob, file_mime or '', now))
                logger.info(f"[SQLITE] File BLOB stored for doc_id={doc_id}")

            cursor.execute('''
                INSERT INTO documents (
                    id, type, original_file, file_format, processed_data,
                    metadata, app_data, created_by, created_at, updated_at, file_hash,
                    replication, s3_result, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                file_hash,
                json.dumps(replication) if replication else None,
                json.dumps(s3_result) if s3_result else None,
                message
            ))

            conn.commit()

            # Replicate to replica database if enabled
            replica_result = None
            if self.replica_enabled:
                try:
                    replica_conn = sqlite3.connect(self.replica_db_path)
                    replica_cursor = replica_conn.cursor()
                    
                    # Store file blob in replica if present
                    if file_blob is not None:
                        replica_cursor.execute('''
                            CREATE TABLE IF NOT EXISTS document_files (
                                document_id TEXT PRIMARY KEY,
                                file_blob BLOB,
                                file_mime TEXT,
                                created_at TEXT,
                                FOREIGN KEY(document_id) REFERENCES documents(id)
                            )
                        ''')
                        replica_cursor.execute('''
                            INSERT INTO document_files (document_id, file_blob, file_mime, created_at)
                            VALUES (?, ?, ?, ?)
                        ''', (doc_id, file_blob, file_mime or '', now))
                        logger.info(f"[SQLITE-REPLICA] File BLOB replicated for doc_id={doc_id}")
                    
                    # Replicate document metadata
                    replica_cursor.execute('''
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
                    
                    # Replicate audit log
                    replica_cursor.execute('''
                        INSERT INTO audit_log (id, document_id, action, actor, actor_type, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (f"audit-{uuid.uuid4()}", doc_id, 'CREATE', created_by, 'app', now))
                    
                    replica_conn.commit()
                    replica_conn.close()
                    logger.info(f"[SQLITE-REPLICA] Document replicated successfully: doc_id={doc_id}")
                    replica_result = {'success': True, 'message': 'Document replicated to replica DB'}
                except Exception as e:
                    logger.warning(f"[SQLITE-REPLICA] Replication failed (non-critical): {e}")
                    replica_result = {'success': False, 'error': str(e)}
            
            # Log the action
            cursor.execute('''
                INSERT INTO audit_log (id, document_id, action, actor, actor_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (f"audit-{uuid.uuid4()}", doc_id, 'CREATE', created_by, 'app', now))

            conn.commit()
            conn.close()

            logger.debug(f"store_document: doc.id={doc_id}, storage_location={original_file}, provider_id=sqlite")
            return (
                Document(
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
                    file_hash=file_hash,
                    storage_location=original_file if original_file else None,
                    provider_id='sqlite',
                    replication=replication,
                    s3_result=s3_result,
                    message=message
                ),
                False
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
                   app_data, created_by, created_at, updated_at, version, deleted_at, file_hash,
                   replication, s3_result, message
            FROM documents WHERE id = ? AND deleted_at IS NULL
        ''', (document_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        doc = Document(
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
            file_hash=row[12],
            storage_location=row[2] if row[2] else None,
            provider_id='sqlite',
            replication=json.loads(row[13]) if row[13] else None,
            s3_result=json.loads(row[14]) if row[14] else None,
            message=row[15]
        )
        logger.debug(f"retrieve_document: doc.id={doc.id}, storage_location={doc.storage_location}, provider_id={doc.provider_id}")
        return doc

    async def update_document_metadata(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        updated_by: str = 'api',
        replace: bool = False,
    ) -> Optional[Document]:
        """Update metadata for a single document and return the refreshed row."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                'SELECT metadata, version FROM documents WHERE id = ? AND deleted_at IS NULL',
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"[METADATA-UPDATE] Document not found: {document_id}")
                conn.close()
                return None

            current_metadata = json.loads(row[0]) if row[0] else {}
            next_metadata = metadata or {}
            merged_metadata = next_metadata if replace else deep_merge_dict(current_metadata, next_metadata)
            next_version = int(row[1] or 1) + 1
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                'UPDATE documents SET metadata = ?, updated_at = ?, version = ? WHERE id = ?',
                (json.dumps(merged_metadata), now, next_version, document_id),
            )
            conn.commit()

            cursor.execute('''
                SELECT id, type, original_file, file_format, processed_data, metadata,
                       app_data, created_by, created_at, updated_at, version, deleted_at, file_hash,
                       replication, s3_result, message
                FROM documents WHERE id = ? AND deleted_at IS NULL
            ''', (document_id,))
            refreshed = cursor.fetchone()
            conn.close()

            logger.info(
                f"[METADATA-UPDATE] document_id={document_id} updated_by={updated_by} "
                f"replace={replace} version={next_version}"
            )

            if not refreshed:
                return None

            return Document(
                id=refreshed[0],
                type=refreshed[1],
                original_file=refreshed[2],
                file_format=refreshed[3],
                processed_data=json.loads(refreshed[4]),
                metadata=json.loads(refreshed[5]),
                app_data=json.loads(refreshed[6]),
                created_by=refreshed[7],
                created_at=refreshed[8],
                updated_at=refreshed[9],
                version=refreshed[10],
                deleted_at=refreshed[11],
                file_hash=refreshed[12],
                storage_location=refreshed[2] if refreshed[2] else None,
                provider_id='sqlite',
                replication=json.loads(refreshed[13]) if refreshed[13] else None,
                s3_result=json.loads(refreshed[14]) if refreshed[14] else None,
                message=refreshed[15],
            )

        except Exception as e:
            conn.close()
            logger.error(f"Error updating document metadata for {document_id}: {e}", exc_info=True)
            raise

    async def retrieve_document_file(self, document_id: str) -> Optional[bytes]:
        """Retrieve the original file BLOB for a document by ID"""
        logger.debug(f"[RETRIEVE-FILE] Attempting to retrieve file for document_id={document_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT file_blob, file_mime FROM document_files WHERE document_id = ?
            ''', (document_id,))

            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[RETRIEVE-FILE] File not found for document_id={document_id}")
                return None

            file_blob, file_mime = row
            logger.info(f"[RETRIEVE-FILE] File retrieved for document_id={document_id}, size={len(file_blob) if file_blob else 0} bytes, mime={file_mime}")
            return file_blob
        except Exception as e:
            logger.error(f"[RETRIEVE-FILE] Error retrieving file for document_id={document_id}: {e}", exc_info=True)
            return None
        finally:
            conn.close()

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
            doc = Document(
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
                storage_location=row[2] if row[2] else None,
                provider_id='sqlite'
            )
            logger.debug(f"list_documents: doc.id={doc.id}, storage_location={doc.storage_location}, provider_id={doc.provider_id}")
            documents.append(doc)

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

    def _cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec_a: First vector (list of floats)
            vec_b: Second vector (list of floats)
            
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
            logger.error(f"[SEARCH-DOCUMENTS] Error calculating cosine similarity: {e}")
            return 0.0

    async def search_documents(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 5,
        min_confidence: float = 0.5,
        include_original_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search documents using embeddings (semantic) or keyword fallback.
        
        Args:
            query: Search query string
            query_embedding: Optional embedding vector for semantic search
            limit: Max results to return
            min_confidence: Minimum relevance score (0-1)
            include_original_content: Whether to include original file data
            
        Returns:
            List of documents with relevance scores
        """
        logger.info(f"[SEARCH-DOCUMENTS] Searching for: '{query}' (embedding={'yes' if query_embedding else 'no'})")

        def _tokenize_search_text(text: str) -> List[str]:
            stopwords = {
                "a", "an", "are", "as", "at", "be", "by", "do", "does", "for", "from",
                "have", "in", "is", "it", "of", "on", "or", "the", "to", "was", "were",
                "what", "when", "where", "who", "why", "with", "any", "document", "documents",
                "archive", "content", "reference", "references", "mentioned", "mentions", "mention",
                "place", "organization", "organizations", "person", "people", "related", "about",
            }
            tokens: List[str] = []
            seen = set()
            for raw_token in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", (text or "").lower()):
                if len(raw_token) < 3 or raw_token in stopwords or raw_token in seen:
                    continue
                seen.add(raw_token)
                tokens.append(raw_token)
            return tokens

        def _normalize_search_token(token: str) -> str:
            normalized = re.sub(r"[^a-z0-9]+", "", (token or "").lower())
            if len(normalized) > 4:
                if normalized.endswith("ies"):
                    return normalized[:-3] + "y"
                if normalized.endswith("es") and len(normalized) > 5:
                    return normalized[:-2]
                if normalized.endswith("s") and len(normalized) > 4:
                    return normalized[:-1]
            return normalized

        def _token_overlap_score(text: str, query_terms: List[str]) -> float:
            if not text or not query_terms:
                return 0.0

            text_tokens = set(_tokenize_search_text(text))
            normalized_text_tokens = {_normalize_search_token(token) for token in text_tokens}
            if not text_tokens:
                return 0.0

            matched = []
            for term in query_terms:
                normalized_term = _normalize_search_token(term)
                if term in text_tokens or normalized_term in text_tokens or normalized_term in normalized_text_tokens:
                    matched.append(term)
            if not matched:
                return 0.0

            overlap = len(matched) / max(len(query_terms), 1)
            return min(0.45 + (overlap * 0.4), 0.9)

        def _collect_searchable_text(value: Any, fragments: List[str]) -> None:
            if value is None:
                return
            if isinstance(value, dict):
                for key, nested_value in value.items():
                    if key == 'embedding_vector':
                        continue
                    _collect_searchable_text(nested_value, fragments)
                return
            if isinstance(value, list):
                for item in value:
                    _collect_searchable_text(item, fragments)
                return
            if isinstance(value, (str, int, float, bool)):
                text = str(value).strip()
                if text:
                    fragments.append(text)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            results = []
            
            # Step 1: Fetch all documents
            logger.debug("[SEARCH-DOCUMENTS] Fetching documents from database...")
            cursor.execute('''
                SELECT id, type, original_file, file_format, processed_data, metadata,
                       app_data, created_by, created_at, updated_at, version, file_size, file_hash
                FROM documents
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1000
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            logger.debug(f"[SEARCH-DOCUMENTS] Loaded {len(rows)} documents for searching")
            query_terms = _tokenize_search_text(query)
            logger.info(
                "[SEARCH-DOCUMENTS] Query terms=%s min_confidence=%.2f include_original_content=%s row_count=%d",
                query_terms,
                min_confidence,
                include_original_content,
                len(rows),
            )
            
            # Step 2: Score documents
            for row in rows:
                doc_id = row[0]
                doc_type = row[1]
                original_file = row[2]
                file_format = row[3]
                processed_data = json.loads(row[4]) if row[4] else {}
                metadata = json.loads(row[5]) if row[5] else {}
                app_data = json.loads(row[6]) if row[6] else {}
                created_by = row[7]
                created_at = row[8]
                updated_at = row[9]
                version = row[10]
                file_size = row[11]
                file_hash = row[12]
                
                relevance_score = 0.0
                match_method = "none"
                matched_path = None
                matched_text = ""
                
                # Method 1: Semantic search using embeddings
                if query_embedding:
                    try:
                        # Get document embedding from app_data
                        doc_embedding = app_data.get('embedding_vector', None)
                        
                        # If embedding is a string (JSON), parse it
                        if doc_embedding and isinstance(doc_embedding, str):
                            try:
                                doc_embedding = json.loads(doc_embedding)
                                logger.debug(f"[SEARCH-DOCUMENTS] Parsed embedding from JSON string")
                            except:
                                doc_embedding = None
                        
                        if doc_embedding and isinstance(doc_embedding, list):
                            logger.debug(f"[SEARCH-DOCUMENTS] Found embedding for {original_file} (dim={len(doc_embedding)})")
                            # Calculate cosine similarity (range: -1 to 1)
                            raw_similarity = self._cosine_similarity(query_embedding, doc_embedding)
                            # Normalize to [0, 1] range: (similarity + 1) / 2
                            similarity = (raw_similarity + 1.0) / 2.0
                            logger.info(f"[SEARCH-DOCUMENTS] {original_file}: raw_sim={raw_similarity:.4f}, normalized={similarity:.4f}, threshold={min_confidence}")
                            if similarity >= min_confidence:
                                relevance_score = similarity
                                match_method = "semantic"
                                # Prefer a short excerpt from metadata or processed_data for semantic matches
                                if metadata.get('summary'):
                                    matched_text = metadata.get('summary', '')[:300]
                                    matched_path = 'metadata.summary'
                                elif isinstance(processed_data, dict) and processed_data.get('content'):
                                    matched_text = processed_data.get('content', '')[:300]
                                    matched_path = 'processed_data.content'
                                else:
                                    matched_text = ''
                                    matched_path = 'semantic_embedding'
                                logger.info(f"[SEARCH-DOCUMENTS] ✅ MATCH: {original_file} (score={similarity:.3f})")
                            else:
                                logger.debug(f"[SEARCH-DOCUMENTS] Below threshold: {similarity:.4f} < {min_confidence}")
                        else:
                            logger.debug(f"[SEARCH-DOCUMENTS] No embedding or not a list for {original_file}: type={type(doc_embedding)}")
                    except Exception as e:
                        logger.error(f"[SEARCH-DOCUMENTS] Error in semantic search: {e}", exc_info=True)
                        pass  # Fall through to keyword search
                
                # Method 2: Keyword search (if no semantic match or no embedding)
                if relevance_score < min_confidence:
                    query_lower = query.lower()
                    keyword_score = 0.0
                    
                    # Check filename
                    if original_file and query_lower in original_file.lower():
                        keyword_score = max(keyword_score, 0.7)
                        matched_path = 'original_file'
                        matched_text = original_file
                    
                    # Check document type
                    if doc_type and query_lower in doc_type.lower():
                        keyword_score = max(keyword_score, 0.6)
                        matched_path = 'type'
                        matched_text = doc_type
                    
                    # Check metadata summaries and topics
                    if metadata:
                        if metadata.get('summary') and query_lower in metadata.get('summary', '').lower():
                            keyword_score = max(keyword_score, 0.6)
                            matched_path = 'metadata.summary'
                            matched_text = metadata.get('summary', '')
                        if metadata.get('topics'):
                            topics = metadata.get('topics', [])
                            if isinstance(topics, list):
                                for topic in topics:
                                    if query_lower in str(topic).lower():
                                        keyword_score = max(keyword_score, 0.5)
                                        matched_path = 'metadata.topics'
                                        matched_text = str(topic)
                                        break
                        if metadata.get('places'):
                            places = metadata.get('places', [])
                            if isinstance(places, list):
                                for place in places:
                                    if query_lower in str(place).lower():
                                        keyword_score = max(keyword_score, 0.5)
                                        matched_path = 'metadata.places'
                                        matched_text = str(place)
                                        break
                    
                    # Check processed data
                    if processed_data:
                        for key, val in processed_data.items():
                            if isinstance(val, str) and query_lower in val.lower():
                                keyword_score = max(keyword_score, 0.5)
                                matched_path = f'processed_data.{key}'
                                matched_text = val if isinstance(val, str) else str(val)
                                break

                    if keyword_score < min_confidence:
                        searchable_fields = []
                        if original_file:
                            searchable_fields.append(original_file)
                        if doc_type:
                            searchable_fields.append(doc_type)
                        _collect_searchable_text(metadata, searchable_fields)
                        _collect_searchable_text(processed_data, searchable_fields)

                        overlap_score = 0.0
                        best_field = ""
                        best_field_full = ""
                        for field_text in searchable_fields:
                            field_score = _token_overlap_score(field_text, query_terms)
                            if field_score > overlap_score:
                                overlap_score = field_score
                                best_field_full = field_text
                                best_field = field_text[:160]

                        logger.debug(
                            "[SEARCH-DOCUMENTS] Keyword evaluation: file=%s fields=%d query_terms=%s overlap_score=%.3f best_field=%r",
                            original_file,
                            len(searchable_fields),
                            query_terms,
                            overlap_score,
                            best_field,
                        )

                        # If overlap produced the best signal, prefer it for matched_text/path
                        if overlap_score >= keyword_score:
                            matched_path = 'searchable_field'
                            matched_text = best_field_full
                        keyword_score = max(keyword_score, overlap_score)
                    
                    logger.info(f"[SEARCH-DOCUMENTS] After keyword matching: file={original_file} keyword_score={keyword_score:.4f} threshold={min_confidence} passes={keyword_score >= min_confidence}")
                    if keyword_score >= min_confidence:
                        relevance_score = keyword_score
                        match_method = "keyword"
                        logger.info(f"[SEARCH-DOCUMENTS] Keyword match: {original_file} (score={keyword_score:.3f})")
                        match_method = "keyword"
                        logger.info(f"[SEARCH-DOCUMENTS] Keyword match: {original_file} (score={keyword_score:.3f})")
                    else:
                        logger.debug(
                            "[SEARCH-DOCUMENTS] No match: file=%s semantic=%s keyword_score=%.3f threshold=%.2f query_terms=%s",
                            original_file,
                            "yes" if query_embedding else "no",
                            keyword_score,
                            min_confidence,
                            query_terms,
                        )
                
                # Add to results if scored above threshold
                logger.debug(f"[SEARCH-DOCUMENTS] Gating check: relevance_score={relevance_score:.4f} >= min_confidence={min_confidence}? {relevance_score >= min_confidence}")
                if relevance_score >= min_confidence:
                    # Extract excerpt from metadata or processed data
                    excerpt = ""
                    if metadata.get('summary'):
                        excerpt = metadata.get('summary', '')[:300]
                    elif isinstance(processed_data, dict) and processed_data.get('content'):
                        content = processed_data.get('content', '')
                        if isinstance(content, str):
                            excerpt = content[:300]
                    
                    result = {
                        'document_id': doc_id,
                        'type': doc_type,
                        'original_file': original_file,
                        'file_format': file_format,
                        'relevance_score': round(relevance_score, 3),
                        'match_method': match_method,
                        'matched_path': matched_path,
                        'matched_text': (matched_text or '')[:400],
                        'created_at': created_at,
                        'created_by': created_by,
                        'summary': metadata.get('summary', '') if isinstance(metadata, dict) else '',
                        'topics': metadata.get('topics', []) if isinstance(metadata, dict) else [],
                        'places': metadata.get('places', []) if isinstance(metadata, dict) else [],
                        'excerpt': excerpt,
                    }
                    
                    if include_original_content:
                        result['original_file_data'] = processed_data.get('content', '') if isinstance(processed_data, dict) else ''
                    
                    logger.info(f"[SEARCH-DOCUMENTS] ✅ Adding result: {original_file} (score={relevance_score:.3f}, method={match_method})")
                    results.append(result)
            
            # Step 3: Sort by relevance and limit
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            results = results[:limit]
            
            logger.info(
                "[SEARCH-DOCUMENTS] ✅ Search complete: %d results found; top_results=%s",
                len(results),
                [
                    {
                        "document_id": item.get("document_id"),
                        "file": item.get("original_file"),
                        "score": item.get("relevance_score"),
                        "method": item.get("match_method"),
                    }
                    for item in results[:5]
                ],
            )
            return results
            
        except Exception as e:
            logger.error(f"[SEARCH-DOCUMENTS] ❌ Error during search: {e}", exc_info=True)
            return []

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
            file_hash=row[12],
            storage_location=row[2],
            provider_id='sqlite'
        )
