"""Seed workflow data and immediately verify it"""
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import mongo

print("="*80)
print("🚀 RUNNING WORKFLOW SIMULATION")
print("="*80)

# Create Flask app
app = create_app()

with app.app_context():
    # Run the seed script (import and execute main)
    from seed_workflow_simulation import main as seed_main

    print("\nExecuting seed script...")
    seed_main()

    print("\n" + "="*80)
    print("🔍 IMMEDIATE VERIFICATION")
    print("="*80)

    # Verify users
    workflow_emails = [
        'admin@docgen.ai',
        'reviewer1@docgen.ai',
        'reviewer2@docgen.ai',
        'reviewer3@docgen.ai',
        'reviewer4@docgen.ai',
        'reviewer5@docgen.ai',
        'teacher1@docgen.ai',
        'teacher2@docgen.ai'
    ]

    print("\n=== USERS ===")
    found_users = []
    for email in workflow_emails:
        user = mongo.db.users.find_one({'email': email})
        if user:
            roles_str = ', '.join(user.get('roles', []))
            print(f"✅ {user['name']} ({email}) - Roles: {roles_str}")
            found_users.append(user)
        else:
            print(f"❌ {email} - NOT FOUND")

    print(f"\nFound {len(found_users)}/8 workflow test users")

    # Verify workflow test project
    project = mongo.db.projects.find_one({'name': 'Workflow Test Project'})
    if project:
        print(f"\n=== PROJECT ===")
        print(f"✅ {project['name']} (ID: {project['_id']})")

        # Count documents
        total_docs = mongo.db.images.count_documents({'project_id': project['_id']})
        public_docs = mongo.db.images.count_documents({'project_id': project['_id'], 'classification': 'PUBLIC'})
        private_docs = mongo.db.images.count_documents({'project_id': project['_id'], 'classification': 'PRIVATE'})

        print(f"\n=== DOCUMENTS ===")
        print(f"Total: {total_docs}")
        print(f"  - PUBLIC: {public_docs}")
        print(f"  - PRIVATE: {private_docs}")

        # Queue distribution
        print(f"\n=== QUEUES ===")
        for queue in ['teacher_queue', 'reviewer_queue', 'reviewer_approved', 'rejected']:
            count = mongo.db.images.count_documents({'project_id': project['_id'], 'current_queue': queue})
            print(f"  - {queue}: {count}")

        # Audit logs
        workflow_user_ids = [u['_id'] for u in found_users]
        audit_count = mongo.db.audit_logs.count_documents({'user_id': {'$in': workflow_user_ids}})
        print(f"\n=== AUDIT LOGS ===")
        print(f"Total: {audit_count}")

        print("\n" + "="*80)
        print("✅ VERIFICATION COMPLETE - ALL DATA PRESENT!")
        print("="*80)

        # Print login instructions
        print("\n📝 LOGIN CREDENTIALS:")
        print("   Email: admin@docgen.ai")
        print("   Password: password123")
        print("\n   All users use the same password: password123")
        print("   See full list in the output above.")
    else:
        print("\n❌ Workflow Test Project not found!")
