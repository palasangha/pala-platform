"""List all users in the database"""
from pymongo import MongoClient
import os

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp%40123@localhost:27017/gvpocr?authSource=admin')
client = MongoClient(mongo_uri)
db = client['gvpocr']

print("="*80)
print("👥 ALL USERS IN DATABASE")
print("="*80)

users = list(db.users.find({}))
print(f"\nTotal users: {len(users)}")

for user in users:
    roles_str = ', '.join(user.get('roles', []))
    created_at = user.get('created_at', 'N/A')
    print(f"\n{user['name']} ({user['email']})")
    print(f"  ID: {user['_id']}")
    print(f"  Roles: {roles_str}")
    print(f"  Created: {created_at}")

# Check if workflow users were recently created
print("\n" + "="*80)
print("🔍 CHECKING FOR WORKFLOW TEST USERS")
print("="*80)

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

for email in workflow_emails:
    user = db.users.find_one({'email': email})
    if user:
        print(f"✅ {email} - FOUND")
    else:
        print(f"❌ {email} - NOT FOUND")

client.close()
