"""
MongoDB model for enriched documents
Stores OCR data, enriched results, and quality metrics
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class ReviewStatus(str, Enum):
    """Review status for enriched document"""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class EnrichedDocument:
    """MongoDB model for enriched document"""

    collection_name = "enriched_documents"

    def __init__(
        self,
        document_id: str,
        enrichment_job_id: str,
        ocr_data: Dict[str, Any],
        created_at: Optional[datetime] = None
    ):
        self.document_id = document_id
        self.enrichment_job_id = enrichment_job_id
        self.ocr_data = ocr_data
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Enriched results
        self.enriched_data: Dict[str, Any] = {
            "metadata": {},
            "document": {},
            "content": {},
            "analysis": {}
        }

        # Quality metrics
        self.quality_metrics = {
            "completeness_score": 0.0,
            "confidence_scores": {},
            "missing_fields": [],
            "low_confidence_fields": []
        }

        # Enrichment metadata
        self.enrichment_metadata = {
            "phase_1_completed": None,
            "phase_2_completed": None,
            "phase_3_completed": None,
            "agent_invocations": [],
            "total_processing_time_ms": 0,
            "cost_breakdown": {}
        }

        # Review status
        self.review_status = ReviewStatus.NOT_REQUIRED
        self.review_notes = ""
        self.reviewer_id = ""
        self.review_completed_at = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB"""
        return {
            "_id": self.document_id,
            "document_id": self.document_id,
            "enrichment_job_id": self.enrichment_job_id,
            "ocr_data": self.ocr_data,
            "enriched_data": self.enriched_data,
            "quality_metrics": self.quality_metrics,
            "enrichment_metadata": self.enrichment_metadata,
            "review_status": self.review_status,
            "review_notes": self.review_notes,
            "reviewer_id": self.reviewer_id,
            "review_completed_at": self.review_completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnrichedDocument":
        """Create from MongoDB document"""
        doc = cls(
            document_id=data["document_id"],
            enrichment_job_id=data["enrichment_job_id"],
            ocr_data=data.get("ocr_data", {}),
            created_at=data.get("created_at")
        )
        doc.enriched_data = data.get("enriched_data", doc.enriched_data)
        doc.quality_metrics = data.get("quality_metrics", doc.quality_metrics)
        doc.enrichment_metadata = data.get("enrichment_metadata", doc.enrichment_metadata)
        doc.review_status = data.get("review_status", ReviewStatus.NOT_REQUIRED)
        doc.review_notes = data.get("review_notes", "")
        doc.reviewer_id = data.get("reviewer_id", "")
        doc.review_completed_at = data.get("review_completed_at")
        doc.updated_at = data.get("updated_at", datetime.utcnow())
        return doc

    def update_quality_metrics(
        self,
        completeness_score: float,
        missing_fields: List[str],
        low_confidence_fields: List[Dict[str, Any]]
    ) -> None:
        """Update quality metrics"""
        self.quality_metrics = {
            "completeness_score": completeness_score,
            "confidence_scores": self._extract_confidence_scores(),
            "missing_fields": missing_fields,
            "low_confidence_fields": low_confidence_fields
        }
        self.updated_at = datetime.utcnow()

    def _extract_confidence_scores(self) -> Dict[str, float]:
        """Extract confidence scores from enriched data"""
        scores = {}
        for section in ["metadata", "document", "content", "analysis"]:
            if section in self.enriched_data:
                scores[section] = 0.85  # Default confidence
        return scores

    def set_review_required(self, reason: str, fields: List[str]) -> None:
        """Mark document as requiring review"""
        self.review_status = ReviewStatus.PENDING
        self.review_notes = f"Review required: {reason}. Missing/low-confidence fields: {', '.join(fields)}"
        self.updated_at = datetime.utcnow()

    def approve_review(self, reviewer_id: str, corrections: Optional[Dict[str, Any]] = None) -> None:
        """Approve reviewed document"""
        self.review_status = ReviewStatus.APPROVED
        self.reviewer_id = reviewer_id
        self.review_completed_at = datetime.utcnow()

        if corrections:
            self._apply_corrections(corrections)

        self.updated_at = datetime.utcnow()

    def _apply_corrections(self, corrections: Dict[str, Any]) -> None:
        """Apply manual corrections to enriched data"""
        for path, value in corrections.items():
            parts = path.split(".")
            current = self.enriched_data
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
