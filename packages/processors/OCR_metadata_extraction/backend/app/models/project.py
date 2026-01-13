from datetime import datetime
from bson import ObjectId

class Project:
    """Project model for database operations"""

    @staticmethod
    def create(mongo, user_id, name, description=''):
        """Create a new project"""
        project_data = {
            'user_id': ObjectId(user_id),
            'name': name,
            'description': description,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'image_count': 0
        }

        result = mongo.db.projects.insert_one(project_data)
        project_data['_id'] = result.inserted_id
        return project_data

    @staticmethod
    def find_by_id(mongo, project_id, user_id=None):
        """Find project by ID"""
        query = {'_id': ObjectId(project_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.projects.find_one(query)

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=50):
        """Find all projects for a user"""
        return list(mongo.db.projects.find(
            {'user_id': ObjectId(user_id)}
        ).sort('updated_at', -1).skip(skip).limit(limit))

    @staticmethod
    def update(mongo, project_id, user_id, data):
        """Update project"""
        data['updated_at'] = datetime.utcnow()
        return mongo.db.projects.update_one(
            {'_id': ObjectId(project_id), 'user_id': ObjectId(user_id)},
            {'$set': data}
        )

    @staticmethod
    def delete(mongo, project_id, user_id):
        """Delete project and associated images"""
        # Delete all images associated with this project
        mongo.db.images.delete_many({
            'project_id': ObjectId(project_id)
        })

        # Delete the project
        return mongo.db.projects.delete_one({
            '_id': ObjectId(project_id),
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def increment_image_count(mongo, project_id):
        """Increment image count"""
        return mongo.db.projects.update_one(
            {'_id': ObjectId(project_id)},
            {'$inc': {'image_count': 1}, '$set': {'updated_at': datetime.utcnow()}}
        )

    @staticmethod
    def decrement_image_count(mongo, project_id):
        """Decrement image count"""
        return mongo.db.projects.update_one(
            {'_id': ObjectId(project_id)},
            {'$inc': {'image_count': -1}, '$set': {'updated_at': datetime.utcnow()}}
        )

    @staticmethod
    def to_dict(project):
        """Convert project document to dictionary"""
        if not project:
            return None

        return {
            'id': str(project['_id']),
            'user_id': str(project['user_id']),
            'name': project['name'],
            'description': project.get('description', ''),
            'image_count': project.get('image_count', 0),
            'created_at': project['created_at'].isoformat() if project.get('created_at') else None,
            'updated_at': project['updated_at'].isoformat() if project.get('updated_at') else None
        }
