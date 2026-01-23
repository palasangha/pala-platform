"""
Migration 001: Add RBAC fields to existing collections
- Add roles field to users collection
- Add classification and review fields to images collection
- Create audit_logs collection
- Create roles collection with default roles
"""

from datetime import datetime
from bson import ObjectId
import pymongo


def upgrade(mongo):
    """Apply migration"""
    print("Starting Migration 001: Add RBAC fields...")

    # ========================================================================
    # 1. Create/Update Users Collection
    # ========================================================================
    print("  • Updating users collection...")

    # Add roles field to existing users (default: 'reviewer')
    users_result = mongo.db.users.update_many(
        {'roles': {'$exists': False}},
        {
            '$set': {
                'roles': ['reviewer'],
                'is_active': True,
                'updated_at': datetime.utcnow()
            }
        }
    )
    print(f"    ✓ Added roles field to {users_result.modified_count} users")

    # Create index for users
    mongo.db.users.create_index([('email', pymongo.ASCENDING)], unique=True)
    mongo.db.users.create_index([('roles', pymongo.ASCENDING)])
    print("    ✓ Created indexes for users collection")

    # ========================================================================
    # 2. Create/Update Images Collection
    # ========================================================================
    print("  • Updating images collection...")

    # Add RBAC fields to existing images
    images_result = mongo.db.images.update_many(
        {'classification': {'$exists': False}},
        {
            '$set': {
                'classification': None,  # PUBLIC or PRIVATE
                'document_status': 'UPLOADED',
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
                'updated_at': datetime.utcnow()
            }
        }
    )
    print(f"    ✓ Added RBAC fields to {images_result.modified_count} images")

    # Create indexes for images
    mongo.db.images.create_index([('classification', pymongo.ASCENDING)])
    mongo.db.images.create_index([('document_status', pymongo.ASCENDING)])
    mongo.db.images.create_index([('claimed_by', pymongo.ASCENDING)])
    mongo.db.images.create_index([('project_id', pymongo.ASCENDING), ('document_status', pymongo.ASCENDING)])
    mongo.db.images.create_index([('created_at', pymongo.DESCENDING)])
    print("    ✓ Created indexes for images collection")

    # ========================================================================
    # 3. Create Roles Collection
    # ========================================================================
    print("  • Creating roles collection...")

    roles_data = [
        {
            'name': 'admin',
            'description': 'Administrator with full access to all functions',
            'permissions': [
                'classify_document',
                'run_ocr',
                'view_public_queue',
                'view_private_queue',
                'claim_document',
                'approve_document',
                'reject_document',
                'view_dashboard',
                'view_audit_logs',
                'export_documents',
                'manage_users',
                'manage_roles'
            ],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': 'reviewer',
            'description': 'Document reviewer with access to public documents only',
            'permissions': [
                'view_public_queue',
                'claim_document',
                'approve_document',
                'reject_document'
            ],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'name': 'teacher',
            'description': 'Teacher with access to public and private documents',
            'permissions': [
                'view_public_queue',
                'view_private_queue',
                'claim_document',
                'approve_document',
                'reject_document'
            ],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]

    for role_data in roles_data:
        mongo.db.roles.update_one(
            {'name': role_data['name']},
            {'$set': role_data},
            upsert=True
        )

    print(f"    ✓ Created/updated {len(roles_data)} roles")

    # Create index for roles
    mongo.db.roles.create_index([('name', pymongo.ASCENDING)], unique=True)
    print("    ✓ Created indexes for roles collection")

    # ========================================================================
    # 4. Create Audit Logs Collection
    # ========================================================================
    print("  • Creating audit_logs collection...")

    # Create capped collection for audit logs (10GB, max 10 million docs)
    try:
        mongo.db.create_collection(
            'audit_logs',
            capped=True,
            size=10 * 1024 * 1024 * 1024,  # 10GB
            max=10000000  # 10 million documents
        )
        print("    ✓ Created capped audit_logs collection (10GB, 10M max docs)")
    except Exception as e:
        # Collection might already exist
        if 'already exists' in str(e):
            print("    • audit_logs collection already exists")
        else:
            print(f"    ⚠ Warning: Could not create capped collection: {e}")

    # Create indexes for audit_logs
    mongo.db.audit_logs.create_index([('user_id', pymongo.ASCENDING)])
    mongo.db.audit_logs.create_index([('resource_type', pymongo.ASCENDING), ('resource_id', pymongo.ASCENDING)])
    mongo.db.audit_logs.create_index([('action_type', pymongo.ASCENDING)])
    mongo.db.audit_logs.create_index([('created_at', pymongo.DESCENDING)])
    print("    ✓ Created indexes for audit_logs collection")

    print("\n✓ Migration 001 completed successfully!")


def downgrade(mongo):
    """Rollback migration"""
    print("Rolling back Migration 001...")

    # Remove RBAC fields from images
    mongo.db.images.update_many(
        {},
        {
            '$unset': {
                'classification': '',
                'document_status': '',
                'classified_by': '',
                'classified_at': '',
                'classification_reason': '',
                'claimed_by': '',
                'claimed_at': '',
                'review_status': '',
                'reviewed_by': '',
                'reviewed_at': '',
                'manual_edits': '',
                'review_notes': '',
                'rejection_reason': ''
            }
        }
    )
    print("  ✓ Removed RBAC fields from images")

    # Remove roles field from users
    mongo.db.users.update_many(
        {},
        {'$unset': {'roles': '', 'is_active': ''}}
    )
    print("  ✓ Removed roles field from users")

    # Drop audit_logs collection
    try:
        mongo.db.audit_logs.drop()
        print("  ✓ Dropped audit_logs collection")
    except:
        pass

    # Drop roles collection
    try:
        mongo.db.roles.drop()
        print("  ✓ Dropped roles collection")
    except:
        pass

    print("\n✓ Migration 001 rolled back successfully!")
