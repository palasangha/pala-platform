"""
Storage Provider Interface

Defines the abstract interface that all storage providers must implement.
This allows different backends (SQLite, PostgreSQL, AWS, etc.) to be
used interchangeably without changing the storage agent code.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Document:
    """Represents a stored document"""
    id: str
    type: str  # 'transcript', 'ocr_document', 'image', 'video', 'audio'
    original_file: str  # S3 path or local path
    file_format: str  # 'pdf', 'mp3', 'jpg', etc.
    processed_data: Dict[str, Any]  # OCR text, transcript, image metadata, etc.
    metadata: Dict[str, Any]  # Shared: language, date, location, entities, topics
    app_data: Dict[str, Any]  # App-specific: project_id, folder, tags, collection
    created_by: str  # Which app created this
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    version: int = 1
    deleted_at: Optional[str] = None
    file_hash: Optional[str] = None  # SHA-256 for deduplication


@dataclass
class Extraction:
    """Represents a stored extraction (generic result from any extraction tool)"""
    id: str
    source_type: str  # 'ocr', 'transcription', 'translation', 'custom'
    source_id: str  # ID of source file/input
    data: Any  # The actual extracted content
    data_type: str  # 'text', 'json', 'binary'
    metadata: Dict[str, Any]
    provider: str  # Which model/service performed extraction
    confidence: Optional[float] = None
    created_by: str = 'api'
    created_at: str = ''


class StorageProvider(ABC):
    """Abstract base class for all storage providers"""

    @abstractmethod
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
        """Store a document"""
        pass

    @abstractmethod
    async def retrieve_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID"""
        pass

    @abstractmethod
    async def list_documents(
        self,
        doc_type: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List documents with optional filters"""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def retrieve_extraction(self, extraction_id: str) -> Optional[Extraction]:
        """Retrieve an extraction by ID"""
        pass

    @abstractmethod
    async def list_extractions(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List extractions with optional filters"""
        pass

    @abstractmethod
    async def create_relationship(
        self,
        from_document_id: str,
        to_document_id: str,
        relationship_type: str,
        created_by: str = 'api',
    ) -> Dict[str, Any]:
        """Create a relationship between two documents"""
        pass

    @abstractmethod
    async def add_tags(
        self,
        document_id: str,
        tags: Dict[str, str],
        created_by: str = 'api',
    ) -> Dict[str, Any]:
        """Add tags to a document"""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def search_full_text(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Document]:
        """Full-text search across documents"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        pass

    @abstractmethod
    async def delete_all_documents(self) -> int:
        """Delete all documents (for testing/reset)"""
        pass

    @abstractmethod
    async def find_by_hash(self, file_hash: str) -> Optional[Document]:
        """Find document by file hash (for deduplication)"""
        pass
