from datetime import datetime
from bson import ObjectId

class Role:
    """Role model for RBAC system"""

    # Predefined roles
    ROLE_ADMIN = 'admin'
    ROLE_REVIEWER = 'reviewer'
    ROLE_TEACHER = 'teacher'

    VALID_ROLES = [ROLE_ADMIN, ROLE_REVIEWER, ROLE_TEACHER]

    # Permissions constants
    PERMISSION_CLASSIFY_DOCUMENT = 'classify_document'
    PERMISSION_RUN_OCR = 'run_ocr'
    PERMISSION_VIEW_PUBLIC_QUEUE = 'view_public_queue'
    PERMISSION_VIEW_PRIVATE_QUEUE = 'view_private_queue'
    PERMISSION_CLAIM_DOCUMENT = 'claim_document'
    PERMISSION_APPROVE_DOCUMENT = 'approve_document'
    PERMISSION_REJECT_DOCUMENT = 'reject_document'
    PERMISSION_VIEW_DASHBOARD = 'view_dashboard'
    PERMISSION_VIEW_AUDIT_LOGS = 'view_audit_logs'
    PERMISSION_EXPORT_DOCUMENTS = 'export_documents'
    PERMISSION_MANAGE_USERS = 'manage_users'
    PERMISSION_MANAGE_ROLES = 'manage_roles'

    # Role permission mappings
    ROLE_PERMISSIONS = {
        ROLE_ADMIN: [
            PERMISSION_CLASSIFY_DOCUMENT,
            PERMISSION_RUN_OCR,
            PERMISSION_VIEW_PUBLIC_QUEUE,
            PERMISSION_VIEW_PRIVATE_QUEUE,
            PERMISSION_CLAIM_DOCUMENT,
            PERMISSION_APPROVE_DOCUMENT,
            PERMISSION_REJECT_DOCUMENT,
            PERMISSION_VIEW_DASHBOARD,
            PERMISSION_VIEW_AUDIT_LOGS,
            PERMISSION_EXPORT_DOCUMENTS,
            PERMISSION_MANAGE_USERS,
            PERMISSION_MANAGE_ROLES
        ],
        ROLE_REVIEWER: [
            PERMISSION_VIEW_PUBLIC_QUEUE,
            PERMISSION_CLAIM_DOCUMENT,
            PERMISSION_APPROVE_DOCUMENT,
            PERMISSION_REJECT_DOCUMENT
        ],
        ROLE_TEACHER: [
            PERMISSION_VIEW_PUBLIC_QUEUE,
            PERMISSION_VIEW_PRIVATE_QUEUE,
            PERMISSION_CLAIM_DOCUMENT,
            PERMISSION_APPROVE_DOCUMENT,
            PERMISSION_REJECT_DOCUMENT
        ]
    }

    @staticmethod
    def create(mongo, role_name, description=''):
        """Create a new role"""
        if role_name not in Role.VALID_ROLES:
            raise ValueError(f'Invalid role: {role_name}')

        role_data = {
            'name': role_name,
            'description': description,
            'permissions': Role.ROLE_PERMISSIONS.get(role_name, []),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Check if role already exists
        existing = mongo.db.roles.find_one({'name': role_name})
        if existing:
            return existing

        result = mongo.db.roles.insert_one(role_data)
        role_data['_id'] = result.inserted_id
        return role_data

    @staticmethod
    def find_by_name(mongo, role_name):
        """Find role by name"""
        return mongo.db.roles.find_one({'name': role_name})

    @staticmethod
    def find_by_id(mongo, role_id):
        """Find role by ID"""
        return mongo.db.roles.find_one({'_id': ObjectId(role_id)})

    @staticmethod
    def initialize_default_roles(mongo):
        """Initialize default roles in database"""
        for role_name in Role.VALID_ROLES:
            description_map = {
                Role.ROLE_ADMIN: 'Administrator with full access to all functions',
                Role.ROLE_REVIEWER: 'Document reviewer with access to public documents only',
                Role.ROLE_TEACHER: 'Teacher with access to public and private documents'
            }
            Role.create(mongo, role_name, description_map.get(role_name, ''))

    @staticmethod
    def get_permissions(mongo, role_name):
        """Get permissions for a role"""
        return Role.ROLE_PERMISSIONS.get(role_name, [])

    @staticmethod
    def has_permission(mongo, role_name, permission):
        """Check if role has a specific permission"""
        permissions = Role.get_permissions(mongo, role_name)
        return permission in permissions

    @staticmethod
    def to_dict(role):
        """Convert role document to dictionary"""
        if not role:
            return None

        return {
            'id': str(role['_id']),
            'name': role['name'],
            'description': role.get('description', ''),
            'permissions': role.get('permissions', []),
            'created_at': role['created_at'].isoformat() if role.get('created_at') else None
        }
