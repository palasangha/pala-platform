"""
Comprehensive RBAC System Test Suite
Tests all RBAC endpoints, authorization, and error handling
"""

import pytest
import json
from datetime import datetime, timedelta
from bson import ObjectId
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import mongo, init_db
from app.models.user import User
from app.models.role import Role
from app.models.image import Image
from app.models.audit_log import AuditLog
import jwt


class TestRBACSystem:
    """Test RBAC system functionality"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        # Create test app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Create app context
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Initialize database
        init_db(self.app)

        # Clear test data
        mongo.db.users.delete_many({})
        mongo.db.roles.delete_many({})
        mongo.db.images.delete_many({})
        mongo.db.audit_logs.delete_many({})

        # Create default roles
        Role.initialize_default_roles(mongo)

        # Create test users
        self.admin = User.create(mongo, 'admin@test.com', 'admin123',
                                name='Test Admin', roles=['admin'])
        self.reviewer = User.create(mongo, 'reviewer@test.com', 'reviewer123',
                                   name='Test Reviewer', roles=['reviewer'])
        self.teacher = User.create(mongo, 'teacher@test.com', 'teacher123',
                                  name='Test Teacher', roles=['teacher'])

        # Generate tokens
        self.admin_token = self._generate_token(self.admin['_id'])
        self.reviewer_token = self._generate_token(self.reviewer['_id'])
        self.teacher_token = self._generate_token(self.teacher['_id'])

        yield

        self.ctx.pop()

    def _generate_token(self, user_id):
        """Generate JWT token for testing"""
        from app.config import Config
        return jwt.encode({
            'user_id': str(user_id),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, Config.JWT_SECRET_KEY, algorithm='HS256')

    def _get_headers(self, token):
        """Get headers with authorization"""
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def _create_test_image(self, project_id):
        """Create a test image"""
        image = Image.create(mongo, project_id, 'test.pdf', '/tmp/test.pdf', 'test.pdf')
        # Mark as OCR processed to appear in review queue
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {'$set': {'document_status': Image.STATUS_OCR_PROCESSED}}
        )
        return Image.find_by_id(mongo, image['_id'])

    # ========================================================================
    # CLASSIFICATION TESTS
    # ========================================================================

    def test_classify_document_admin_success(self):
        """Test admin can classify document"""
        # Create test image
        image = self._create_test_image(ObjectId())
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/documents/{doc_id}/classify',
            headers=self._get_headers(self.admin_token),
            json={
                'classification': 'PUBLIC',
                'reason': 'Test classification'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['document']['classification'] == 'PUBLIC'

    def test_classify_document_reviewer_forbidden(self):
        """Test reviewer cannot classify document"""
        image = self._create_test_image(ObjectId())
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/documents/{doc_id}/classify',
            headers=self._get_headers(self.reviewer_token),
            json={
                'classification': 'PUBLIC',
                'reason': 'Should fail'
            }
        )

        assert response.status_code == 403

    def test_classify_invalid_classification(self):
        """Test invalid classification value"""
        image = self._create_test_image(ObjectId())
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/documents/{doc_id}/classify',
            headers=self._get_headers(self.admin_token),
            json={
                'classification': 'INVALID',
                'reason': 'Should fail'
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid classification' in data['error']

    def test_classify_document_not_found(self):
        """Test classify non-existent document"""
        fake_id = str(ObjectId())

        response = self.client.post(
            f'/api/rbac/documents/{fake_id}/classify',
            headers=self._get_headers(self.admin_token),
            json={
                'classification': 'PUBLIC',
                'reason': 'Should fail'
            }
        )

        assert response.status_code == 404

    def test_classify_already_classified(self):
        """Test cannot re-classify document"""
        image = self._create_test_image(ObjectId())
        doc_id = str(image['_id'])

        # First classification
        self.client.post(
            f'/api/rbac/documents/{doc_id}/classify',
            headers=self._get_headers(self.admin_token),
            json={'classification': 'PUBLIC', 'reason': 'First'}
        )

        # Second classification should fail
        response = self.client.post(
            f'/api/rbac/documents/{doc_id}/classify',
            headers=self._get_headers(self.admin_token),
            json={'classification': 'PRIVATE', 'reason': 'Second'}
        )

        assert response.status_code == 409
        data = response.get_json()
        assert 'already classified' in data['error'].lower()

    # ========================================================================
    # REVIEW QUEUE TESTS
    # ========================================================================

    def test_review_queue_reviewer_public_only(self):
        """Test reviewer sees only PUBLIC documents"""
        project_id = ObjectId()

        # Create PUBLIC document
        public_doc = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': public_doc['_id']},
            {'$set': {'classification': 'PUBLIC'}}
        )

        # Create PRIVATE document
        private_doc = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': private_doc['_id']},
            {'$set': {'classification': 'PRIVATE'}}
        )

        response = self.client.get(
            '/api/rbac/review-queue',
            headers=self._get_headers(self.reviewer_token)
        )

        assert response.status_code == 200
        data = response.get_json()
        queue = data['queue']

        # Should see only PUBLIC
        assert len(queue) == 1
        assert queue[0]['classification'] == 'PUBLIC'

    def test_review_queue_teacher_all_documents(self):
        """Test teacher sees PUBLIC and PRIVATE documents"""
        project_id = ObjectId()

        # Create PUBLIC document
        public_doc = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': public_doc['_id']},
            {'$set': {'classification': 'PUBLIC'}}
        )

        # Create PRIVATE document
        private_doc = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': private_doc['_id']},
            {'$set': {'classification': 'PRIVATE'}}
        )

        response = self.client.get(
            '/api/rbac/review-queue',
            headers=self._get_headers(self.teacher_token)
        )

        assert response.status_code == 200
        data = response.get_json()
        queue = data['queue']

        # Should see both
        assert len(queue) == 2

    def test_review_queue_pagination(self):
        """Test review queue pagination"""
        project_id = ObjectId()

        # Create 15 documents
        for i in range(15):
            doc = self._create_test_image(project_id)
            mongo.db.images.update_one(
                {'_id': doc['_id']},
                {'$set': {'classification': 'PUBLIC'}}
            )

        response = self.client.get(
            '/api/rbac/review-queue?page=1&per_page=10',
            headers=self._get_headers(self.reviewer_token)
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data['queue']) == 10
        assert data['pagination']['total_count'] == 15
        assert data['pagination']['total_pages'] == 2

    # ========================================================================
    # CLAIM DOCUMENT TESTS
    # ========================================================================

    def test_claim_document_success(self):
        """Test reviewer can claim document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {'$set': {'classification': 'PUBLIC'}}
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/claim',
            headers=self._get_headers(self.reviewer_token)
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['document']['claimed_by'] == str(self.reviewer['_id'])

    def test_claim_already_claimed(self):
        """Test cannot claim already claimed document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {'$set': {'classification': 'PUBLIC', 'claimed_by': self.reviewer['_id']}}
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/claim',
            headers=self._get_headers(self.teacher_token)
        )

        assert response.status_code == 409
        data = response.get_json()
        assert 'already claimed' in data['error'].lower()

    def test_claim_private_reviewer_forbidden(self):
        """Test reviewer cannot claim PRIVATE document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {'$set': {'classification': 'PRIVATE'}}
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/claim',
            headers=self._get_headers(self.reviewer_token)
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'PRIVATE' in data['error']

    def test_claim_private_teacher_success(self):
        """Test teacher can claim PRIVATE document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {'$set': {'classification': 'PRIVATE'}}
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/claim',
            headers=self._get_headers(self.teacher_token)
        )

        assert response.status_code == 200

    # ========================================================================
    # APPROVE DOCUMENT TESTS
    # ========================================================================

    def test_approve_document_success(self):
        """Test can approve claimed document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {
                '$set': {
                    'classification': 'PUBLIC',
                    'claimed_by': self.reviewer['_id'],
                    'document_status': Image.STATUS_IN_REVIEW
                }
            }
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/approve',
            headers=self._get_headers(self.reviewer_token),
            json={
                'edit_fields': {'author': 'John Doe'},
                'notes': 'Approved'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['document']['review_status'] == 'approved'

    def test_approve_not_claimed_by_user(self):
        """Test cannot approve document not claimed by user"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {
                '$set': {
                    'classification': 'PUBLIC',
                    'claimed_by': self.reviewer['_id'],
                    'document_status': Image.STATUS_IN_REVIEW
                }
            }
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/approve',
            headers=self._get_headers(self.teacher_token),
            json={'edit_fields': {}, 'notes': 'Should fail'}
        )

        assert response.status_code == 403

    def test_approve_wrong_status(self):
        """Test cannot approve document not in review status"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {
                '$set': {
                    'classification': 'PUBLIC',
                    'claimed_by': self.reviewer['_id'],
                    'document_status': Image.STATUS_UPLOADED  # Wrong status
                }
            }
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/approve',
            headers=self._get_headers(self.reviewer_token),
            json={'edit_fields': {}, 'notes': 'Should fail'}
        )

        assert response.status_code == 409

    # ========================================================================
    # REJECT DOCUMENT TESTS
    # ========================================================================

    def test_reject_document_success(self):
        """Test can reject claimed document"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {
                '$set': {
                    'classification': 'PUBLIC',
                    'claimed_by': self.reviewer['_id'],
                    'document_status': Image.STATUS_IN_REVIEW
                }
            }
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/reject',
            headers=self._get_headers(self.reviewer_token),
            json={'reason': 'Quality too low'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['document']['review_status'] == 'rejected'

    def test_reject_missing_reason(self):
        """Test rejection requires reason"""
        project_id = ObjectId()
        image = self._create_test_image(project_id)
        mongo.db.images.update_one(
            {'_id': image['_id']},
            {
                '$set': {
                    'classification': 'PUBLIC',
                    'claimed_by': self.reviewer['_id'],
                    'document_status': Image.STATUS_IN_REVIEW
                }
            }
        )
        doc_id = str(image['_id'])

        response = self.client.post(
            f'/api/rbac/review/{doc_id}/reject',
            headers=self._get_headers(self.reviewer_token),
            json={'reason': ''}
        )

        assert response.status_code == 400

    # ========================================================================
    # ROLE MANAGEMENT TESTS
    # ========================================================================

    def test_update_user_roles_admin_only(self):
        """Test only admin can update user roles"""
        new_user = User.create(mongo, 'newuser@test.com', 'pass123', roles=['reviewer'])

        response = self.client.post(
            f'/api/rbac/users/{str(new_user["_id"])}/roles',
            headers=self._get_headers(self.admin_token),
            json={'roles': ['teacher', 'reviewer']}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert set(data['new_roles']) == {'teacher', 'reviewer'}

    def test_update_roles_non_admin_forbidden(self):
        """Test reviewer cannot update roles"""
        response = self.client.post(
            f'/api/rbac/users/{str(self.reviewer["_id"])}/roles',
            headers=self._get_headers(self.reviewer_token),
            json={'roles': ['admin']}
        )

        assert response.status_code == 403

    # ========================================================================
    # AUDIT LOG TESTS
    # ========================================================================

    def test_audit_logs_accessible_by_admin(self):
        """Test admin can view audit logs"""
        response = self.client.get(
            '/api/rbac/audit-logs',
            headers=self._get_headers(self.admin_token)
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'audit_logs' in data

    def test_audit_logs_not_accessible_by_reviewer(self):
        """Test reviewer cannot view audit logs"""
        response = self.client.get(
            '/api/rbac/audit-logs',
            headers=self._get_headers(self.reviewer_token)
        )

        assert response.status_code == 403

    def test_document_audit_trail(self):
        """Test document audit trail accessible by admin"""
        image = self._create_test_image(ObjectId())
        doc_id = str(image['_id'])

        response = self.client.get(
            f'/api/rbac/audit-logs/document/{doc_id}',
            headers=self._get_headers(self.admin_token)
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'audit_trail' in data

    # ========================================================================
    # AUTHORIZATION TESTS
    # ========================================================================

    def test_invalid_token(self):
        """Test invalid token is rejected"""
        response = self.client.get(
            '/api/rbac/review-queue',
            headers={'Authorization': 'Bearer invalid_token'}
        )

        assert response.status_code == 401

    def test_missing_token(self):
        """Test missing token is rejected"""
        response = self.client.get('/api/rbac/review-queue')

        assert response.status_code == 401

    def test_expired_token(self):
        """Test expired token is rejected"""
        expired_token = jwt.encode({
            'user_id': str(self.admin['_id']),
            'exp': datetime.utcnow() - timedelta(hours=1)
        }, 'test_secret', algorithm='HS256')

        response = self.client.get(
            '/api/rbac/review-queue',
            headers={'Authorization': f'Bearer {expired_token}'}
        )

        assert response.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
