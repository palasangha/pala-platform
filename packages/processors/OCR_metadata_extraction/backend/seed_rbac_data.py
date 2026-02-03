"""
Seed script to populate RBAC test data for DocGen AI
This script creates:
- Sample users with different roles (admin, reviewer, teacher)
- Sample documents with various statuses
- Sample audit log entries
- Sample projects

Usage: python seed_rbac_data.py
"""

import sys
import os
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import mongo
from app.models.user import User
from app.models.role import Role
from app.models.image import Image
from app.models.audit_log import AuditLog
from app import create_app

def clear_existing_data(mongo_db):
    """Clear existing test data"""
    print("🗑️  Clearing existing test data...")

    # Don't delete users with real emails, only test users
    mongo_db.users.delete_many({'email': {'$regex': '^test'}})

    # Clear all images from test project
    test_projects = list(mongo_db.projects.find({'name': {'$regex': 'Test Project'}}))
    if test_projects:
        project_ids = [p['_id'] for p in test_projects]
        mongo_db.images.delete_many({'project_id': {'$in': project_ids}})
        mongo_db.projects.delete_many({'_id': {'$in': project_ids}})

    print("✅ Cleared existing test data")


def create_test_users(mongo_db):
    """Create test users with different roles"""
    print("\n👥 Creating test users...")

    users = [
        {
            'email': 'test.admin@docgen.ai',
            'password': 'admin123',
            'name': 'Test Admin',
            'roles': ['admin']
        },
        {
            'email': 'test.reviewer1@docgen.ai',
            'password': 'reviewer123',
            'name': 'Test Reviewer 1',
            'roles': ['reviewer']
        },
        {
            'email': 'test.reviewer2@docgen.ai',
            'password': 'reviewer123',
            'name': 'Test Reviewer 2',
            'roles': ['reviewer']
        },
        {
            'email': 'test.teacher@docgen.ai',
            'password': 'teacher123',
            'name': 'Test Teacher',
            'roles': ['teacher']
        }
    ]

    created_users = {}

    for user_data in users:
        # Check if user already exists
        existing_user = User.find_by_email(mongo_db, user_data['email'])
        if existing_user:
            print(f"   User {user_data['email']} already exists, skipping...")
            created_users[user_data['email']] = existing_user
            continue

        # Create user
        user_id = User.create(
            mongo_db,
            email=user_data['email'],
            password=user_data['password'],
            name=user_data['name']
        )

        # Set roles
        User.set_roles(mongo_db, str(user_id), user_data['roles'])

        # Get created user
        user = User.find_by_id(mongo_db, str(user_id))
        created_users[user_data['email']] = user

        # Create login audit log
        AuditLog.create(
            mongo_db,
            str(user_id),
            AuditLog.ACTION_USER_REGISTER,
            details={'email': user_data['email'], 'roles': user_data['roles']}
        )

        print(f"   ✅ Created user: {user_data['name']} ({user_data['email']}) - Roles: {', '.join(user_data['roles'])}")

    return created_users


def create_test_project(mongo_db):
    """Create a test project"""
    print("\n📁 Creating test project...")

    project_data = {
        'name': 'Test Project - RBAC Demo',
        'description': 'Test project for RBAC system validation',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

    result = mongo_db.projects.insert_one(project_data)
    project_id = result.inserted_id

    print(f"   ✅ Created project: {project_data['name']} (ID: {project_id})")

    return project_id


def create_test_documents(mongo_db, project_id, users):
    """Create test documents with various statuses"""
    print("\n📄 Creating test documents...")

    admin_id = str(users['test.admin@docgen.ai']['_id'])
    reviewer1_id = str(users['test.reviewer1@docgen.ai']['_id'])
    reviewer2_id = str(users['test.reviewer2@docgen.ai']['_id'])
    teacher_id = str(users['test.teacher@docgen.ai']['_id'])

    # Document templates with different statuses
    document_templates = [
        # Uploaded documents (5)
        *[{
            'original_filename': f'invoice_{i:03d}.pdf',
            'classification': None,
            'document_status': Image.STATUS_UPLOADED,
            'review_status': None,
        } for i in range(1, 6)],

        # Classification pending (3)
        *[{
            'original_filename': f'receipt_{i:03d}.pdf',
            'classification': None,
            'document_status': Image.STATUS_CLASSIFICATION_PENDING,
            'review_status': None,
        } for i in range(1, 4)],

        # Classified PUBLIC documents (10)
        *[{
            'original_filename': f'public_doc_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PUBLIC,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=random.randint(1, 5)),
            'document_status': Image.STATUS_CLASSIFIED,
            'review_status': None,
        } for i in range(1, 11)],

        # Classified PRIVATE documents (5)
        *[{
            'original_filename': f'private_doc_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PRIVATE,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=random.randint(1, 5)),
            'document_status': Image.STATUS_CLASSIFIED,
            'review_status': None,
        } for i in range(1, 6)],

        # OCR Processed - awaiting review (8)
        *[{
            'original_filename': f'processed_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PUBLIC if i % 2 == 0 else Image.CLASSIFICATION_PRIVATE,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=3),
            'document_status': Image.STATUS_OCR_PROCESSED,
            'ocr_status': 'completed',
            'ocr_processed_at': datetime.utcnow() - timedelta(days=2),
            'ocr_text': f'Sample OCR text for document {i}',
            'review_status': None,
        } for i in range(1, 9)],

        # In Review - claimed by reviewer1 (6)
        *[{
            'original_filename': f'in_review_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PUBLIC,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=4),
            'document_status': Image.STATUS_IN_REVIEW,
            'ocr_status': 'completed',
            'ocr_processed_at': datetime.utcnow() - timedelta(days=3),
            'claimed_by': ObjectId(reviewer1_id),
            'claimed_at': datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            'review_status': 'in_review',
        } for i in range(1, 7)],

        # Approved documents (12)
        *[{
            'original_filename': f'approved_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PUBLIC if i % 3 != 0 else Image.CLASSIFICATION_PRIVATE,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=6),
            'document_status': Image.STATUS_REVIEWED_APPROVED,
            'ocr_status': 'completed',
            'ocr_processed_at': datetime.utcnow() - timedelta(days=5),
            'claimed_by': ObjectId(reviewer1_id if i % 2 == 0 else reviewer2_id),
            'claimed_at': datetime.utcnow() - timedelta(days=4, hours=random.randint(1, 24)),
            'reviewed_by': ObjectId(reviewer1_id if i % 2 == 0 else reviewer2_id),
            'reviewed_at': datetime.utcnow() - timedelta(days=3, hours=random.randint(1, 24)),
            'review_status': 'approved',
            'review_notes': f'Approved - document quality is good',
            'manual_edits': [] if i % 4 != 0 else [{'field': 'total_amount', 'value': '1234.56'}],
        } for i in range(1, 13)],

        # Rejected documents (4)
        *[{
            'original_filename': f'rejected_{i:03d}.pdf',
            'classification': Image.CLASSIFICATION_PUBLIC,
            'classified_by': ObjectId(admin_id),
            'classified_at': datetime.utcnow() - timedelta(days=5),
            'document_status': Image.STATUS_IN_REVIEW,
            'ocr_status': 'completed',
            'ocr_processed_at': datetime.utcnow() - timedelta(days=4),
            'claimed_by': None,  # Rejected documents are unclaimed
            'claimed_at': None,
            'review_status': 'rejected',
            'rejection_reason': 'OCR quality too low, needs reprocessing',
        } for i in range(1, 5)],
    ]

    created_count = 0
    document_ids = []

    for template in document_templates:
        # Create base document
        doc_data = {
            'project_id': ObjectId(project_id),
            'filename': f'file_{ObjectId()}.pdf',
            'filepath': f'/uploads/{template["original_filename"]}',
            'original_filename': template['original_filename'],
            'file_type': 'pdf',
            'ocr_text': template.get('ocr_text'),
            'ocr_status': template.get('ocr_status', 'pending'),
            'ocr_processed_at': template.get('ocr_processed_at'),
            'classification': template.get('classification'),
            'document_status': template['document_status'],
            'classified_by': template.get('classified_by'),
            'classified_at': template.get('classified_at'),
            'classification_reason': template.get('classification_reason'),
            'claimed_by': template.get('claimed_by'),
            'claimed_at': template.get('claimed_at'),
            'review_status': template.get('review_status'),
            'reviewed_by': template.get('reviewed_by'),
            'reviewed_at': template.get('reviewed_at'),
            'manual_edits': template.get('manual_edits', []),
            'review_notes': template.get('review_notes'),
            'rejection_reason': template.get('rejection_reason'),
            'enrichment_data': None,
            'enrichment_status': 'pending',
            'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 7)),
            'updated_at': datetime.utcnow()
        }

        result = mongo_db.images.insert_one(doc_data)
        document_ids.append(result.inserted_id)
        created_count += 1

    print(f"   ✅ Created {created_count} test documents")
    print(f"      - Uploaded: 5")
    print(f"      - Classification Pending: 3")
    print(f"      - Classified: 15 (10 PUBLIC, 5 PRIVATE)")
    print(f"      - OCR Processed: 8")
    print(f"      - In Review: 6")
    print(f"      - Approved: 12")
    print(f"      - Rejected: 4")

    return document_ids


def create_audit_logs(mongo_db, users, document_ids):
    """Create sample audit logs for various actions"""
    print("\n📋 Creating audit log entries...")

    admin_id = str(users['test.admin@docgen.ai']['_id'])
    reviewer1_id = str(users['test.reviewer1@docgen.ai']['_id'])
    reviewer2_id = str(users['test.reviewer2@docgen.ai']['_id'])
    teacher_id = str(users['test.teacher@docgen.ai']['_id'])

    audit_entries = [
        # User logins
        (reviewer1_id, AuditLog.ACTION_USER_LOGIN, None, None, {'ip_address': '192.168.1.100'}, 1),
        (reviewer2_id, AuditLog.ACTION_USER_LOGIN, None, None, {'ip_address': '192.168.1.101'}, 1),
        (teacher_id, AuditLog.ACTION_USER_LOGIN, None, None, {'ip_address': '192.168.1.102'}, 2),
        (admin_id, AuditLog.ACTION_USER_LOGIN, None, None, {'ip_address': '192.168.1.103'}, 1),

        # Document classifications (10 entries)
        *[(admin_id, AuditLog.ACTION_CLASSIFY_DOCUMENT, 'document', str(doc_id),
           {'classification': 'PUBLIC', 'reason': 'No sensitive data'},
           random.randint(3, 6)) for doc_id in document_ids[:10]],

        # Document claims (15 entries)
        *[(reviewer1_id, AuditLog.ACTION_CLAIM_DOCUMENT, 'document', str(doc_id),
           {'claimed_at': (datetime.utcnow() - timedelta(days=2)).isoformat()},
           random.randint(2, 4)) for doc_id in document_ids[20:28]],

        # Document approvals (12 entries)
        *[(reviewer1_id if i % 2 == 0 else reviewer2_id,
           AuditLog.ACTION_APPROVE_DOCUMENT, 'document', str(doc_id),
           {'notes': 'Approved after review', 'manual_edits': 0 if i % 4 == 0 else 1},
           random.randint(1, 3)) for i, doc_id in enumerate(document_ids[30:42])],

        # Document rejections (4 entries)
        *[(reviewer2_id, AuditLog.ACTION_REJECT_DOCUMENT, 'document', str(doc_id),
           {'reason': 'OCR quality issues, needs reprocessing'},
           random.randint(1, 3)) for doc_id in document_ids[42:46]],

        # Role assignments
        (admin_id, AuditLog.ACTION_ROLES_UPDATED, 'user', reviewer1_id,
         {'previous_roles': [], 'new_roles': ['reviewer']}, 7),
        (admin_id, AuditLog.ACTION_ROLES_UPDATED, 'user', teacher_id,
         {'previous_roles': ['reviewer'], 'new_roles': ['teacher']}, 6),

        # Document assignments
        (admin_id, AuditLog.ACTION_DOCUMENT_ASSIGNED, 'document', str(document_ids[0]),
         {'assigned_to': reviewer1_id, 'assigned_to_email': 'test.reviewer1@docgen.ai'}, 5),
    ]

    created_count = 0
    for entry in audit_entries:
        user_id, action_type, resource_type, resource_id, details, days_ago = entry

        log_data = {
            'user_id': ObjectId(user_id) if user_id else None,
            'action_type': action_type,
            'resource_type': resource_type,
            'resource_id': ObjectId(resource_id) if resource_id else None,
            'previous_state': None,
            'new_state': None,
            'details': details,
            'ip_address': details.get('ip_address'),
            'user_agent': 'Mozilla/5.0 (Test Browser)',
            'created_at': datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
            'timestamp': datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
        }

        mongo_db.audit_logs.insert_one(log_data)
        created_count += 1

    print(f"   ✅ Created {created_count} audit log entries")
    print(f"      - User logins: 4")
    print(f"      - Document classifications: 10")
    print(f"      - Document claims: 8")
    print(f"      - Document approvals: 12")
    print(f"      - Document rejections: 4")
    print(f"      - Role updates: 2")
    print(f"      - Document assignments: 1")


def print_summary(mongo_db, users):
    """Print summary of created data"""
    print("\n" + "="*80)
    print("✅ SEED DATA CREATION COMPLETE")
    print("="*80)

    print("\n📊 Summary:")
    print(f"   Users: {len(users)}")
    print(f"   Projects: {mongo_db.projects.count_documents({'name': {'$regex': 'Test Project'}})}")
    print(f"   Documents: {mongo_db.images.count_documents({})}")
    print(f"   Audit Logs: {mongo_db.audit_logs.count_documents({})}")

    print("\n👥 Test User Credentials:")
    print("   ┌─────────────────────────────────────────────────────────────┐")
    print("   │ Admin:                                                      │")
    print("   │   Email: test.admin@docgen.ai                               │")
    print("   │   Password: admin123                                        │")
    print("   ├─────────────────────────────────────────────────────────────┤")
    print("   │ Reviewer 1:                                                 │")
    print("   │   Email: test.reviewer1@docgen.ai                           │")
    print("   │   Password: reviewer123                                     │")
    print("   ├─────────────────────────────────────────────────────────────┤")
    print("   │ Reviewer 2:                                                 │")
    print("   │   Email: test.reviewer2@docgen.ai                           │")
    print("   │   Password: reviewer123                                     │")
    print("   ├─────────────────────────────────────────────────────────────┤")
    print("   │ Teacher:                                                    │")
    print("   │   Email: test.teacher@docgen.ai                             │")
    print("   │   Password: teacher123                                      │")
    print("   └─────────────────────────────────────────────────────────────┘")

    print("\n🧪 Testing Instructions:")
    print("   1. Login as admin to see full dashboard with all metrics")
    print("   2. Check admin dashboard at /rbac/admin-dashboard")
    print("   3. Check review queue at /rbac/review-queue")
    print("   4. Check audit logs at /rbac/audit-logs")
    print("   5. Verify file names appear in review queue")
    print("   6. Test claiming, approving, and rejecting documents")
    print("   7. Verify audit logs are recording all actions")

    print("\n🔍 Expected Dashboard Metrics:")
    print("   - Total Documents: 53")
    print("   - In Review: 6")
    print("   - Approved: 12")
    print("   - Rejected: 4")
    print("   - Pending: 8 (5 uploaded + 3 classification pending)")
    print("   - Average Review Time: Should show calculated time in minutes")

    print("\n" + "="*80)


def main():
    """Main seeding function"""
    print("\n" + "="*80)
    print("🌱 RBAC SEED DATA SCRIPT")
    print("="*80)

    # Create Flask app and initialize MongoDB
    app = create_app()

    with app.app_context():
        # Clear existing test data
        clear_existing_data(mongo.db)

        # Create test users
        users = create_test_users(mongo.db)

        # Create test project
        project_id = create_test_project(mongo.db)

        # Create test documents
        document_ids = create_test_documents(mongo.db, project_id, users)

        # Create audit logs
        create_audit_logs(mongo.db, users, document_ids)

        # Print summary
        print_summary(mongo.db, users)


if __name__ == '__main__':
    main()
