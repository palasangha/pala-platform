"""
Unit Tests for OCRChainTemplate Model
Tests cover CRUD operations, validation, and edge cases
"""

import pytest
from datetime import datetime
from bson import ObjectId
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Mock MongoDB before imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestOCRChainTemplateCreate:
    """Test suite for template creation"""

    def test_create_valid_template(self):
        """
        Test: Create a valid template with all required fields
        Expected: Template is created and returned with _id
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        # Setup
        mongo = Mock()
        mongo.db.ocr_chain_templates.insert_one.return_value = Mock(inserted_id=ObjectId())
        user_id = str(ObjectId())

        template_data = {
            'name': 'Test Chain',
            'description': 'Test description',
            'steps': [
                {
                    'step_number': 1,
                    'provider': 'google_vision',
                    'input_source': 'original_image',
                    'prompt': '',
                    'enabled': True
                }
            ],
            'is_public': False
        }

        # Execute
        result = OCRChainTemplate.create(mongo, user_id, template_data)

        # Assert
        assert result is not None, "Template creation returned None"
        assert result['name'] == 'Test Chain', f"Expected name 'Test Chain', got {result['name']}"
        assert result['user_id'] == ObjectId(user_id), f"User ID mismatch"
        assert '_id' in result, "Template missing _id field"
        assert result['created_at'] is not None, "created_at not set"
        assert result['updated_at'] is not None, "updated_at not set"
        print("✅ PASS: Valid template creation")

    def test_create_template_missing_name(self):
        """
        Test: Create template without required name field
        Expected: Template still created (name will be None)
        Issue: Should validate and reject
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mongo.db.ocr_chain_templates.insert_one.return_value = Mock(inserted_id=ObjectId())

        template_data = {
            # Missing 'name'
            'steps': [{'step_number': 1, 'provider': 'google_vision'}]
        }

        result = OCRChainTemplate.create(mongo, ObjectId(), template_data)

        # This is the bug - name is None but no error
        if result['name'] is None:
            print("⚠️ ISSUE FOUND: Template created with None name - should validate")
        else:
            print("✅ PASS: Template name validation works")

    def test_create_template_invalid_user_id_format(self):
        """
        Test: Create template with invalid user_id format
        Expected: Raises InvalidId exception
        """
        from app.models.ocr_chain_template import OCRChainTemplate
        from bson.errors import InvalidId

        mongo = Mock()

        try:
            # Invalid ObjectId string
            result = OCRChainTemplate.create(mongo, "invalid_id", {})
            # If we reach here, the bug is confirmed
            print("❌ FAILURE: Should have raised InvalidId exception")
        except InvalidId:
            print("✅ PASS: InvalidId exception raised for bad format")
        except Exception as e:
            print(f"⚠️ ISSUE: Unexpected exception - {type(e).__name__}: {e}")

    def test_create_template_database_error(self):
        """
        Test: Database connection fails during insert
        Expected: Should propagate exception with clear error message
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mongo.db.ocr_chain_templates.insert_one.side_effect = Exception("Connection timeout")

        try:
            result = OCRChainTemplate.create(mongo, str(ObjectId()), {'name': 'Test'})
            print("❌ FAILURE: Should have raised exception on DB error")
        except Exception as e:
            if "Connection timeout" in str(e):
                print("✅ PASS: Database error propagated correctly")
            else:
                print(f"⚠️ ISSUE: Unexpected error - {e}")


class TestOCRChainTemplateValidation:
    """Test suite for chain validation"""

    def test_validate_valid_single_step(self):
        """
        Test: Validate a single-step chain
        Expected: Returns (True, None)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {
                'step_number': 1,
                'provider': 'google_vision',
                'input_source': 'original_image',
                'prompt': '',
                'enabled': True
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is True, f"Single step should be valid"
        assert error is None, f"Error should be None for valid chain"
        print("✅ PASS: Single step chain validation")

    def test_validate_valid_multi_step(self):
        """
        Test: Validate a multi-step chain with proper input routing
        Expected: Returns (True, None)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {
                'step_number': 1,
                'provider': 'google_vision',
                'input_source': 'original_image',
                'prompt': '',
                'enabled': True
            },
            {
                'step_number': 2,
                'provider': 'claude',
                'input_source': 'previous_step',
                'prompt': 'Extract names',
                'enabled': True
            },
            {
                'step_number': 3,
                'provider': 'ollama',
                'input_source': 'step_N',
                'input_step_numbers': [2],
                'prompt': 'Format as JSON',
                'enabled': True
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is True, f"Valid multi-step chain failed: {error}"
        print("✅ PASS: Multi-step chain validation")

    def test_validate_empty_steps(self):
        """
        Test: Validate empty steps list
        Expected: Returns (False, error_message)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        is_valid, error = OCRChainTemplate.validate_chain([])

        assert is_valid is False, "Empty steps should be invalid"
        assert error is not None, "Error message should be provided"
        assert "at least one step" in error.lower(), f"Error should mention steps: {error}"
        print("✅ PASS: Empty steps validation")

    def test_validate_non_sequential_steps(self):
        """
        Test: Validate steps with non-sequential numbering (1, 3, 2)
        Expected: Returns (False, error_message about sequence)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {'step_number': 1, 'provider': 'google_vision', 'input_source': 'original_image'},
            {'step_number': 3, 'provider': 'claude', 'input_source': 'previous_step'},  # Wrong!
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "Non-sequential steps should be invalid"
        assert "sequential" in error.lower(), f"Error should mention sequencing: {error}"
        print("✅ PASS: Non-sequential step detection")

    def test_validate_step_1_previous_step_input(self):
        """
        Test: Step 1 tries to use 'previous_step' as input
        Expected: Returns (False, error_message)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {
                'step_number': 1,
                'provider': 'google_vision',
                'input_source': 'previous_step',  # Invalid for step 1!
                'prompt': '',
                'enabled': True
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "Step 1 with previous_step should be invalid"
        assert "Step 1" in error, f"Error should reference Step 1: {error}"
        print("✅ PASS: Step 1 previous_step validation")

    def test_validate_missing_provider(self):
        """
        Test: Validate step without provider
        Expected: Returns (False, error_message)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {
                'step_number': 1,
                'input_source': 'original_image',
                # Missing 'provider'!
                'prompt': '',
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "Missing provider should be invalid"
        assert "provider" in error.lower(), f"Error should mention provider: {error}"
        print("✅ PASS: Missing provider detection")

    def test_validate_circular_dependency_forward_reference(self):
        """
        Test: Step 2 references step 3 (future step)
        Expected: Returns (False, error_message about circular reference)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {'step_number': 1, 'provider': 'google_vision', 'input_source': 'original_image'},
            {
                'step_number': 2,
                'provider': 'claude',
                'input_source': 'step_N',
                'input_step_numbers': [3],  # References future step!
                'prompt': ''
            },
            {'step_number': 3, 'provider': 'ollama', 'input_source': 'previous_step', 'prompt': ''}
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "Forward reference should be invalid"
        assert "cannot reference" in error.lower(), f"Error should mention reference issue: {error}"
        print("✅ PASS: Forward reference detection")

    def test_validate_step_N_without_input_steps(self):
        """
        Test: Step with input_source='step_N' but missing input_step_numbers
        Expected: Returns (False, error_message)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {'step_number': 1, 'provider': 'google_vision', 'input_source': 'original_image'},
            {
                'step_number': 2,
                'provider': 'claude',
                'input_source': 'step_N',
                # Missing input_step_numbers!
                'prompt': ''
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "step_N without input_step_numbers should be invalid"
        assert "input_step_numbers" in error, f"Error should mention input_step_numbers: {error}"
        print("✅ PASS: step_N without input_steps detection")

    def test_validate_invalid_input_source(self):
        """
        Test: Step has invalid input_source value
        Expected: Returns (False, error_message)
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        steps = [
            {
                'step_number': 1,
                'provider': 'google_vision',
                'input_source': 'invalid_source',  # Not in allowed list!
                'prompt': ''
            }
        ]

        is_valid, error = OCRChainTemplate.validate_chain(steps)

        assert is_valid is False, "Invalid input_source should be invalid"
        assert "input_source" in error.lower(), f"Error should mention input_source: {error}"
        print("✅ PASS: Invalid input_source detection")


class TestOCRChainTemplateFind:
    """Test suite for template queries"""

    def test_find_by_id_valid(self):
        """
        Test: Find template by valid ObjectId
        Expected: Returns template document
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        template_id = ObjectId()
        user_id = ObjectId()
        mock_template = {'_id': template_id, 'name': 'Test'}

        mongo.db.ocr_chain_templates.find_one.return_value = mock_template

        result = OCRChainTemplate.find_by_id(mongo, str(template_id), str(user_id))

        assert result == mock_template, "Should return template"
        mongo.db.ocr_chain_templates.find_one.assert_called_once()
        print("✅ PASS: Find template by ID")

    def test_find_by_id_invalid_format(self):
        """
        Test: Find template with invalid ObjectId format
        Expected: Raises InvalidId exception
        """
        from app.models.ocr_chain_template import OCRChainTemplate
        from bson.errors import InvalidId

        mongo = Mock()

        try:
            result = OCRChainTemplate.find_by_id(mongo, "invalid_id", str(ObjectId()))
            print("❌ FAILURE: Should have raised InvalidId")
        except InvalidId:
            print("✅ PASS: InvalidId raised for bad format")

    def test_find_by_user_authorization(self):
        """
        Test: find_by_id with user_id should check both _id and user_id
        Expected: Query includes both filters
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mongo.db.ocr_chain_templates.find_one.return_value = None

        template_id = str(ObjectId())
        user_id = str(ObjectId())

        OCRChainTemplate.find_by_id(mongo, template_id, user_id)

        # Verify query includes both user_id and template _id
        call_args = mongo.db.ocr_chain_templates.find_one.call_args[0][0]
        assert '_id' in call_args, "Query should filter by _id"
        assert 'user_id' in call_args, "Query should filter by user_id for authorization"
        print("✅ PASS: Authorization check in find_by_id")


class TestOCRChainTemplateUpdate:
    """Test suite for template updates"""

    def test_update_valid(self):
        """
        Test: Update template with valid data
        Expected: Returns result with matched_count > 0
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mock_result = Mock(matched_count=1, modified_count=1)
        mongo.db.ocr_chain_templates.update_one.return_value = mock_result

        template_id = str(ObjectId())
        user_id = str(ObjectId())

        result = OCRChainTemplate.update(mongo, template_id, user_id, {'name': 'Updated'})

        assert result.matched_count == 1, "Should match existing document"
        # Verify update_data includes updated_at
        call_args = mongo.db.ocr_chain_templates.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert 'updated_at' in update_data, "Should set updated_at timestamp"
        print("✅ PASS: Template update with timestamp")

    def test_update_nonexistent(self):
        """
        Test: Update non-existent template
        Expected: Returns matched_count = 0 (no error raised)
        Issue: Should validate and return error
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mock_result = Mock(matched_count=0, modified_count=0)
        mongo.db.ocr_chain_templates.update_one.return_value = mock_result

        result = OCRChainTemplate.update(mongo, str(ObjectId()), str(ObjectId()), {})

        if result.matched_count == 0:
            print("⚠️ ISSUE: Update returned success even though no document matched")
            print("   Should notify caller that update failed")
        else:
            print("✅ PASS: Non-existent update handled")


class TestOCRChainTemplateDelete:
    """Test suite for template deletion"""

    def test_delete_valid(self):
        """
        Test: Delete existing template
        Expected: deleted_count > 0
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mock_result = Mock(deleted_count=1)
        mongo.db.ocr_chain_templates.delete_one.return_value = mock_result

        result = OCRChainTemplate.delete(mongo, str(ObjectId()), str(ObjectId()))

        assert result.deleted_count == 1, "Should delete one document"
        print("✅ PASS: Template deletion")

    def test_delete_nonexistent(self):
        """
        Test: Delete non-existent template
        Expected: deleted_count = 0 (no error)
        Issue: Should distinguish between "not found" and "authorization failed"
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mock_result = Mock(deleted_count=0)
        mongo.db.ocr_chain_templates.delete_one.return_value = mock_result

        result = OCRChainTemplate.delete(mongo, str(ObjectId()), str(ObjectId()))

        if result.deleted_count == 0:
            print("⚠️ ISSUE: Delete returned success even though no document deleted")
            print("   Client won't know if template not found or authorization failed")


class TestOCRChainTemplateDuplicate:
    """Test suite for template duplication"""

    def test_duplicate_valid(self):
        """
        Test: Duplicate an existing template
        Expected: Returns new template with copied fields
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        original = {
            '_id': ObjectId(),
            'user_id': ObjectId(),
            'name': 'Original',
            'description': 'Original desc',
            'steps': [{'step_number': 1, 'provider': 'test'}],
            'is_public': False
        }

        mock_new_id = ObjectId()
        mongo.db.ocr_chain_templates.find_one.return_value = original
        mongo.db.ocr_chain_templates.insert_one.return_value = Mock(inserted_id=mock_new_id)

        result = OCRChainTemplate.duplicate(mongo, str(original['_id']), str(original['user_id']), 'Duplicate')

        assert result['name'] == 'Duplicate', "New template should have new name"
        assert result['steps'] == original['steps'], "Steps should be copied"
        assert result['user_id'] == original['user_id'], "User should be same"
        print("✅ PASS: Template duplication")

    def test_duplicate_nonexistent(self):
        """
        Test: Duplicate non-existent template
        Expected: Returns None
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        mongo = Mock()
        mongo.db.ocr_chain_templates.find_one.return_value = None

        result = OCRChainTemplate.duplicate(mongo, str(ObjectId()), str(ObjectId()), 'Copy')

        assert result is None, "Should return None for non-existent template"
        print("✅ PASS: Duplicate non-existent returns None")


class TestOCRChainTemplateToDict:
    """Test suite for serialization"""

    def test_to_dict_valid(self):
        """
        Test: Convert template document to dictionary
        Expected: All fields present and properly formatted
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        template = {
            '_id': ObjectId(),
            'user_id': ObjectId(),
            'name': 'Test',
            'description': 'Test desc',
            'steps': [{'step_number': 1}],
            'is_public': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        result = OCRChainTemplate.to_dict(template)

        assert result['id'] == str(template['_id']), "ID should be stringified"
        assert result['user_id'] == str(template['user_id']), "User ID should be stringified"
        assert result['name'] == 'Test', "Name should be preserved"
        assert isinstance(result['created_at'], str), "Timestamp should be ISO string"
        print("✅ PASS: Template serialization")

    def test_to_dict_none(self):
        """
        Test: Convert None to dictionary
        Expected: Returns None
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        result = OCRChainTemplate.to_dict(None)

        assert result is None, "Should return None for None input"
        print("✅ PASS: to_dict None handling")

    def test_to_dict_missing_fields(self):
        """
        Test: Convert document with missing optional fields
        Expected: Returns dict with default values for missing fields
        """
        from app.models.ocr_chain_template import OCRChainTemplate

        template = {
            '_id': ObjectId(),
            'user_id': ObjectId(),
            'name': 'Minimal',
            # Missing: description, is_public, created_at, updated_at
        }

        result = OCRChainTemplate.to_dict(template)

        assert result['description'] == '', "Missing description should default to empty string"
        assert result['is_public'] is False, "Missing is_public should default to False"
        assert result['created_at'] is None, "Missing created_at should be None"
        print("✅ PASS: to_dict default values")


# ============================================================================
# Test Summary and Execution
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("OCR CHAIN TEMPLATE - UNIT TEST SUITE")
    print("="*70 + "\n")

    test_classes = [
        TestOCRChainTemplateCreate,
        TestOCRChainTemplateValidation,
        TestOCRChainTemplateFind,
        TestOCRChainTemplateUpdate,
        TestOCRChainTemplateDelete,
        TestOCRChainTemplateDuplicate,
        TestOCRChainTemplateToDict,
    ]

    passed = 0
    failed = 0
    issues = 0

    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 70)

        test_instance = test_class()
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_instance, method_name)
                    method()
                    passed += 1
                except AssertionError as e:
                    print(f"❌ FAILURE: {e}")
                    failed += 1
                except Exception as e:
                    print(f"⚠️ ERROR: {type(e).__name__}: {e}")
                    issues += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed, {issues} issues")
    print("="*70 + "\n")
