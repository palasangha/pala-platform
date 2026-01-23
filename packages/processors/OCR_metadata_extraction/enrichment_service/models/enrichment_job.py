"""
MongoDB model for enrichment jobs
Tracks batch enrichment progress and metadata
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class EnrichmentJobStatus(str, Enum):
    """Enrichment job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    REVIEW_PENDING = "review_pending"


class EnrichmentJob:
    """MongoDB model for enrichment job"""

    collection_name = "enrichment_jobs"

    def __init__(
        self,
        job_id: str,
        ocr_job_id: str,
        collection_id: str,
        total_documents: int = 0,
        status: str = EnrichmentJobStatus.PENDING,
        created_at: Optional[datetime] = None,
        **kwargs
    ):
        self.job_id = job_id
        self.ocr_job_id = ocr_job_id
        self.collection_id = collection_id
        self.total_documents = total_documents
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Progress tracking
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.review_count = 0

        # Cost tracking
        self.cost_summary = {
            "ollama_calls": 0,
            "claude_haiku_tokens": 0,
            "claude_sonnet_tokens": 0,
            "claude_opus_tokens": 0,
            "estimated_cost_usd": 0.0
        }

        # Additional data
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB"""
        return {
            "job_id": self.job_id,
            "ocr_job_id": self.ocr_job_id,
            "collection_id": self.collection_id,
            "total_documents": self.total_documents,
            "status": self.status,
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "review_count": self.review_count,
            "cost_summary": self.cost_summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnrichmentJob":
        """Create from MongoDB document"""
        job = cls(
            job_id=data["job_id"],
            ocr_job_id=data["ocr_job_id"],
            collection_id=data["collection_id"],
            total_documents=data.get("total_documents", 0),
            status=data.get("status", EnrichmentJobStatus.PENDING),
            created_at=data.get("created_at")
        )
        job.processed_count = data.get("processed_count", 0)
        job.success_count = data.get("success_count", 0)
        job.error_count = data.get("error_count", 0)
        job.review_count = data.get("review_count", 0)
        job.cost_summary = data.get("cost_summary", {})
        job.updated_at = data.get("updated_at", datetime.utcnow())
        return job
