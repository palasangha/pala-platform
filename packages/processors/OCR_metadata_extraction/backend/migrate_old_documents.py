"""
Migrate old documents to add required RBAC fields

This script updates old documents that are missing:
- document_status
- classification
- created_by
- title
- other workflow fields

After running this, old documents will be accessible in the UI and can go through the RBAC workflow.
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# Connect to MongoDB
mongo_uri = os.getenv('MONGO_URI', 'mongodb://gvpocr_admin:gvp%40123@localhost:27017/gvpocr?authSource=admin')
client = MongoClient(mongo_uri)
db = client['gvpocr']

print("="*80)
print("🔄 MIGRATING OLD DOCUMENTS TO RBAC SCHEMA")
print("="*80)

# Find admin user to set as creator
admin_user = db.users.find_one({'email': 'admin@docgen.ai'})
if not admin_user:
    print("\n⚠️  No admin@docgen.ai user found. Using first admin user...")
    admin_user = db.users.find_one({'roles': 'admin'})

if not admin_user:
    print("\n❌ ERROR: No admin user found in database!")
    print("   Please create an admin user first.")
    exit(1)

admin_id = admin_user['_id']
print(f"\n✅ Using admin: {admin_user['name']} ({admin_user['email']})")

# Find documents missing RBAC fields
print("\n📋 Finding documents needing migration...")

# Query for documents missing key fields
migration_query = {
    '$or': [
        {'document_status': {'$exists': False}},
        {'document_status': None},
        {'classification': {'$exists': False}},
        {'classification': None}
    ]
}

docs_to_migrate = list(db.images.find(migration_query))
total_to_migrate = len(docs_to_migrate)

print(f"   Found {total_to_migrate} documents to migrate")

if total_to_migrate == 0:
    print("\n✅ All documents already have required fields!")
    client.close()
    exit(0)

# Show sample of what will be migrated
print("\n📄 Sample documents to migrate:")
for doc in docs_to_migrate[:3]:
    print(f"   - {doc.get('original_filename', doc.get('filename', 'Unknown'))}")
    print(f"     Missing: document_status={doc.get('document_status')}, classification={doc.get('classification')}")

# Ask for confirmation
print(f"\n⚠️  This will update {total_to_migrate} documents with:")
print("   - document_status: 'OCR_PROCESSED' (if OCR done) or 'UPLOADED'")
print("   - classification: 'PUBLIC' (default, can be changed later)")
print(f"   - created_by: {admin_user['email']}")
print("   - title: Based on original_filename")
print("   - Other required RBAC fields")

response = input("\nProceed with migration? (yes/no): ")
if response.lower() != 'yes':
    print("\n❌ Migration cancelled")
    client.close()
    exit(0)

# Perform migration
print("\n🔄 Migrating documents...")
migrated_count = 0
skipped_count = 0

for doc in docs_to_migrate:
    doc_id = doc['_id']

    # Determine document_status based on OCR status
    if doc.get('ocr_text') and doc.get('ocr_status') == 'completed':
        document_status = 'OCR_PROCESSED'
    else:
        document_status = 'UPLOADED'

    # Generate title from filename if missing
    title = doc.get('title')
    if not title:
        original_filename = doc.get('original_filename', doc.get('filename', 'Untitled'))
        # Remove extension and clean up
        title = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
        title = title.replace('_', ' ').replace('-', ' ').strip()

    # Build update document
    update_fields = {}

    # Add missing fields
    if not doc.get('document_status'):
        update_fields['document_status'] = document_status

    if not doc.get('classification'):
        update_fields['classification'] = 'PUBLIC'  # Default to PUBLIC, admin can reclassify

    if not doc.get('created_by'):
        update_fields['created_by'] = admin_id

    if not doc.get('title'):
        update_fields['title'] = title

    # Add other RBAC fields if missing
    if not doc.get('classified_by'):
        update_fields['classified_by'] = None

    if not doc.get('classified_at'):
        update_fields['classified_at'] = None

    if not doc.get('classification_reason'):
        update_fields['classification_reason'] = None

    # Review fields
    if not doc.get('claimed_by'):
        update_fields['claimed_by'] = None

    if not doc.get('claimed_at'):
        update_fields['claimed_at'] = None

    if not doc.get('review_status'):
        update_fields['review_status'] = None

    if not doc.get('reviewed_by'):
        update_fields['reviewed_by'] = None

    if not doc.get('reviewed_at'):
        update_fields['reviewed_at'] = None

    if 'manual_edits' not in doc:
        update_fields['manual_edits'] = []

    if not doc.get('review_notes'):
        update_fields['review_notes'] = None

    if not doc.get('rejection_reason'):
        update_fields['rejection_reason'] = None

    # Workflow fields
    if 'current_queue' not in doc:
        update_fields['current_queue'] = 'awaiting_classification' if not doc.get('classification') else 'ocr_complete'

    if 'queue_history' not in doc:
        update_fields['queue_history'] = ['upload']

    if 'assignment_history' not in doc:
        update_fields['assignment_history'] = []

    if not doc.get('assigned_to'):
        update_fields['assigned_to'] = None

    if not doc.get('assigned_by'):
        update_fields['assigned_by'] = None

    if not doc.get('assigned_at'):
        update_fields['assigned_at'] = None

    # Update timestamp
    update_fields['updated_at'] = datetime.utcnow()

    # Perform update
    try:
        result = db.images.update_one(
            {'_id': doc_id},
            {'$set': update_fields}
        )

        if result.modified_count > 0:
            migrated_count += 1
            if migrated_count % 10 == 0:
                print(f"   ✅ Migrated {migrated_count}/{total_to_migrate}...")
        else:
            skipped_count += 1
    except Exception as e:
        print(f"   ❌ Error migrating document {doc_id}: {e}")

print(f"\n✅ Migration complete!")
print(f"   Migrated: {migrated_count}")
print(f"   Skipped: {skipped_count}")

# Show updated status
print("\n📊 Updated document distribution:")
doc_statuses = db.images.aggregate([
    {'$group': {'_id': '$document_status', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
])
for status in doc_statuses:
    status_name = status['_id'] if status['_id'] else '(null/missing)'
    print(f"   - {status_name}: {status['count']}")

print("\n📋 Classification distribution:")
classifications = db.images.aggregate([
    {'$group': {'_id': '$classification', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
])
for classification in classifications:
    class_name = classification['_id'] if classification['_id'] else '(null/unclassified)'
    print(f"   - {class_name}: {classification['count']}")

print("\n" + "="*80)
print("✅ MIGRATION COMPLETE")
print("="*80)
print("\nNext steps:")
print("  1. Login as admin (admin@docgen.ai / password123)")
print("  2. Go to Document Classification page")
print("  3. Reclassify documents as PUBLIC or PRIVATE as needed")
print("  4. Assign documents to reviewers")
print("\nAll 110 documents should now be visible in the UI!")
print("="*80)

client.close()
