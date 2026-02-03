"""
Comprehensive RBAC Workflow Simulation Script
===============================================

Simulates realistic document review workflow with:
- 5 Reviewers
- 2 Teachers
- 35 Documents with workflow transitions
- Queue movements
- Assignment changes
- Complete audit trail

Usage: python3 seed_workflow_simulation.py
"""

import sys
import os
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash
import random
import json

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import mongo
from app.models.user import User
from app.models.role import Role
from app.models.image import Image
from app.models.audit_log import AuditLog
from app import create_app


# ============================================================================
# CONFIGURATION
# ============================================================================

REVIEWERS = [
    {'username': 'reviewer1', 'name': 'Alice Johnson', 'email': 'reviewer1@docgen.ai'},
    {'username': 'reviewer2', 'name': 'Bob Smith', 'email': 'reviewer2@docgen.ai'},
    {'username': 'reviewer3', 'name': 'Carol Williams', 'email': 'reviewer3@docgen.ai'},
    {'username': 'reviewer4', 'name': 'David Brown', 'email': 'reviewer4@docgen.ai'},
    {'username': 'reviewer5', 'name': 'Emma Davis', 'email': 'reviewer5@docgen.ai'},
]

TEACHERS = [
    {'username': 'teacher1', 'name': 'Prof. Michael Chen', 'email': 'teacher1@docgen.ai'},
    {'username': 'teacher2', 'name': 'Prof. Sarah Martinez', 'email': 'teacher2@docgen.ai'},
]

ADMIN = {'username': 'admin', 'name': 'System Admin', 'email': 'admin@docgen.ai'}

DEFAULT_PASSWORD = 'password123'

# Document templates
DOCUMENT_TYPES = [
    'Letter', 'Newsletter', 'Publication', 'Report', 'Memo',
    'Invoice', 'Contract', 'Form', 'Certificate', 'Notice'
]

SOURCE_TYPES = ['Scanned Document', 'Email Attachment', 'Web Upload', 'Mobile Capture', 'Bulk Import']


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clear_existing_workflow_data(mongo_db):
    """Clear existing workflow simulation data"""
    print("\n" + "="*80)
    print("🗑️  CLEARING EXISTING WORKFLOW DATA")
    print("="*80)

    # Delete workflow test users
    deleted_users = mongo_db.users.delete_many({
        'email': {'$in': [
            *[r['email'] for r in REVIEWERS],
            *[t['email'] for t in TEACHERS],
            ADMIN['email']
        ]}
    })

    # Delete workflow test project
    test_projects = list(mongo_db.projects.find({'name': 'Workflow Test Project'}))
    if test_projects:
        project_ids = [p['_id'] for p in test_projects]
        deleted_docs = mongo_db.images.delete_many({'project_id': {'$in': project_ids}})
        deleted_projects = mongo_db.projects.delete_many({'_id': {'$in': project_ids}})
        print(f"   ✅ Deleted {deleted_docs.deleted_count} documents")
        print(f"   ✅ Deleted {deleted_projects.deleted_count} projects")

    print(f"   ✅ Deleted {deleted_users.deleted_count} users")
    print("   ✅ Cleared workflow data")


def create_users(mongo):
    """Create admin, reviewers, and teachers"""
    print("\n" + "="*80)
    print("👥 CREATING USERS")
    print("="*80)

    users = {}

    # Create Admin
    print("\n📋 Creating Admin User...")
    admin_user = User.create(
        mongo,
        email=ADMIN['email'],
        password=DEFAULT_PASSWORD,
        name=ADMIN['name']
    )
    admin_id = str(admin_user['_id'])
    User.set_roles(mongo, admin_id, ['admin'])
    users['admin'] = User.find_by_id(mongo, admin_id)
    print(f"   ✅ {ADMIN['name']} ({ADMIN['email']}) - Role: admin")

    # Create audit log for admin creation
    AuditLog.create(
        mongo.db,
        admin_id,
        AuditLog.ACTION_USER_CREATED,
        details={'email': ADMIN['email'], 'role': 'admin'}
    )

    # Create Reviewers
    print("\n📋 Creating Reviewers...")
    for reviewer in REVIEWERS:
        reviewer_user = User.create(
            mongo,
            email=reviewer['email'],
            password=DEFAULT_PASSWORD,
            name=reviewer['name']
        )
        reviewer_id = str(reviewer_user['_id'])
        User.set_roles(mongo, reviewer_id, ['reviewer'])
        users[reviewer['username']] = User.find_by_id(mongo, reviewer_id)
        print(f"   ✅ {reviewer['name']} ({reviewer['email']}) - Role: reviewer")

        # Create audit log
        AuditLog.create(
            mongo.db,
            admin_id,
            AuditLog.ACTION_USER_CREATED,
            details={'email': reviewer['email'], 'role': 'reviewer'}
        )

    # Create Teachers
    print("\n📋 Creating Teachers...")
    for teacher in TEACHERS:
        teacher_user = User.create(
            mongo,
            email=teacher['email'],
            password=DEFAULT_PASSWORD,
            name=teacher['name']
        )
        teacher_id = str(teacher_user['_id'])
        User.set_roles(mongo, teacher_id, ['teacher'])
        users[teacher['username']] = User.find_by_id(mongo, teacher_id)
        print(f"   ✅ {teacher['name']} ({teacher['email']}) - Role: teacher")

        # Create audit log
        AuditLog.create(
            mongo.db,
            admin_id,
            AuditLog.ACTION_USER_CREATED,
            details={'email': teacher['email'], 'role': 'teacher'}
        )

    print(f"\n✅ Created {len(users)} users total")
    return users


def create_project(mongo_db):
    """Create workflow test project"""
    print("\n" + "="*80)
    print("📁 CREATING WORKFLOW TEST PROJECT")
    print("="*80)

    project_data = {
        'name': 'Workflow Test Project',
        'description': 'Comprehensive RBAC workflow simulation with 35 documents',
        'created_at': datetime.utcnow() - timedelta(days=30),
        'updated_at': datetime.utcnow()
    }

    result = mongo_db.projects.insert_one(project_data)
    project_id = result.inserted_id

    print(f"   ✅ Created project: {project_data['name']}")
    print(f"   📌 Project ID: {project_id}")

    return project_id


def create_documents(mongo_db, project_id, users):
    """Create 35 documents with realistic metadata"""
    print("\n" + "="*80)
    print("📄 CREATING 35 DOCUMENTS")
    print("="*80)

    admin_id = str(users['admin']['_id'])
    documents = []

    # Document title templates
    title_templates = [
        "Annual Report {year}",
        "Monthly Newsletter - {month}",
        "Customer Letter #{num}",
        "Product Catalog {quarter}",
        "Training Manual v{version}",
        "Financial Statement Q{quarter}",
        "Employee Handbook {year}",
        "Project Proposal #{num}",
        "Meeting Minutes {date}",
        "Policy Update Notice {num}",
        "Research Paper #{num}",
        "Marketing Brochure {season}",
        "Technical Specification {version}",
        "Service Agreement #{num}",
        "Compliance Report {month}",
        "Inventory List {date}",
        "Sales Report {quarter}",
        "Client Presentation {num}",
        "Audit Report {year}",
        "Safety Guidelines v{version}",
        "Operational Manual {num}",
        "Budget Proposal {year}",
        "Performance Review {quarter}",
        "Contract Amendment #{num}",
        "Certificate of Achievement {num}",
        "Work Order #{num}",
        "Purchase Order #{num}",
        "Delivery Note #{num}",
        "Quality Assurance Report {num}",
        "Strategic Plan {year}",
        "Executive Summary {quarter}",
        "Board Resolution #{num}",
        "Membership Application {num}",
        "Event Program {date}",
        "Press Release {date}"
    ]

    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    seasons = ['Spring', 'Summer', 'Fall', 'Winter']
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']

    print("\n📝 Generating document metadata...")

    for i in range(35):
        # Generate title
        template = title_templates[i]
        title = template.format(
            year=random.choice([2024, 2025, 2026]),
            month=random.choice(months),
            quarter=random.choice(quarters),
            season=random.choice(seasons),
            num=random.randint(1000, 9999),
            version=f"{random.randint(1, 5)}.{random.randint(0, 9)}",
            date=f"{random.randint(1, 28)}-{random.choice(months[:3])}"
        )

        # Generate filename
        filename_safe = title.lower().replace(' ', '_').replace('#', 'num').replace('/', '-')
        original_filename = f"{filename_safe}.pdf"

        # Document creation date (spread over last 30 days)
        created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))

        # Create document in "UPLOADED" state initially
        doc_data = {
            'project_id': ObjectId(project_id),
            'filename': f'file_{ObjectId()}.pdf',
            'filepath': f'/uploads/workflow_test/{original_filename}',
            'original_filename': original_filename,
            'title': title,
            'file_type': 'pdf',
            'source_type': random.choice(SOURCE_TYPES),
            'ocr_text': None,
            'ocr_status': 'pending',
            'ocr_processed_at': None,
            # Classification
            'classification': None,
            'document_status': Image.STATUS_UPLOADED,
            'classified_by': None,
            'classified_at': None,
            'classification_reason': None,
            # Review fields
            'claimed_by': None,
            'claimed_at': None,
            'review_status': None,
            'reviewed_by': None,
            'reviewed_at': None,
            'manual_edits': [],
            'review_notes': None,
            'rejection_reason': None,
            # Workflow tracking
            'current_queue': 'upload',
            'queue_history': ['upload'],
            'assignment_history': [],
            # Enrichment
            'enrichment_data': None,
            'enrichment_status': 'pending',
            'enriched_at': None,
            # Metadata
            'created_by': ObjectId(admin_id),
            'created_at': created_at,
            'updated_at': created_at
        }

        result = mongo_db.images.insert_one(doc_data)
        doc_data['_id'] = result.inserted_id
        documents.append(doc_data)

        # Create upload audit log
        AuditLog.create(
            mongo_db,
            admin_id,
            'DOCUMENT_UPLOADED',
            resource_type='document',
            resource_id=str(result.inserted_id),
            details={
                'title': title,
                'original_filename': original_filename,
                'source_type': doc_data['source_type']
            }
        )

    print(f"   ✅ Created {len(documents)} documents")
    print(f"   📊 Source types: {set([d['source_type'] for d in documents])}")

    return documents


def simulate_classification(mongo_db, documents, users):
    """Admin classifies all documents"""
    print("\n" + "="*80)
    print("🏷️  PHASE 1: CLASSIFICATION")
    print("="*80)

    admin_id = str(users['admin']['_id'])

    print("\n📋 Admin classifying documents...")

    for i, doc in enumerate(documents):
        # 70% PUBLIC, 30% PRIVATE
        classification = Image.CLASSIFICATION_PUBLIC if i % 10 < 7 else Image.CLASSIFICATION_PRIVATE

        classified_at = doc['created_at'] + timedelta(hours=random.randint(1, 12))

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'classification': classification,
                    'classified_by': ObjectId(admin_id),
                    'classified_at': classified_at,
                    'classification_reason': f'Classified as {classification}' + (
                        ' - contains sensitive information' if classification == Image.CLASSIFICATION_PRIVATE
                        else ' - public information'
                    ),
                    'document_status': Image.STATUS_CLASSIFIED,
                    'current_queue': 'classification_complete',
                    'updated_at': classified_at
                },
                '$push': {'queue_history': 'classification_complete'}
            }
        )

        # Update in-memory document
        doc['classification'] = classification
        doc['classified_by'] = ObjectId(admin_id)
        doc['classified_at'] = classified_at
        doc['document_status'] = Image.STATUS_CLASSIFIED
        doc['current_queue'] = 'classification_complete'

        # Create audit log
        AuditLog.create(
            mongo_db,
            admin_id,
            AuditLog.ACTION_CLASSIFY_DOCUMENT,
            resource_type='document',
            resource_id=str(doc['_id']),
            previous_state={'document_status': Image.STATUS_UPLOADED, 'classification': None},
            new_state={'document_status': Image.STATUS_CLASSIFIED, 'classification': classification},
            details={'classification': classification}
        )

        if (i + 1) % 10 == 0:
            print(f"   ✅ Classified {i + 1} documents...")

    print(f"\n   ✅ Classification complete: 35 documents")
    public_count = sum(1 for d in documents if d['classification'] == Image.CLASSIFICATION_PUBLIC)
    private_count = 35 - public_count
    print(f"   📊 PUBLIC: {public_count} | PRIVATE: {private_count}")


def simulate_ocr_processing(mongo_db, documents):
    """Simulate OCR processing"""
    print("\n" + "="*80)
    print("🔍 PHASE 2: OCR PROCESSING")
    print("="*80)

    print("\n⚙️  Processing OCR for all documents...")

    for i, doc in enumerate(documents):
        ocr_processed_at = doc['classified_at'] + timedelta(hours=random.randint(2, 24))

        # Generate sample OCR text
        ocr_text = f"[OCR Output for {doc['title']}]\n\nThis is simulated OCR text extracted from the document.\n" \
                   f"Document contains {random.randint(100, 500)} words.\n" \
                   f"Confidence score: {random.randint(85, 99)}%\n" \
                   f"Processed by OCR Engine v2.1"

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'ocr_text': ocr_text,
                    'ocr_status': 'completed',
                    'ocr_processed_at': ocr_processed_at,
                    'document_status': Image.STATUS_OCR_PROCESSED,
                    'current_queue': 'ocr_complete',
                    'updated_at': ocr_processed_at
                },
                '$push': {'queue_history': 'ocr_complete'}
            }
        )

        # Update in-memory document
        doc['ocr_text'] = ocr_text
        doc['ocr_status'] = 'completed'
        doc['ocr_processed_at'] = ocr_processed_at
        doc['document_status'] = Image.STATUS_OCR_PROCESSED
        doc['current_queue'] = 'ocr_complete'

        if (i + 1) % 10 == 0:
            print(f"   ✅ Processed {i + 1} documents...")

    print(f"\n   ✅ OCR processing complete: 35 documents")


def assign_to_reviewers(mongo_db, documents, users):
    """Assign 7 documents to each of 5 reviewers"""
    print("\n" + "="*80)
    print("👥 PHASE 3: REVIEWER ASSIGNMENT")
    print("="*80)

    admin_id = str(users['admin']['_id'])

    # Get reviewer IDs
    reviewer_ids = [str(users[f'reviewer{i+1}']['_id']) for i in range(5)]
    reviewer_names = [users[f'reviewer{i+1}']['name'] for i in range(5)]

    print("\n📋 Assigning documents to reviewers...")
    print("   Distribution: 7 documents per reviewer")

    # Assign 7 documents to each reviewer
    assignment_count = {}
    for i, doc in enumerate(documents):
        reviewer_index = i % 5  # Round-robin assignment
        reviewer_id = reviewer_ids[reviewer_index]
        reviewer_name = reviewer_names[reviewer_index]

        # Track assignment count
        if reviewer_id not in assignment_count:
            assignment_count[reviewer_id] = 0
        assignment_count[reviewer_id] += 1

        assigned_at = doc['ocr_processed_at'] + timedelta(hours=random.randint(1, 6))

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'assigned_to': reviewer_id,
                    'assigned_by': admin_id,
                    'assigned_at': assigned_at,
                    'current_queue': 'reviewer_queue',
                    'updated_at': assigned_at
                },
                '$push': {
                    'queue_history': 'reviewer_queue',
                    'assignment_history': {
                        'assigned_to': reviewer_id,
                        'assigned_by': admin_id,
                        'assigned_at': assigned_at,
                        'role': 'reviewer'
                    }
                }
            }
        )

        # Update in-memory document
        doc['assigned_to'] = reviewer_id
        doc['assigned_by'] = admin_id
        doc['assigned_at'] = assigned_at
        doc['current_queue'] = 'reviewer_queue'

        # Create audit log
        AuditLog.create(
            mongo_db,
            admin_id,
            AuditLog.ACTION_DOCUMENT_ASSIGNED,
            resource_type='document',
            resource_id=str(doc['_id']),
            details={
                'assigned_to': reviewer_id,
                'assigned_to_name': reviewer_name,
                'role': 'reviewer'
            }
        )

    print("\n   ✅ Assignment complete:")
    for i, (reviewer_id, count) in enumerate(assignment_count.items()):
        print(f"      {reviewer_names[i]}: {count} documents")


def simulate_reviewer_work(mongo_db, documents, users):
    """Simulate reviewers claiming and reviewing documents"""
    print("\n" + "="*80)
    print("✍️  PHASE 4: REVIEWER WORK")
    print("="*80)

    print("\n📋 Simulating reviewer claims and reviews...")

    claim_count = 0
    approve_count = 0

    for doc in documents:
        reviewer_id = doc.get('assigned_to')
        if not reviewer_id:
            continue

        # Claim document
        claimed_at = doc['assigned_at'] + timedelta(hours=random.randint(1, 24))

        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'claimed_by': ObjectId(reviewer_id),
                    'claimed_at': claimed_at,
                    'review_status': 'in_review',
                    'document_status': Image.STATUS_IN_REVIEW,
                    'current_queue': 'in_review',
                    'updated_at': claimed_at
                },
                '$push': {'queue_history': 'in_review'}
            }
        )

        # Update in-memory document
        doc['claimed_by'] = ObjectId(reviewer_id)
        doc['claimed_at'] = claimed_at
        doc['review_status'] = 'in_review'
        doc['document_status'] = Image.STATUS_IN_REVIEW
        doc['current_queue'] = 'in_review'

        # Create audit log for claim
        AuditLog.create(
            mongo_db,
            reviewer_id,
            AuditLog.ACTION_CLAIM_DOCUMENT,
            resource_type='document',
            resource_id=str(doc['_id']),
            new_state={'claimed_by': reviewer_id, 'review_status': 'in_review'},
            details={'claimed_at': claimed_at.isoformat()}
        )

        claim_count += 1

        # Review and approve document (after some time)
        reviewed_at = claimed_at + timedelta(hours=random.randint(2, 48))

        # Some documents get manual edits
        manual_edits = []
        if random.random() < 0.3:  # 30% get edits
            manual_edits = [
                {'field': 'total_amount', 'old_value': 'N/A', 'new_value': f'${random.randint(100, 9999)}.00'},
                {'field': 'date', 'old_value': 'N/A', 'new_value': datetime.utcnow().strftime('%Y-%m-%d')}
            ]

        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'reviewed_by': ObjectId(reviewer_id),
                    'reviewed_at': reviewed_at,
                    'review_status': 'approved',
                    'document_status': Image.STATUS_REVIEWED_APPROVED,
                    'review_notes': f'Reviewed by {users[[k for k, v in users.items() if str(v["_id"]) == reviewer_id][0]]["name"]}. Quality verified.',
                    'manual_edits': manual_edits,
                    'current_queue': 'reviewer_approved',
                    'updated_at': reviewed_at
                },
                '$push': {'queue_history': 'reviewer_approved'}
            }
        )

        # Update in-memory document
        doc['reviewed_by'] = ObjectId(reviewer_id)
        doc['reviewed_at'] = reviewed_at
        doc['review_status'] = 'approved'
        doc['document_status'] = Image.STATUS_REVIEWED_APPROVED
        doc['current_queue'] = 'reviewer_approved'

        # Create audit log for approval
        AuditLog.create(
            mongo_db,
            reviewer_id,
            AuditLog.ACTION_APPROVE_DOCUMENT,
            resource_type='document',
            resource_id=str(doc['_id']),
            previous_state={'review_status': 'in_review'},
            new_state={'review_status': 'approved'},
            details={'manual_edits': len(manual_edits), 'notes': 'Approved after review'}
        )

        approve_count += 1

        if approve_count % 10 == 0:
            print(f"   ✅ Processed {approve_count} documents...")

    print(f"\n   ✅ Reviewer work complete:")
    print(f"      Claimed: {claim_count} documents")
    print(f"      Approved: {approve_count} documents")


def assign_to_teachers(mongo_db, documents, users):
    """Assign 10 documents to teachers (5 each)"""
    print("\n" + "="*80)
    print("👨‍🏫 PHASE 5: TEACHER ASSIGNMENT")
    print("="*80)

    admin_id = str(users['admin']['_id'])
    teacher1_id = str(users['teacher1']['_id'])
    teacher2_id = str(users['teacher2']['_id'])

    # Select 10 documents that have been approved by reviewers
    approved_docs = [d for d in documents if d.get('review_status') == 'approved'][:10]

    print(f"\n📋 Assigning 10 documents to teachers...")
    print(f"   Teacher 1 ({users['teacher1']['name']}): 5 documents")
    print(f"   Teacher 2 ({users['teacher2']['name']}): 5 documents")

    for i, doc in enumerate(approved_docs):
        teacher_id = teacher1_id if i < 5 else teacher2_id
        teacher_name = users['teacher1']['name'] if i < 5 else users['teacher2']['name']

        assigned_at = doc['reviewed_at'] + timedelta(hours=random.randint(2, 12))

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'assigned_to': teacher_id,
                    'assigned_by': admin_id,
                    'assigned_at': assigned_at,
                    'current_queue': 'teacher_queue',
                    'updated_at': assigned_at
                },
                '$push': {
                    'queue_history': 'teacher_queue',
                    'assignment_history': {
                        'assigned_to': teacher_id,
                        'assigned_by': admin_id,
                        'assigned_at': assigned_at,
                        'role': 'teacher'
                    }
                }
            }
        )

        # Update in-memory document
        doc['assigned_to'] = teacher_id
        doc['assigned_at'] = assigned_at
        doc['current_queue'] = 'teacher_queue'

        # Create audit log
        AuditLog.create(
            mongo_db,
            admin_id,
            AuditLog.ACTION_DOCUMENT_ASSIGNED,
            resource_type='document',
            resource_id=str(doc['_id']),
            details={
                'assigned_to': teacher_id,
                'assigned_to_name': teacher_name,
                'role': 'teacher',
                'previous_reviewer': str(doc['reviewed_by'])
            }
        )

    print(f"\n   ✅ Teacher assignment complete: 10 documents")


def simulate_reassignments(mongo_db, documents, users):
    """Simulate document reassignments between reviewers"""
    print("\n" + "="*80)
    print("🔄 PHASE 6: REASSIGNMENTS")
    print("="*80)

    admin_id = str(users['admin']['_id'])
    reviewer_ids = [str(users[f'reviewer{i+1}']['_id']) for i in range(5)]
    reviewer_names = [users[f'reviewer{i+1}']['name'] for i in range(5)]

    print("\n📋 Simulating reassignments...")

    # Select 5 documents to reassign
    docs_to_reassign = random.sample([d for d in documents if d.get('current_queue') == 'reviewer_approved'], 5)

    reassignment_count = 0
    for doc in docs_to_reassign:
        old_reviewer_id = doc['assigned_to']
        old_reviewer_name = [reviewer_names[i] for i, rid in enumerate(reviewer_ids) if rid == old_reviewer_id][0]

        # Assign to different reviewer
        available_reviewers = [(rid, name) for rid, name in zip(reviewer_ids, reviewer_names) if rid != old_reviewer_id]
        new_reviewer_id, new_reviewer_name = random.choice(available_reviewers)

        reassigned_at = doc['reviewed_at'] + timedelta(hours=random.randint(1, 12))

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'assigned_to': new_reviewer_id,
                    'assigned_by': admin_id,
                    'assigned_at': reassigned_at,
                    'current_queue': 'reviewer_queue',
                    'review_status': None,
                    'claimed_by': None,
                    'claimed_at': None,
                    'updated_at': reassigned_at
                },
                '$push': {
                    'queue_history': 'reviewer_queue_reassigned',
                    'assignment_history': {
                        'assigned_to': new_reviewer_id,
                        'assigned_by': admin_id,
                        'assigned_at': reassigned_at,
                        'role': 'reviewer',
                        'reassignment': True,
                        'previous_owner': old_reviewer_id
                    }
                }
            }
        )

        # Update in-memory document
        doc['assigned_to'] = new_reviewer_id
        doc['current_queue'] = 'reviewer_queue'

        # Create audit log
        AuditLog.create(
            mongo_db,
            admin_id,
            AuditLog.ACTION_DOCUMENT_ASSIGNED,
            resource_type='document',
            resource_id=str(doc['_id']),
            previous_state={'assigned_to': old_reviewer_id},
            new_state={'assigned_to': new_reviewer_id},
            details={
                'reassignment': True,
                'from': old_reviewer_name,
                'to': new_reviewer_name,
                'reason': 'Workload balancing'
            }
        )

        reassignment_count += 1
        print(f"   ✅ Reassigned from {old_reviewer_name} → {new_reviewer_name}")

    print(f"\n   ✅ Reassignment complete: {reassignment_count} documents")


def simulate_rejections(mongo_db, documents, users):
    """Simulate some documents being rejected and sent back"""
    print("\n" + "="*80)
    print("❌ PHASE 7: REJECTIONS & CORRECTIONS")
    print("="*80)

    print("\n📋 Simulating document rejections...")

    # Select 3 documents to reject
    docs_to_reject = random.sample([d for d in documents if d.get('current_queue') == 'reviewer_approved'], 3)

    rejection_count = 0
    for doc in docs_to_reject:
        reviewer_id = str(doc['reviewed_by'])
        rejected_at = doc['reviewed_at'] + timedelta(hours=random.randint(1, 6))

        rejection_reasons = [
            'OCR quality too low - needs reprocessing',
            'Missing critical information',
            'Document classification incorrect',
            'Requires manual data entry',
            'Image quality insufficient'
        ]

        reason = random.choice(rejection_reasons)

        # Update document
        mongo_db.images.update_one(
            {'_id': doc['_id']},
            {
                '$set': {
                    'review_status': 'rejected',
                    'rejection_reason': reason,
                    'claimed_by': None,
                    'claimed_at': None,
                    'current_queue': 'rejected',
                    'updated_at': rejected_at
                },
                '$push': {'queue_history': 'rejected'}
            }
        )

        # Update in-memory document
        doc['review_status'] = 'rejected'
        doc['rejection_reason'] = reason
        doc['current_queue'] = 'rejected'

        # Create audit log
        AuditLog.create(
            mongo_db,
            reviewer_id,
            AuditLog.ACTION_REJECT_DOCUMENT,
            resource_type='document',
            resource_id=str(doc['_id']),
            previous_state={'review_status': 'approved'},
            new_state={'review_status': 'rejected'},
            details={'reason': reason}
        )

        rejection_count += 1
        print(f"   ❌ Rejected: {doc['title'][:50]}... - {reason}")

    print(f"\n   ✅ Rejection simulation complete: {rejection_count} documents")


def generate_final_summary(mongo_db, documents, users):
    """Generate comprehensive final summary"""
    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)

    # Count documents by status
    status_counts = {}
    for doc in documents:
        status = doc.get('current_queue', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    # Count documents by classification
    classification_counts = {
        'PUBLIC': sum(1 for d in documents if d.get('classification') == Image.CLASSIFICATION_PUBLIC),
        'PRIVATE': sum(1 for d in documents if d.get('classification') == Image.CLASSIFICATION_PRIVATE)
    }

    # Count assignments by user
    reviewer_assignments = {}
    teacher_assignments = {}

    for doc in documents:
        assigned_to = doc.get('assigned_to')
        if assigned_to:
            # Check if reviewer or teacher
            user_data = [u for u in users.values() if str(u['_id']) == assigned_to]
            if user_data:
                user = user_data[0]
                roles = user.get('roles', [])
                if 'reviewer' in roles:
                    reviewer_assignments[user['name']] = reviewer_assignments.get(user['name'], 0) + 1
                elif 'teacher' in roles:
                    teacher_assignments[user['name']] = teacher_assignments.get(user['name'], 0) + 1

    # Get audit log count
    audit_log_count = mongo_db.audit_logs.count_documents({})

    print("\n📈 User Summary:")
    print(f"   Total Users: {len(users)}")
    print(f"   - Admins: 1")
    print(f"   - Reviewers: 5")
    print(f"   - Teachers: 2")

    print("\n📄 Document Summary:")
    print(f"   Total Documents: {len(documents)}")
    print(f"   Classification:")
    print(f"   - PUBLIC: {classification_counts['PUBLIC']}")
    print(f"   - PRIVATE: {classification_counts['PRIVATE']}")

    print("\n📊 Queue Distribution:")
    for queue, count in sorted(status_counts.items()):
        print(f"   - {queue}: {count} documents")

    print("\n👥 Reviewer Assignments:")
    for name, count in sorted(reviewer_assignments.items()):
        print(f"   - {name}: {count} documents")

    print("\n👨‍🏫 Teacher Assignments:")
    for name, count in sorted(teacher_assignments.items()):
        print(f"   - {name}: {count} documents")

    print(f"\n📋 Audit Log Entries: {audit_log_count}")

    # Generate JSON output
    output_data = {
        'summary': {
            'total_users': len(users),
            'total_documents': len(documents),
            'total_audit_logs': audit_log_count
        },
        'users': {
            'admins': [{'name': ADMIN['name'], 'email': ADMIN['email']}],
            'reviewers': [{'name': r['name'], 'email': r['email']} for r in REVIEWERS],
            'teachers': [{'name': t['name'], 'email': t['email']} for t in TEACHERS]
        },
        'documents': {
            'total': len(documents),
            'by_classification': classification_counts,
            'by_queue': status_counts
        },
        'assignments': {
            'reviewers': reviewer_assignments,
            'teachers': teacher_assignments
        }
    }

    # Save JSON output
    output_file = '/mnt/sda1/mango1_home/pala-platform/packages/processors/OCR_metadata_extraction/workflow_simulation_output.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"\n💾 JSON output saved to: workflow_simulation_output.json")

    return output_data


def print_credentials(users):
    """Print login credentials"""
    print("\n" + "="*80)
    print("🔑 USER CREDENTIALS")
    print("="*80)

    print("\n📋 All users use the same password: password123")
    print("\n👤 Admin:")
    print(f"   Email: {ADMIN['email']}")
    print(f"   Password: {DEFAULT_PASSWORD}")

    print("\n👥 Reviewers:")
    for reviewer in REVIEWERS:
        print(f"   Email: {reviewer['email']}")

    print("\n👨‍🏫 Teachers:")
    for teacher in TEACHERS:
        print(f"   Email: {teacher['email']}")


def print_testing_guide():
    """Print testing instructions"""
    print("\n" + "="*80)
    print("🧪 TESTING GUIDE")
    print("="*80)

    print("""
1. LOGIN AS ADMIN:
   - Email: admin@docgen.ai
   - View dashboard at /rbac/admin-dashboard
   - Should see all 35 documents
   - Check user role management at /rbac/user-roles
   - View complete audit logs at /rbac/audit-logs

2. LOGIN AS REVIEWER (e.g., reviewer1@docgen.ai):
   - View review queue at /rbac/review-queue
   - Should see only documents assigned to them
   - Cannot see documents assigned to other reviewers
   - Can claim and review documents
   - Test approve/reject workflows

3. LOGIN AS TEACHER (e.g., teacher1@docgen.ai):
   - View review queue
   - Should see both PUBLIC and PRIVATE documents
   - Can see documents in teacher queue
   - More permissions than reviewers

4. VERIFY RBAC:
   - Reviewers should NOT see admin dashboard
   - Reviewers should NOT see all documents
   - Teachers CAN see PRIVATE documents
   - Audit logs record all actions

5. WORKFLOW VERIFICATION:
   - Documents moved through queues (upload → classification → OCR → review → teacher)
   - Assignments visible in document metadata
   - Queue history tracked
   - Reassignments recorded in audit logs
""")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main workflow simulation"""
    print("\n" + "="*80)
    print("🚀 COMPREHENSIVE RBAC WORKFLOW SIMULATION")
    print("="*80)
    print("\nThis script will create:")
    print("  - 1 Admin user")
    print("  - 5 Reviewer users")
    print("  - 2 Teacher users")
    print("  - 35 Documents with complete workflow")
    print("  - Queue transitions and reassignments")
    print("  - Complete audit trail")

    # Create Flask app
    app = create_app()

    with app.app_context():
        # Clear existing data
        clear_existing_workflow_data(mongo.db)

        # Create users - pass mongo instance, not mongo.db
        users = create_users(mongo)

        # Create project
        project_id = create_project(mongo.db)

        # Create documents
        documents = create_documents(mongo.db, project_id, users)

        # Simulate workflow phases
        simulate_classification(mongo.db, documents, users)
        simulate_ocr_processing(mongo.db, documents)
        assign_to_reviewers(mongo.db, documents, users)
        simulate_reviewer_work(mongo.db, documents, users)
        assign_to_teachers(mongo.db, documents, users)
        simulate_reassignments(mongo.db, documents, users)
        simulate_rejections(mongo.db, documents, users)

        # Generate final summary
        output_data = generate_final_summary(mongo.db, documents, users)

        # Print credentials
        print_credentials(users)

        # Print testing guide
        print_testing_guide()

        print("\n" + "="*80)
        print("✅ WORKFLOW SIMULATION COMPLETE")
        print("="*80)
        print("\nYou can now test the RBAC system with realistic workflow data!")
        print("All users use password: password123")
        print("="*80 + "\n")


if __name__ == '__main__':
    main()
