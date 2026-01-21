"""
Verification Audit Model
Tracks all changes made during the verification process with user and timestamp
"""
from datetime import datetime
from bson import ObjectId


class VerificationAudit:
    """Model for tracking verification changes and audit trail"""

    @staticmethod
    def create(mongo, image_id, user_id, action, field_name=None, old_value=None, new_value=None, notes=None):
        """
        Create an audit log entry
        
        Args:
            mongo: MongoDB connection
            image_id: ID of the image being verified
            user_id: ID of the user making the change
            action: Type of action (edit, verify, reject, undo, redo)
            field_name: Name of the field changed (for edit actions)
            old_value: Previous value
            new_value: New value
            notes: Optional notes about the change
        
        Returns:
            Created audit entry
        """
        audit_data = {
            'image_id': ObjectId(image_id),
            'user_id': ObjectId(user_id),
            'action': action,
            'field_name': field_name,
            'old_value': old_value,
            'new_value': new_value,
            'notes': notes,
            'created_at': datetime.utcnow()
        }

        result = mongo.db.verification_audits.insert_one(audit_data)
        audit_data['_id'] = result.inserted_id
        return audit_data

    @staticmethod
    def find_by_image(mongo, image_id, skip=0, limit=100):
        """Find all audit entries for a specific image"""
        return list(mongo.db.verification_audits.find(
            {'image_id': ObjectId(image_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=100):
        """Find all audit entries by a specific user"""
        return list(mongo.db.verification_audits.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_recent(mongo, limit=50):
        """Find recent audit entries across all images"""
        return list(mongo.db.verification_audits.find().sort('created_at', -1).limit(limit))

    @staticmethod
    def count_by_image(mongo, image_id):
        """Count audit entries for an image"""
        return mongo.db.verification_audits.count_documents({'image_id': ObjectId(image_id)})

    @staticmethod
    def to_dict(audit):
        """Convert audit document to dictionary"""
        if not audit:
            return None

        return {
            'id': str(audit['_id']),
            'image_id': str(audit['image_id']),
            'user_id': str(audit['user_id']),
            'action': audit['action'],
            'field_name': audit.get('field_name'),
            'old_value': audit.get('old_value'),
            'new_value': audit.get('new_value'),
            'notes': audit.get('notes'),
            'created_at': audit['created_at'].isoformat() if audit.get('created_at') else None
        }
