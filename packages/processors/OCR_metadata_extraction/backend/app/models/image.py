from datetime import datetime
from bson import ObjectId

class Image:
    """Image model for database operations"""

    # Classification constants
    CLASSIFICATION_PUBLIC = 'PUBLIC'
    CLASSIFICATION_PRIVATE = 'PRIVATE'
    VALID_CLASSIFICATIONS = [CLASSIFICATION_PUBLIC, CLASSIFICATION_PRIVATE]

    # Document status constants
    STATUS_UPLOADED = 'UPLOADED'
    STATUS_CLASSIFICATION_PENDING = 'CLASSIFICATION_PENDING'
    STATUS_CLASSIFIED = 'CLASSIFIED'
    STATUS_OCR_PROCESSING = 'OCR_PROCESSING'
    STATUS_OCR_PROCESSED = 'OCR_PROCESSED'
    STATUS_IN_REVIEW = 'IN_REVIEW'
    STATUS_REVIEWED_APPROVED = 'REVIEWED_APPROVED'
    STATUS_EXPORTED = 'EXPORTED'

    VALID_STATUSES = [
        STATUS_UPLOADED,
        STATUS_CLASSIFICATION_PENDING,
        STATUS_CLASSIFIED,
        STATUS_OCR_PROCESSING,
        STATUS_OCR_PROCESSED,
        STATUS_IN_REVIEW,
        STATUS_REVIEWED_APPROVED,
        STATUS_EXPORTED
    ]

    @staticmethod
    def create(mongo, project_id, filename, filepath, original_filename):
        """Create a new image record"""
        # Detect file type based on extension
        import os
        ext = os.path.splitext(original_filename)[1].lower()
        file_type = 'pdf' if ext == '.pdf' else 'image'

        image_data = {
            'project_id': ObjectId(project_id),
            'filename': filename,
            'filepath': filepath,
            'original_filename': original_filename,
            'file_type': file_type,
            'ocr_text': None,
            'ocr_status': 'pending',  # pending, processing, completed, failed
            'ocr_processed_at': None,
            # RBAC fields
            'classification': None,  # PUBLIC or PRIVATE
            'document_status': Image.STATUS_UPLOADED,
            'classified_by': None,
            'classified_at': None,
            'classification_reason': None,
            # Review fields
            'claimed_by': None,
            'claimed_at': None,
            'review_status': None,  # None, in_review, approved, rejected
            'reviewed_by': None,
            'reviewed_at': None,
            'manual_edits': [],
            'review_notes': None,
            'rejection_reason': None,
            # Audit fields
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = mongo.db.images.insert_one(image_data)
        image_data['_id'] = result.inserted_id
        return image_data

    @staticmethod
    def find_by_id(mongo, image_id):
        """Find image by ID"""
        return mongo.db.images.find_one({'_id': ObjectId(image_id)})

    @staticmethod
    def find_by_project(mongo, project_id, skip=0, limit=100):
        """Find all images for a project"""
        return list(mongo.db.images.find(
            {'project_id': ObjectId(project_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def update_ocr_text(mongo, image_id, ocr_text, status='completed'):
        """Update OCR text for an image"""
        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id)},
            {
                '$set': {
                    'ocr_text': ocr_text,
                    'ocr_status': status,
                    'ocr_processed_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def update_status(mongo, image_id, status):
        """Update OCR status"""
        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id)},
            {
                '$set': {
                    'ocr_status': status,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def delete(mongo, image_id):
        """Delete image"""
        return mongo.db.images.delete_one({'_id': ObjectId(image_id)})

    @staticmethod
    def classify(mongo, image_id, classification, classified_by, reason=None):
        """Classify a document"""
        if classification not in Image.VALID_CLASSIFICATIONS:
            raise ValueError(f'Invalid classification: {classification}')

        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id)},
            {
                '$set': {
                    'classification': classification,
                    'classified_by': ObjectId(classified_by),
                    'classified_at': datetime.utcnow(),
                    'classification_reason': reason,
                    'document_status': Image.STATUS_CLASSIFIED,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def claim_for_review(mongo, image_id, user_id):
        """Claim a document for review"""
        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id), 'claimed_by': None},
            {
                '$set': {
                    'claimed_by': ObjectId(user_id),
                    'claimed_at': datetime.utcnow(),
                    'review_status': 'in_review',
                    'document_status': Image.STATUS_IN_REVIEW,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def approve_document(mongo, image_id, reviewed_by, manual_edits=None, notes=None):
        """Approve a reviewed document"""
        update_data = {
            'reviewed_by': ObjectId(reviewed_by),
            'reviewed_at': datetime.utcnow(),
            'review_status': 'approved',
            'document_status': Image.STATUS_REVIEWED_APPROVED,
            'review_notes': notes,
            'updated_at': datetime.utcnow()
        }

        if manual_edits:
            update_data['manual_edits'] = manual_edits

        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id)},
            {'$set': update_data}
        )

    @staticmethod
    def reject_document(mongo, image_id, reason):
        """Reject a reviewed document"""
        return mongo.db.images.update_one(
            {'_id': ObjectId(image_id)},
            {
                '$set': {
                    'review_status': 'rejected',
                    'document_status': Image.STATUS_IN_REVIEW,
                    'rejection_reason': reason,
                    'claimed_by': None,
                    'claimed_at': None,
                    'updated_at': datetime.utcnow()
                }
            }
        )

    @staticmethod
    def get_status_summary(mongo, project_id):
        """Get status summary for a project"""
        pipeline = [
            {'$match': {'project_id': ObjectId(project_id)}},
            {'$group': {
                '_id': '$document_status',
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]
        return list(mongo.db.images.aggregate(pipeline))

    @staticmethod
    def to_dict(image):
        """Convert image document to dictionary"""
        if not image:
            return None

        # Detect file_type from filename if not stored in database (for legacy records)
        file_type = image.get('file_type')
        if not file_type:
            import os
            original_filename = image.get('original_filename', '')
            ext = os.path.splitext(original_filename)[1].lower()
            file_type = 'pdf' if ext == '.pdf' else 'image'

        return {
            'id': str(image['_id']),
            'project_id': str(image['project_id']),
            'filename': image['filename'],
            'filepath': image.get('filepath'),
            'original_filename': image['original_filename'],
            'file_type': file_type,
            'ocr_text': image.get('ocr_text'),
            'ocr_status': image.get('ocr_status', 'pending'),
            'ocr_processed_at': image['ocr_processed_at'].isoformat() if image.get('ocr_processed_at') else None,
            # RBAC fields
            'classification': image.get('classification'),
            'document_status': image.get('document_status', Image.STATUS_UPLOADED),
            'classified_by': str(image['classified_by']) if image.get('classified_by') else None,
            'classified_at': image['classified_at'].isoformat() if image.get('classified_at') else None,
            'classification_reason': image.get('classification_reason'),
            # Review fields
            'claimed_by': str(image['claimed_by']) if image.get('claimed_by') else None,
            'claimed_at': image['claimed_at'].isoformat() if image.get('claimed_at') else None,
            'review_status': image.get('review_status'),
            'reviewed_by': str(image['reviewed_by']) if image.get('reviewed_by') else None,
            'reviewed_at': image['reviewed_at'].isoformat() if image.get('reviewed_at') else None,
            'manual_edits': image.get('manual_edits', []),
            'review_notes': image.get('review_notes'),
            'rejection_reason': image.get('rejection_reason'),
            # Timestamps
            'created_at': image['created_at'].isoformat() if image.get('created_at') else None,
            'updated_at': image['updated_at'].isoformat() if image.get('updated_at') else None
        }
