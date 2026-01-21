from datetime import datetime
from bson import ObjectId

class Image:
    """Image model for database operations"""

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
            'verification_status': 'pending_verification',  # pending_verification, verified, rejected
            'verified_by': None,
            'verified_at': None,
            'version': 1,  # For optimistic locking
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
    def find_by_verification_status(mongo, status, skip=0, limit=100):
        """Find all images with a specific verification status"""
        return list(mongo.db.images.find(
            {'verification_status': status}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def count_by_verification_status(mongo, status):
        """Count images with a specific verification status"""
        return mongo.db.images.count_documents({'verification_status': status})

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
                },
                '$inc': {'version': 1}
            }
        )

    @staticmethod
    def update_verification_status(mongo, image_id, status, user_id, version=None):
        """
        Update verification status with optimistic locking
        
        Args:
            mongo: MongoDB connection
            image_id: ID of the image
            status: New verification status (verified, rejected)
            user_id: ID of the user performing verification
            version: Expected version for optimistic locking
        
        Returns:
            Update result
        """
        query = {'_id': ObjectId(image_id)}
        if version is not None:
            query['version'] = version

        update = {
            '$set': {
                'verification_status': status,
                'verified_by': ObjectId(user_id) if user_id else None,
                'verified_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            '$inc': {'version': 1}
        }

        return mongo.db.images.update_one(query, update)

    @staticmethod
    def update_with_version(mongo, image_id, updates, version=None):
        """
        Update image fields with optimistic locking
        
        Args:
            mongo: MongoDB connection
            image_id: ID of the image
            updates: Dictionary of fields to update
            version: Expected version for optimistic locking
        
        Returns:
            Update result
        """
        query = {'_id': ObjectId(image_id)}
        if version is not None:
            query['version'] = version

        updates['updated_at'] = datetime.utcnow()

        return mongo.db.images.update_one(
            query,
            {
                '$set': updates,
                '$inc': {'version': 1}
            }
        )

    @staticmethod
    def delete(mongo, image_id):
        """Delete image"""
        return mongo.db.images.delete_one({'_id': ObjectId(image_id)})

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
            'verification_status': image.get('verification_status', 'pending_verification'),
            'verified_by': str(image['verified_by']) if image.get('verified_by') else None,
            'verified_at': image['verified_at'].isoformat() if image.get('verified_at') else None,
            'version': image.get('version', 1),
            'created_at': image['created_at'].isoformat() if image.get('created_at') else None,
            'updated_at': image['updated_at'].isoformat() if image.get('updated_at') else None
        }
