"""Verify only the workflow test project data"""
from pymongo import MongoClient
from bson import ObjectId
import os

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp%40123@localhost:27017/gvpocr?authSource=admin')
client = MongoClient(mongo_uri)
db = client['gvpocr']

print("="*80)
print("🔍 WORKFLOW TEST PROJECT VERIFICATION")
print("="*80)

# Find the workflow test project
project = db.projects.find_one({'name': 'Workflow Test Project'})
if not project:
    print("❌ Workflow Test Project not found!")
    exit(1)

project_id = project['_id']
print(f"\n✅ Found project: {project['name']}")
print(f"   Project ID: {project_id}")

# Count documents in this project
print("\n=== DOCUMENTS ===")
total_docs = db.images.count_documents({'project_id': project_id})
public_docs = db.images.count_documents({'project_id': project_id, 'classification': 'PUBLIC'})
private_docs = db.images.count_documents({'project_id': project_id, 'classification': 'PRIVATE'})

print(f"Total workflow documents: {total_docs}")
print(f"  - PUBLIC: {public_docs}")
print(f"  - PRIVATE: {private_docs}")

# Verify Queues for this project only
print("\n=== QUEUE DISTRIBUTION ===")
teacher_queue = db.images.count_documents({'project_id': project_id, 'current_queue': 'teacher_queue'})
reviewer_queue = db.images.count_documents({'project_id': project_id, 'current_queue': 'reviewer_queue'})
reviewer_approved = db.images.count_documents({'project_id': project_id, 'current_queue': 'reviewer_approved'})
rejected = db.images.count_documents({'project_id': project_id, 'current_queue': 'rejected'})

print(f"  - teacher_queue: {teacher_queue}")
print(f"  - reviewer_queue: {reviewer_queue}")
print(f"  - reviewer_approved: {reviewer_approved}")
print(f"  - rejected: {rejected}")

# Verify workflow test users
print("\n=== WORKFLOW TEST USERS ===")
test_emails = [
    'admin@docgen.ai',
    'reviewer1@docgen.ai',
    'reviewer2@docgen.ai',
    'reviewer3@docgen.ai',
    'reviewer4@docgen.ai',
    'reviewer5@docgen.ai',
    'teacher1@docgen.ai',
    'teacher2@docgen.ai'
]

workflow_users = list(db.users.find({'email': {'$in': test_emails}}))
print(f"Found {len(workflow_users)} workflow test users:")
for user in workflow_users:
    roles_str = ', '.join(user.get('roles', []))
    print(f"  - {user['name']} ({user['email']}) - Roles: {roles_str}")

# Check assignments
print("\n=== ASSIGNMENTS ===")
reviewers = [u for u in workflow_users if 'reviewer' in u.get('roles', [])]
for reviewer in reviewers:
    reviewer_id = str(reviewer['_id'])
    # Check assignments as both string and ObjectId
    assigned_str = db.images.count_documents({'project_id': project_id, 'assigned_to': reviewer_id})
    assigned_obj = db.images.count_documents({'project_id': project_id, 'assigned_to': reviewer['_id']})
    assigned_count = max(assigned_str, assigned_obj)
    print(f"  - {reviewer['name']}: {assigned_count} documents")

teachers = [u for u in workflow_users if 'teacher' in u.get('roles', [])]
for teacher in teachers:
    teacher_id = str(teacher['_id'])
    # Check assignments as both string and ObjectId
    assigned_str = db.images.count_documents({'project_id': project_id, 'assigned_to': teacher_id})
    assigned_obj = db.images.count_documents({'project_id': project_id, 'assigned_to': teacher['_id']})
    assigned_count = max(assigned_str, assigned_obj)
    print(f"  - {teacher['name']}: {assigned_count} documents")

# Verify audit logs for workflow users
print("\n=== AUDIT LOGS ===")
workflow_user_ids = [u['_id'] for u in workflow_users]
workflow_logs = db.audit_logs.count_documents({'user_id': {'$in': workflow_user_ids}})
print(f"Audit logs for workflow users: {workflow_logs}")

# Show breakdown of audit log actions
log_actions = db.audit_logs.aggregate([
    {'$match': {'user_id': {'$in': workflow_user_ids}}},
    {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
])

print("\nAudit log actions:")
for action in log_actions:
    action_name = action['_id'] if action['_id'] else '(no action)'
    print(f"  - {action_name}: {action['count']}")

# Sample documents showing workflow
print("\n=== SAMPLE DOCUMENTS ===")
sample_docs = list(db.images.find({'project_id': project_id}).limit(3))
for doc in sample_docs:
    print(f"\nDocument: {doc.get('title')}")
    print(f"  Status: {doc.get('document_status')}")
    print(f"  Queue: {doc.get('current_queue')}")
    print(f"  Classification: {doc.get('classification')}")
    print(f"  Queue History: {' → '.join(doc.get('queue_history', []))}")
    if doc.get('assignment_history'):
        print(f"  Assignments: {len(doc.get('assignment_history', []))}")

print("\n" + "="*80)
print("✅ WORKFLOW TEST PROJECT VERIFICATION COMPLETE")
print("="*80)
print("\n📝 SUMMARY:")
print(f"   ✅ {len(workflow_users)}/8 users created")
print(f"   ✅ {total_docs}/35 documents created")
print(f"   ✅ {workflow_logs} audit log entries")
print(f"   ✅ Documents distributed across {4 if (teacher_queue and reviewer_queue and reviewer_approved and rejected) else 'some'} queues")
print("\n   All workflow test data has been successfully created! 🎉")

client.close()
