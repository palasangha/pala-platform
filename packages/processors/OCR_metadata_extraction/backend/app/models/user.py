from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId

class User:
    """User model for database operations"""

    @staticmethod
    def create(mongo, email, password=None, google_id=None, name=None):
        """Create a new user"""
        user_data = {
            'email': email,
            'name': name or email.split('@')[0],
            'google_id': google_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        if password:
            user_data['password_hash'] = generate_password_hash(password)

        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return user_data

    @staticmethod
    def find_by_email(mongo, email):
        """Find user by email"""
        return mongo.db.users.find_one({'email': email})

    @staticmethod
    def find_by_id(mongo, user_id):
        """Find user by ID"""
        return mongo.db.users.find_one({'_id': ObjectId(user_id)})

    @staticmethod
    def find_by_google_id(mongo, google_id):
        """Find user by Google ID"""
        return mongo.db.users.find_one({'google_id': google_id})

    @staticmethod
    def verify_password(user, password):
        """Verify user password"""
        if not user or 'password_hash' not in user:
            return False
        return check_password_hash(user['password_hash'], password)

    @staticmethod
    def update(mongo, user_id, data):
        """Update user data"""
        data['updated_at'] = datetime.utcnow()
        return mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': data}
        )

    @staticmethod
    def to_dict(user):
        """Convert user document to dictionary (excluding sensitive data)"""
        if not user:
            return None

        return {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name'),
            'google_id': user.get('google_id'),
            'created_at': user.get('created_at').isoformat() if user.get('created_at') else None
        }
