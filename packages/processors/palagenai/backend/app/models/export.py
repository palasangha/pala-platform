from datetime import datetime
from bson import ObjectId

class Export:
    """Export model for database operations"""

    @staticmethod
    def create(mongo, user_id, project_id, export_data):
        """Create a new export record"""
        export_record = {
            'user_id': ObjectId(user_id),
            'project_id': ObjectId(project_id),
            'exported_at': datetime.utcnow(),
            'metadata': {
                'project_name': export_data.get('project_name'),
                'total_images': export_data.get('total_images', 0),
                'total_characters': export_data.get('total_characters', 0),
                'average_text_length': export_data.get('average_text_length', 0),
                'export_format': export_data.get('export_format', 'zip'),
            },
            'file_info': {
                'zip_filename': export_data.get('zip_filename'),
                'zip_size': export_data.get('zip_size', 0),
            },
            # Store summary of results
            'results_summary': export_data.get('results_summary', []),
        }

        result = mongo.db.exports.insert_one(export_record)
        export_record['_id'] = result.inserted_id
        return export_record

    @staticmethod
    def find_by_id(mongo, export_id, user_id=None):
        """Find export by ID"""
        query = {'_id': ObjectId(export_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.exports.find_one(query)

    @staticmethod
    def find_by_project(mongo, project_id, user_id=None, skip=0, limit=50):
        """Find all exports for a project"""
        query = {'project_id': ObjectId(project_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return list(mongo.db.exports.find(query).sort('exported_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=50):
        """Find all exports for a user"""
        return list(mongo.db.exports.find(
            {'user_id': ObjectId(user_id)}
        ).sort('exported_at', -1).skip(skip).limit(limit))

    @staticmethod
    def delete(mongo, export_id, user_id):
        """Delete export"""
        return mongo.db.exports.delete_one({
            '_id': ObjectId(export_id),
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def delete_by_project(mongo, project_id):
        """Delete all exports for a project"""
        return mongo.db.exports.delete_many({
            'project_id': ObjectId(project_id)
        })

    @staticmethod
    def to_dict(export_record):
        """Convert export document to dictionary"""
        if not export_record:
            return None

        return {
            'id': str(export_record['_id']),
            'user_id': str(export_record['user_id']),
            'project_id': str(export_record['project_id']),
            'exported_at': export_record['exported_at'].isoformat() if export_record.get('exported_at') else None,
            'metadata': export_record.get('metadata', {}),
            'file_info': export_record.get('file_info', {}),
            'results_summary': export_record.get('results_summary', [])
        }
