"""Quick script to verify seed data in MongoDB"""
from pymongo import MongoClient
import os

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp%40123@localhost:27017/gvpocr?authSource=admin')
client = MongoClient(mongo_uri)
db = client['gvpocr']

print("="*80)
print("🔍 SEED DATA VERIFICATION")
print("="*80)

# Verify Users
print("\n=== USERS ===")
total_users = db.users.count_documents({})
admins = db.users.count_documents({'roles': 'admin'})
reviewers = db.users.count_documents({'roles': 'reviewer'})
teachers = db.users.count_documents({'roles': 'teacher'})

print(f"Total users: {total_users}")
print(f"  - Admins: {admins}")
print(f"  - Reviewers: {reviewers}")
print(f"  - Teachers: {teachers}")

# Verify Documents
print("\n=== DOCUMENTS ===")
total_docs = db.images.count_documents({})
public_docs = db.images.count_documents({'classification': 'PUBLIC'})
private_docs = db.images.count_documents({'classification': 'PRIVATE'})

print(f"Total documents: {total_docs}")
print(f"  - PUBLIC: {public_docs}")
print(f"  - PRIVATE: {private_docs}")

# Verify Queues
print("\n=== QUEUE DISTRIBUTION ===")
teacher_queue = db.images.count_documents({'current_queue': 'teacher_queue'})
reviewer_queue = db.images.count_documents({'current_queue': 'reviewer_queue'})
reviewer_approved = db.images.count_documents({'current_queue': 'reviewer_approved'})
rejected = db.images.count_documents({'current_queue': 'rejected'})

print(f"  - teacher_queue: {teacher_queue}")
print(f"  - reviewer_queue: {reviewer_queue}")
print(f"  - reviewer_approved: {reviewer_approved}")
print(f"  - rejected: {rejected}")

# Verify Assignments
print("\n=== ASSIGNMENTS ===")
reviewer_users = list(db.users.find({'roles': 'reviewer'}))
for user in reviewer_users:
    user_id = str(user['_id'])
    assigned_count = db.images.count_documents({'assigned_to': user_id})
    print(f"  - {user['name']}: {assigned_count} documents")

teacher_users = list(db.users.find({'roles': 'teacher'}))
for user in teacher_users:
    user_id = str(user['_id'])
    assigned_count = db.images.count_documents({'assigned_to': user_id})
    print(f"  - {user['name']}: {assigned_count} documents")

# Verify Audit Logs
print("\n=== AUDIT LOGS ===")
total_logs = db.audit_logs.count_documents({})
print(f"Total audit logs: {total_logs}")

# Sample a few audit log types
log_types = db.audit_logs.aggregate([
    {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}},
    {'$limit': 10}
])

print("\nTop audit log actions:")
for log_type in log_types:
    print(f"  - {log_type['_id']}: {log_type['count']}")

# Verify sample document
print("\n=== SAMPLE DOCUMENT ===")
sample_doc = db.images.find_one({'current_queue': 'reviewer_approved'})
if sample_doc:
    print(f"Title: {sample_doc.get('title')}")
    print(f"Classification: {sample_doc.get('classification')}")
    print(f"Document Status: {sample_doc.get('document_status')}")
    print(f"Current Queue: {sample_doc.get('current_queue')}")
    print(f"Queue History: {sample_doc.get('queue_history', [])}")
    print(f"Assignment History: {len(sample_doc.get('assignment_history', []))} assignments")

print("\n" + "="*80)
print("✅ VERIFICATION COMPLETE")
print("="*80)

client.close()
