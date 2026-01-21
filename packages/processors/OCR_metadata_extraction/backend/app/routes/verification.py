"""
Verification Routes
API endpoints for the verification workflow, including queue management, 
inline editing, and audit trail
"""
from flask import Blueprint, request, jsonify
from app.models import Image, VerificationAudit, mongo
from app.routes.auth import jwt_required, get_current_user
from bson import ObjectId
from datetime import datetime

verification_bp = Blueprint('verification', __name__)


@verification_bp.route('/api/verification/queue', methods=['GET'])
@jwt_required
def get_verification_queue():
    """
    Get verification queue with filtering and pagination
    
    Query Parameters:
        status: Filter by verification status (pending_verification, verified, rejected)
        skip: Number of items to skip
        limit: Maximum items to return
    
    Returns:
        JSON with queue items and total count
    """
    try:
        current_user = get_current_user()
        
        # Get query parameters with validation
        status = request.args.get('status', 'pending_verification')
        if status not in ['pending_verification', 'verified', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status value'}), 400
        
        try:
            skip = int(request.args.get('skip', 0))
            limit = int(request.args.get('limit', 50))
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid pagination parameters'}), 400
        
        # Validate pagination ranges
        if skip < 0:
            return jsonify({'success': False, 'error': 'skip must be non-negative'}), 400
        if limit < 1 or limit > 100:
            return jsonify({'success': False, 'error': 'limit must be between 1 and 100'}), 400
        
        # Get images by verification status
        images = Image.find_by_verification_status(mongo.mongo, status, skip, limit)
        total_count = Image.count_by_verification_status(mongo.mongo, status)
        
        return jsonify({
            'success': True,
            'items': [Image.to_dict(img) for img in images],
            'total': total_count,
            'skip': skip,
            'limit': limit
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/queue/counts', methods=['GET'])
@jwt_required
def get_queue_counts():
    """
    Get counts for each verification status
    
    Returns:
        JSON with counts for pending_verification, verified, and rejected
    """
    try:
        pending_count = Image.count_by_verification_status(mongo.mongo, 'pending_verification')
        verified_count = Image.count_by_verification_status(mongo.mongo, 'verified')
        rejected_count = Image.count_by_verification_status(mongo.mongo, 'rejected')
        
        return jsonify({
            'success': True,
            'counts': {
                'pending_verification': pending_count,
                'verified': verified_count,
                'rejected': rejected_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/image/<image_id>', methods=['GET'])
@jwt_required
def get_image_for_verification(image_id):
    """
    Get image details for verification including audit trail
    
    Returns:
        JSON with image details and audit history
    """
    try:
        image = Image.find_by_id(mongo.mongo, image_id)
        if not image:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        # Get audit trail
        audit_entries = VerificationAudit.find_by_image(mongo.mongo, image_id)
        
        return jsonify({
            'success': True,
            'image': Image.to_dict(image),
            'audit_trail': [VerificationAudit.to_dict(entry) for entry in audit_entries]
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/image/<image_id>/edit', methods=['PUT'])
@jwt_required
def edit_image_metadata(image_id):
    """
    Edit image metadata with optimistic locking
    
    Request Body:
        ocr_text: Updated OCR text
        version: Current version for optimistic locking
        notes: Optional notes about the change
    
    Returns:
        JSON with success status and updated image
    """
    try:
        current_user = get_current_user()
        data = request.json
        
        if not data or 'ocr_text' not in data:
            return jsonify({'success': False, 'error': 'OCR text is required'}), 400
        
        # Get current image to check version and old value
        image = Image.find_by_id(mongo.mongo, image_id)
        if not image:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
        
        version = data.get('version')
        old_text = image.get('ocr_text')
        new_text = data.get('ocr_text')
        
        # Update with optimistic locking
        result = Image.update_with_version(
            mongo.mongo,
            image_id,
            {'ocr_text': new_text},
            version
        )
        
        if result.matched_count == 0:
            return jsonify({
                'success': False,
                'error': 'Version conflict - image was updated by another user'
            }), 409
        
        # Create audit entry
        VerificationAudit.create(
            mongo.mongo,
            image_id,
            current_user['id'],
            action='edit',
            field_name='ocr_text',
            old_value=old_text,
            new_value=new_text,
            notes=data.get('notes')
        )
        
        # Get updated image
        updated_image = Image.find_by_id(mongo.mongo, image_id)
        
        return jsonify({
            'success': True,
            'image': Image.to_dict(updated_image)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/image/<image_id>/verify', methods=['POST'])
@jwt_required
def verify_image(image_id):
    """
    Mark image as verified
    
    Request Body:
        version: Current version for optimistic locking
        notes: Optional notes about the verification
    
    Returns:
        JSON with success status and updated image
    """
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        version = data.get('version')
        
        # Update verification status
        result = Image.update_verification_status(
            mongo.mongo,
            image_id,
            'verified',
            current_user['id'],
            version
        )
        
        if result.matched_count == 0:
            return jsonify({
                'success': False,
                'error': 'Version conflict or image not found'
            }), 409
        
        # Create audit entry
        VerificationAudit.create(
            mongo.mongo,
            image_id,
            current_user['id'],
            action='verify',
            notes=data.get('notes')
        )
        
        # Get updated image
        updated_image = Image.find_by_id(mongo.mongo, image_id)
        
        return jsonify({
            'success': True,
            'image': Image.to_dict(updated_image)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/image/<image_id>/reject', methods=['POST'])
@jwt_required
def reject_image(image_id):
    """
    Mark image as rejected
    
    Request Body:
        version: Current version for optimistic locking
        notes: Required notes about why image was rejected
    
    Returns:
        JSON with success status and updated image
    """
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        if not data.get('notes'):
            return jsonify({'success': False, 'error': 'Rejection notes are required'}), 400
        
        version = data.get('version')
        
        # Update verification status
        result = Image.update_verification_status(
            mongo.mongo,
            image_id,
            'rejected',
            current_user['id'],
            version
        )
        
        if result.matched_count == 0:
            return jsonify({
                'success': False,
                'error': 'Version conflict or image not found'
            }), 409
        
        # Create audit entry
        VerificationAudit.create(
            mongo.mongo,
            image_id,
            current_user['id'],
            action='reject',
            notes=data.get('notes')
        )
        
        # Get updated image
        updated_image = Image.find_by_id(mongo.mongo, image_id)
        
        return jsonify({
            'success': True,
            'image': Image.to_dict(updated_image)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/batch/verify', methods=['POST'])
@jwt_required
def batch_verify():
    """
    Verify multiple images at once
    
    Request Body:
        image_ids: List of image IDs to verify
        notes: Optional notes for the batch operation
    
    Returns:
        JSON with success count and any errors
    """
    try:
        current_user = get_current_user()
        data = request.json
        
        if not data or 'image_ids' not in data:
            return jsonify({'success': False, 'error': 'image_ids is required'}), 400
        
        image_ids = data['image_ids']
        notes = data.get('notes')
        
        success_count = 0
        errors = []
        
        for image_id in image_ids:
            try:
                # Update verification status (no version check for batch operations)
                result = Image.update_verification_status(
                    mongo.mongo,
                    image_id,
                    'verified',
                    current_user['id']
                )
                
                if result.matched_count > 0:
                    # Create audit entry
                    VerificationAudit.create(
                        mongo.mongo,
                        image_id,
                        current_user['id'],
                        action='verify',
                        notes=f"Batch verification: {notes}" if notes else "Batch verification"
                    )
                    success_count += 1
                else:
                    errors.append({'image_id': image_id, 'error': 'Image not found'})
                    
            except Exception as e:
                errors.append({'image_id': image_id, 'error': str(e)})
        
        return jsonify({
            'success': True,
            'verified_count': success_count,
            'total_count': len(image_ids),
            'errors': errors
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/batch/reject', methods=['POST'])
@jwt_required
def batch_reject():
    """
    Reject multiple images at once
    
    Request Body:
        image_ids: List of image IDs to reject
        notes: Required notes for the batch rejection
    
    Returns:
        JSON with success count and any errors
    """
    try:
        current_user = get_current_user()
        data = request.json
        
        if not data or 'image_ids' not in data:
            return jsonify({'success': False, 'error': 'image_ids is required'}), 400
        
        if not data.get('notes'):
            return jsonify({'success': False, 'error': 'Rejection notes are required'}), 400
        
        image_ids = data['image_ids']
        notes = data['notes']
        
        success_count = 0
        errors = []
        
        for image_id in image_ids:
            try:
                # Update verification status (no version check for batch operations)
                result = Image.update_verification_status(
                    mongo.mongo,
                    image_id,
                    'rejected',
                    current_user['id']
                )
                
                if result.matched_count > 0:
                    # Create audit entry
                    VerificationAudit.create(
                        mongo.mongo,
                        image_id,
                        current_user['id'],
                        action='reject',
                        notes=f"Batch rejection: {notes}"
                    )
                    success_count += 1
                else:
                    errors.append({'image_id': image_id, 'error': 'Image not found'})
                    
            except Exception as e:
                errors.append({'image_id': image_id, 'error': str(e)})
        
        return jsonify({
            'success': True,
            'rejected_count': success_count,
            'total_count': len(image_ids),
            'errors': errors
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@verification_bp.route('/api/verification/audit/<image_id>', methods=['GET'])
@jwt_required
def get_audit_trail(image_id):
    """
    Get complete audit trail for an image
    
    Returns:
        JSON with audit history
    """
    try:
        audit_entries = VerificationAudit.find_by_image(mongo.mongo, image_id)
        
        return jsonify({
            'success': True,
            'audit_trail': [VerificationAudit.to_dict(entry) for entry in audit_entries],
            'count': len(audit_entries)
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
