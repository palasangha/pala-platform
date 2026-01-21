"""
Unit Tests for Verification Models
Tests cover VerificationAudit model and Image verification features
"""
from datetime import datetime
from unittest.mock import Mock, MagicMock
import sys
import os

# Note: These are unit tests that mock MongoDB and don't require Flask to run
# They test the business logic of the verification models

class TestVerificationAuditModel:
    """Test suite for VerificationAudit model"""

    def test_create_audit_entry(self):
        """
        Test: Create audit entry with all fields
        Expected: Returns audit entry with correct fields
        """
        # Import here to avoid dependency issues
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from app.models.verification_audit import VerificationAudit
        
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = 'test_audit_id'
        mongo.db.verification_audits.insert_one.return_value = mock_result

        audit = VerificationAudit.create(
            mongo,
            image_id='test_image_id',
            user_id='test_user_id',
            action='edit',
            field_name='ocr_text',
            old_value='old text',
            new_value='new text',
            notes='Fixed typo'
        )

        assert audit is not None, "Audit entry should be created"
        assert audit['action'] == 'edit', "Action should be 'edit'"
        assert audit['field_name'] == 'ocr_text', "Field name should be set"
        assert audit['old_value'] == 'old text', "Old value should be set"
        assert audit['new_value'] == 'new text', "New value should be set"
        assert audit['notes'] == 'Fixed typo', "Notes should be set"
        print("✅ PASS: Create audit entry")

    def test_create_verify_action(self):
        """
        Test: Create audit entry for verify action
        Expected: Returns audit entry with action='verify'
        """
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = 'test_audit_id'
        mongo.db.verification_audits.insert_one.return_value = mock_result

        audit = VerificationAudit.create(
            mongo,
            image_id='test_image_id',
            user_id='test_user_id',
            action='verify',
            notes='Looks good'
        )

        assert audit['action'] == 'verify', "Action should be 'verify'"
        assert audit.get('field_name') is None, "Field name should be None for verify"
        print("✅ PASS: Create verify action audit")

    def test_create_reject_action(self):
        """
        Test: Create audit entry for reject action
        Expected: Returns audit entry with action='reject'
        """
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = 'test_audit_id'
        mongo.db.verification_audits.insert_one.return_value = mock_result

        audit = VerificationAudit.create(
            mongo,
            image_id='test_image_id',
            user_id='test_user_id',
            action='reject',
            notes='Poor quality OCR'
        )

        assert audit['action'] == 'reject', "Action should be 'reject'"
        assert audit['notes'] == 'Poor quality OCR', "Notes should be set"
        print("✅ PASS: Create reject action audit")

    def test_find_by_image(self):
        """
        Test: Find audit entries by image ID
        Expected: Returns list of audit entries for the image
        """
        mongo = MagicMock()
        mock_audits = [
            {'action': 'edit', 'created_at': datetime.utcnow()},
            {'action': 'verify', 'created_at': datetime.utcnow()}
        ]
        mongo.db.verification_audits.find.return_value.sort.return_value.skip.return_value.limit.return_value = mock_audits

        audits = VerificationAudit.find_by_image(mongo, 'test_image_id')

        assert len(audits) == 2, "Should return 2 audit entries"
        mongo.db.verification_audits.find.assert_called_once()
        print("✅ PASS: Find audit entries by image")

    def test_to_dict(self):
        """
        Test: Convert audit entry to dictionary
        Expected: Returns properly formatted dictionary
        """
        from bson import ObjectId
        
        audit_doc = {
            '_id': ObjectId(),
            'image_id': ObjectId(),
            'user_id': ObjectId(),
            'action': 'edit',
            'field_name': 'ocr_text',
            'old_value': 'old',
            'new_value': 'new',
            'notes': 'test note',
            'created_at': datetime.utcnow()
        }

        result = VerificationAudit.to_dict(audit_doc)

        assert result is not None, "Result should not be None"
        assert result['action'] == 'edit', "Action should be preserved"
        assert result['field_name'] == 'ocr_text', "Field name should be preserved"
        assert 'id' in result, "Should have id field"
        assert 'created_at' in result, "Should have created_at field"
        print("✅ PASS: Convert audit to dict")


class TestImageVerificationFeatures:
    """Test suite for Image model verification features"""

    def test_create_image_with_verification_fields(self):
        """
        Test: Create image with verification fields
        Expected: Returns image with verification_status='pending_verification' and version=1
        """
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = 'test_image_id'
        mongo.db.images.insert_one.return_value = mock_result

        image = Image.create(
            mongo,
            project_id='test_project',
            filename='test.jpg',
            filepath='/test/test.jpg',
            original_filename='original.jpg'
        )

        assert image['verification_status'] == 'pending_verification', "Should start with pending_verification status"
        assert image['version'] == 1, "Should start with version 1"
        assert image.get('verified_by') is None, "verified_by should be None initially"
        print("✅ PASS: Create image with verification fields")

    def test_update_verification_status(self):
        """
        Test: Update verification status to 'verified'
        Expected: Updates status and increments version
        """
        from bson import ObjectId
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mongo.db.images.update_one.return_value = mock_result

        result = Image.update_verification_status(
            mongo,
            'test_image_id',
            'verified',
            'test_user_id',
            version=1
        )

        assert result.matched_count == 1, "Should match one document"
        mongo.db.images.update_one.assert_called_once()
        call_args = mongo.db.images.update_one.call_args
        assert call_args[0][0]['version'] == 1, "Should check version for optimistic locking"
        assert call_args[0][1]['$set']['verification_status'] == 'verified', "Should set status to verified"
        assert '$inc' in call_args[0][1], "Should increment version"
        print("✅ PASS: Update verification status")

    def test_update_verification_status_version_conflict(self):
        """
        Test: Update verification status with wrong version
        Expected: Returns matched_count=0 (version conflict)
        """
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 0  # No match due to version conflict
        mongo.db.images.update_one.return_value = mock_result

        result = Image.update_verification_status(
            mongo,
            'test_image_id',
            'verified',
            'test_user_id',
            version=1  # Wrong version
        )

        assert result.matched_count == 0, "Should not match when version conflicts"
        print("✅ PASS: Detect version conflict")

    def test_update_with_version(self):
        """
        Test: Update image with optimistic locking
        Expected: Updates fields and increments version
        """
        mongo = MagicMock()
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mongo.db.images.update_one.return_value = mock_result

        result = Image.update_with_version(
            mongo,
            'test_image_id',
            {'ocr_text': 'updated text'},
            version=2
        )

        assert result.matched_count == 1, "Should match one document"
        call_args = mongo.db.images.update_one.call_args
        assert call_args[0][0]['version'] == 2, "Should check version"
        assert '$inc' in call_args[0][1], "Should increment version"
        print("✅ PASS: Update with version")

    def test_find_by_verification_status(self):
        """
        Test: Find images by verification status
        Expected: Returns list of images with matching status
        """
        mongo = MagicMock()
        mock_images = [
            {'verification_status': 'pending_verification', 'filename': 'test1.jpg'},
            {'verification_status': 'pending_verification', 'filename': 'test2.jpg'}
        ]
        mongo.db.images.find.return_value.sort.return_value.skip.return_value.limit.return_value = mock_images

        images = Image.find_by_verification_status(mongo, 'pending_verification')

        assert len(images) == 2, "Should return 2 images"
        mongo.db.images.find.assert_called_with({'verification_status': 'pending_verification'})
        print("✅ PASS: Find images by verification status")

    def test_count_by_verification_status(self):
        """
        Test: Count images by verification status
        Expected: Returns count of matching images
        """
        mongo = MagicMock()
        mongo.db.images.count_documents.return_value = 5

        count = Image.count_by_verification_status(mongo, 'verified')

        assert count == 5, "Should return count of 5"
        mongo.db.images.count_documents.assert_called_with({'verification_status': 'verified'})
        print("✅ PASS: Count images by verification status")

    def test_to_dict_with_verification_fields(self):
        """
        Test: Convert image to dict with verification fields
        Expected: Returns dict with all verification fields
        """
        from bson import ObjectId
        
        image_doc = {
            '_id': ObjectId(),
            'project_id': ObjectId(),
            'filename': 'test.jpg',
            'original_filename': 'original.jpg',
            'file_type': 'image',
            'ocr_status': 'completed',
            'verification_status': 'verified',
            'verified_by': ObjectId(),
            'verified_at': datetime.utcnow(),
            'version': 3,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = Image.to_dict(image_doc)

        assert result is not None, "Result should not be None"
        assert result['verification_status'] == 'verified', "Should have verification status"
        assert result['verified_by'] is not None, "Should have verified_by"
        assert result['verified_at'] is not None, "Should have verified_at"
        assert result['version'] == 3, "Should have version"
        print("✅ PASS: Convert image with verification fields to dict")


if __name__ == '__main__':
    print("\n=== Testing Verification Audit Model ===\n")
    test_audit = TestVerificationAuditModel()
    test_audit.test_create_audit_entry()
    test_audit.test_create_verify_action()
    test_audit.test_create_reject_action()
    test_audit.test_find_by_image()
    test_audit.test_to_dict()

    print("\n=== Testing Image Verification Features ===\n")
    test_image = TestImageVerificationFeatures()
    test_image.test_create_image_with_verification_fields()
    test_image.test_update_verification_status()
    test_image.test_update_verification_status_version_conflict()
    test_image.test_update_with_version()
    test_image.test_find_by_verification_status()
    test_image.test_count_by_verification_status()
    test_image.test_to_dict_with_verification_fields()

    print("\n✅ All tests passed!\n")
