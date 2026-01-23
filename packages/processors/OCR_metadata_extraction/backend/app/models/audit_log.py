from datetime import datetime
from bson import ObjectId

class AuditLog:
    """AuditLog model for tracking all system actions"""

    # Action types
    ACTION_USER_LOGIN = 'USER_LOGIN'
    ACTION_USER_REGISTER = 'USER_REGISTER'
    ACTION_USER_LOGOUT = 'USER_LOGOUT'
    ACTION_CLASSIFY_DOCUMENT = 'CLASSIFY_DOCUMENT'
    ACTION_RUN_OCR = 'RUN_OCR'
    ACTION_CLAIM_DOCUMENT = 'CLAIM_DOCUMENT'
    ACTION_APPROVE_DOCUMENT = 'APPROVE_DOCUMENT'
    ACTION_REJECT_DOCUMENT = 'REJECT_DOCUMENT'
    ACTION_EXPORT_DOCUMENTS = 'EXPORT_DOCUMENTS'
    ACTION_VIEW_DOCUMENT = 'VIEW_DOCUMENT'
    ACTION_ROLE_ASSIGNED = 'ROLE_ASSIGNED'
    ACTION_ROLE_REMOVED = 'ROLE_REMOVED'
    ACTION_USER_CREATED = 'USER_CREATED'
    ACTION_UNAUTHORIZED_ACCESS = 'UNAUTHORIZED_ACCESS'

    @staticmethod
    def create(mongo, user_id, action_type, resource_type=None, resource_id=None,
               previous_state=None, new_state=None, details=None):
        """Create an audit log entry"""
        log_data = {
            'user_id': ObjectId(user_id) if user_id else None,
            'action_type': action_type,
            'resource_type': resource_type,
            'resource_id': ObjectId(resource_id) if resource_id else None,
            'previous_state': previous_state,
            'new_state': new_state,
            'details': details or {},
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow(),
            'timestamp': datetime.utcnow()
        }

        result = mongo.db.audit_logs.insert_one(log_data)
        log_data['_id'] = result.inserted_id
        return log_data

    @staticmethod
    def find_by_id(mongo, log_id):
        """Find audit log by ID"""
        return mongo.db.audit_logs.find_one({'_id': ObjectId(log_id)})

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=100):
        """Find all audit logs for a user"""
        return list(mongo.db.audit_logs.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_by_resource(mongo, resource_id, skip=0, limit=100):
        """Find all audit logs for a resource"""
        return list(mongo.db.audit_logs.find(
            {'resource_id': ObjectId(resource_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_by_action_type(mongo, action_type, skip=0, limit=100):
        """Find all audit logs by action type"""
        return list(mongo.db.audit_logs.find(
            {'action_type': action_type}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_by_date_range(mongo, start_date, end_date, skip=0, limit=100):
        """Find audit logs within a date range"""
        return list(mongo.db.audit_logs.find(
            {'created_at': {'$gte': start_date, '$lte': end_date}}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def to_dict(log):
        """Convert audit log document to dictionary"""
        if not log:
            return None

        return {
            'id': str(log['_id']),
            'user_id': str(log['user_id']) if log.get('user_id') else None,
            'action_type': log['action_type'],
            'resource_type': log.get('resource_type'),
            'resource_id': str(log['resource_id']) if log.get('resource_id') else None,
            'previous_state': log.get('previous_state'),
            'new_state': log.get('new_state'),
            'details': log.get('details', {}),
            'ip_address': log.get('ip_address'),
            'user_agent': log.get('user_agent'),
            'created_at': log['created_at'].isoformat() if log.get('created_at') else None
        }

    @staticmethod
    def get_statistics(mongo, start_date=None, end_date=None):
        """Get statistics about audit logs"""
        query = {}
        if start_date or end_date:
            query['created_at'] = {}
            if start_date:
                query['created_at']['$gte'] = start_date
            if end_date:
                query['created_at']['$lte'] = end_date

        # Count by action type
        action_counts = list(mongo.db.audit_logs.aggregate([
            {'$match': query},
            {'$group': {'_id': '$action_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]))

        # Count by user
        user_counts = list(mongo.db.audit_logs.aggregate([
            {'$match': query},
            {'$group': {'_id': '$user_id', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]))

        return {
            'total_logs': mongo.db.audit_logs.count_documents(query),
            'action_counts': action_counts,
            'user_counts': user_counts
        }
