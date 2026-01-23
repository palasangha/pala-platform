"""
ReviewQueue - Management for documents requiring human review

Routes documents with <95% completeness to human reviewers
Tracks review status and provides API for review interface
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import uuid

logger = logging.getLogger(__name__)


class ReviewQueue:
    """
    Manages documents pending human review
    """

    def __init__(self, db=None):
        """
        Initialize ReviewQueue

        Args:
            db: MongoDB database instance
        """
        self.db = db

    def create_task(
        self,
        document_id: str,
        enrichment_job_id: str,
        reason: str,
        missing_fields: List[str],
        low_confidence_fields: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Create review task for incomplete document

        Args:
            document_id: Document to review
            enrichment_job_id: Parent enrichment job
            reason: Why document needs review
            missing_fields: List of missing required fields
            low_confidence_fields: Fields with low confidence scores

        Returns:
            review_id or None
        """
        if self.db is None:
            logger.warning("Database unavailable, cannot create review task")
            return None

        try:
            review_id = f"review_{uuid.uuid4().hex[:8]}"

            task = {
                '_id': review_id,
                'document_id': document_id,
                'enrichment_job_id': enrichment_job_id,
                'reason': reason,
                'missing_fields': missing_fields,
                'low_confidence_fields': low_confidence_fields,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'assigned_to': None,
                'started_at': None,
                'completed_at': None,
                'reviewer_notes': '',
                'corrections': {}
            }

            self.db.review_queue.insert_one(task)
            logger.info(f"Created review task {review_id} for document {document_id}")
            return review_id

        except Exception as e:
            logger.error(f"Error creating review task: {e}")
            return None

    def get_pending_tasks(self, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Get pending review tasks

        Args:
            limit: Max results to return
            skip: Number of results to skip (for pagination)

        Returns:
            List of review tasks
        """
        if self.db is None:
            return []

        try:
            tasks = list(self.db.review_queue.find(
                {'status': 'pending'}
            ).sort('created_at', -1).skip(skip).limit(limit))

            return tasks

        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []

    def get_task(self, review_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific review task with full context

        Args:
            review_id: Task ID

        Returns:
            Task with enriched data for comparison
        """
        if self.db is None:
            return None

        try:
            task = self.db.review_queue.find_one({'_id': review_id})
            if not task:
                return None

            # Fetch associated enriched document and OCR data
            doc = self.db.enriched_documents.find_one({'_id': task['document_id']})
            if doc:
                task['enriched_data'] = doc.get('enriched_data', {})
                task['ocr_data'] = doc.get('ocr_data', {})
                task['quality_metrics'] = doc.get('quality_metrics', {})

            return task

        except Exception as e:
            logger.error(f"Error getting review task {review_id}: {e}")
            return None

    def assign_task(self, review_id: str, reviewer_id: str) -> bool:
        """
        Assign review task to reviewer

        Args:
            review_id: Task ID
            reviewer_id: ID of reviewer user

        Returns:
            True if assigned successfully
        """
        if self.db is None:
            return False

        try:
            result = self.db.review_queue.update_one(
                {'_id': review_id},
                {'$set': {
                    'status': 'in_progress',
                    'assigned_to': reviewer_id,
                    'started_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }}
            )

            logger.info(f"Assigned task {review_id} to reviewer {reviewer_id}")
            return result.matched_count > 0

        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            return False

    def approve_task(
        self,
        review_id: str,
        reviewer_id: str,
        reviewer_notes: str = '',
        corrections: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Approve reviewed document

        Args:
            review_id: Task ID
            reviewer_id: Reviewer user ID
            reviewer_notes: Optional notes from reviewer
            corrections: Optional corrections to enriched data

        Returns:
            True if approved successfully
        """
        if self.db is None:
            return False

        try:
            # Update review task
            result = self.db.review_queue.update_one(
                {'_id': review_id},
                {'$set': {
                    'status': 'approved',
                    'assigned_to': reviewer_id,
                    'completed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'reviewer_notes': reviewer_notes,
                    'corrections': corrections or {}
                }}
            )

            if result.matched_count == 0:
                logger.warning(f"Review task {review_id} not found")
                return False

            # Get review task to find document
            task = self.db.review_queue.find_one({'_id': review_id})
            if task:
                # Update enriched document approval status
                self.db.enriched_documents.update_one(
                    {'_id': task['document_id']},
                    {'$set': {'review_status': 'approved'}}
                )

                # Apply corrections if provided
                if corrections:
                    self.db.enriched_documents.update_one(
                        {'_id': task['document_id']},
                        {'$set': {'enriched_data': corrections}}
                    )

            logger.info(f"Approved review task {review_id}")
            return True

        except Exception as e:
            logger.error(f"Error approving task: {e}")
            return False

    def reject_task(
        self,
        review_id: str,
        reviewer_id: str,
        reason: str,
        reviewer_notes: str = ''
    ) -> bool:
        """
        Reject reviewed document and re-queue for enrichment

        Args:
            review_id: Task ID
            reviewer_id: Reviewer user ID
            reason: Reason for rejection
            reviewer_notes: Optional notes

        Returns:
            True if rejected successfully
        """
        if self.db is None:
            return False

        try:
            # Update review task
            result = self.db.review_queue.update_one(
                {'_id': review_id},
                {'$set': {
                    'status': 'rejected',
                    'assigned_to': reviewer_id,
                    'completed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'reviewer_notes': reviewer_notes,
                    'rejection_reason': reason
                }}
            )

            if result.matched_count == 0:
                return False

            # Get review task to find document and enrichment job
            task = self.db.review_queue.find_one({'_id': review_id})
            if task:
                # Update enriched document status
                self.db.enriched_documents.update_one(
                    {'_id': task['document_id']},
                    {'$set': {'review_status': 'rejected'}}
                )

                # Re-queue for enrichment if needed
                # This would trigger a new enrichment task

            logger.info(f"Rejected review task {review_id}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error rejecting task: {e}")
            return False

    def get_stats(self) -> Dict[str, int]:
        """
        Get review queue statistics

        Returns:
            Stats dict with counts by status
        """
        if self.db is None:
            return {}

        try:
            stats = {
                'pending': self.db.review_queue.count_documents({'status': 'pending'}),
                'in_progress': self.db.review_queue.count_documents({'status': 'in_progress'}),
                'approved': self.db.review_queue.count_documents({'status': 'approved'}),
                'rejected': self.db.review_queue.count_documents({'status': 'rejected'})
            }
            stats['total'] = sum(stats.values())

            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def get_document_review_history(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get review history for a document

        Args:
            document_id: Document ID

        Returns:
            List of all review tasks for this document
        """
        if self.db is None:
            return []

        try:
            history = list(self.db.review_queue.find(
                {'document_id': document_id}
            ).sort('created_at', -1))

            return history

        except Exception as e:
            logger.error(f"Error getting review history: {e}")
            return []
