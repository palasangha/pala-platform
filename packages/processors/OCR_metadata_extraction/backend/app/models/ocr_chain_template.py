"""
OCR Chain Template model for storing reusable provider chain configurations
"""

from datetime import datetime
from bson import ObjectId


class OCRChainTemplate:
    """OCRChainTemplate model for database operations"""

    @staticmethod
    def create(mongo, user_id, template_data):
        """
        Create a new OCR chain template

        Args:
            mongo: MongoDB connection
            user_id: User ID who created the template
            template_data: Dictionary containing:
                - name: Template name (required)
                - description: Template description (optional)
                - steps: List of step configurations (required)
                - is_public: Whether template is public (default: False)

        Returns:
            Created template document
        """
        template = {
            'user_id': ObjectId(user_id),
            'name': template_data.get('name'),
            'description': template_data.get('description', ''),
            'steps': template_data.get('steps', []),
            'is_public': template_data.get('is_public', False),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        result = mongo.db.ocr_chain_templates.insert_one(template)
        template['_id'] = result.inserted_id
        return template

    @staticmethod
    def find_by_id(mongo, template_id, user_id=None):
        """Find template by MongoDB _id"""
        query = {'_id': ObjectId(template_id)}
        if user_id:
            query['user_id'] = ObjectId(user_id)
        return mongo.db.ocr_chain_templates.find_one(query)

    @staticmethod
    def find_by_user(mongo, user_id, skip=0, limit=50):
        """Find all templates for a user"""
        return list(mongo.db.ocr_chain_templates.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def find_public(mongo, skip=0, limit=50):
        """Find all public templates"""
        return list(mongo.db.ocr_chain_templates.find(
            {'is_public': True}
        ).sort('created_at', -1).skip(skip).limit(limit))

    @staticmethod
    def count_by_user(mongo, user_id):
        """Count total templates for a user"""
        return mongo.db.ocr_chain_templates.count_documents({'user_id': ObjectId(user_id)})

    @staticmethod
    def update(mongo, template_id, user_id, update_data):
        """Update template"""
        update_data['updated_at'] = datetime.utcnow()
        return mongo.db.ocr_chain_templates.update_one(
            {
                '_id': ObjectId(template_id),
                'user_id': ObjectId(user_id)
            },
            {'$set': update_data}
        )

    @staticmethod
    def delete(mongo, template_id, user_id):
        """Delete template"""
        return mongo.db.ocr_chain_templates.delete_one({
            '_id': ObjectId(template_id),
            'user_id': ObjectId(user_id)
        })

    @staticmethod
    def duplicate(mongo, template_id, user_id, new_name):
        """
        Duplicate a template with a new name

        Args:
            mongo: MongoDB connection
            template_id: Template ID to duplicate
            user_id: User ID who owns the template
            new_name: Name for the duplicated template

        Returns:
            Created duplicate template
        """
        original = OCRChainTemplate.find_by_id(mongo, template_id, user_id)
        if not original:
            return None

        new_template = {
            'user_id': original['user_id'],
            'name': new_name,
            'description': original.get('description', ''),
            'steps': original.get('steps', []),
            'is_public': original.get('is_public', False),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        result = mongo.db.ocr_chain_templates.insert_one(new_template)
        new_template['_id'] = result.inserted_id
        return new_template

    @staticmethod
    def validate_chain(steps):
        """
        Validate chain configuration

        Args:
            steps: List of step configurations

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not steps or len(steps) == 0:
            return False, "Chain must have at least one step"

        # Validate step numbers and order
        for i, step in enumerate(steps):
            if step.get('step_number') != i + 1:
                return False, f"Step numbers must be sequential (expected {i+1}, got {step.get('step_number')})"

            if not step.get('provider'):
                return False, f"Step {i+1} must have a provider"

            input_source = step.get('input_source', 'original_image')
            if input_source not in ['original_image', 'previous_step', 'step_N', 'combined']:
                return False, f"Step {i+1} has invalid input_source: {input_source}"

            # Validate input source references
            if input_source == 'previous_step' and i == 0:
                return False, "Step 1 cannot use 'previous_step' as input"

            # Check for circular dependencies (simplified check)
            if input_source == 'step_N':
                input_steps = step.get('input_step_numbers', [])
                if not input_steps:
                    return False, f"Step {i+1} has input_source='step_N' but no input_step_numbers"

                for input_step_num in input_steps:
                    if input_step_num >= step.get('step_number', i+1):
                        return False, f"Step {i+1} cannot reference step {input_step_num} (cannot reference self or future steps)"

            elif input_source == 'combined':
                input_steps = step.get('input_step_numbers', [])
                if not input_steps:
                    return False, f"Step {i+1} has input_source='combined' but no input_step_numbers"

                for input_step_num in input_steps:
                    if input_step_num >= step.get('step_number', i+1):
                        return False, f"Step {i+1} cannot reference step {input_step_num} (cannot reference self or future steps)"

        return True, None

    @staticmethod
    def to_dict(template):
        """Convert template document to dictionary"""
        if not template:
            return None

        return {
            'id': str(template['_id']),
            'user_id': str(template.get('user_id')),
            'name': template.get('name'),
            'description': template.get('description', ''),
            'steps': template.get('steps', []),
            'is_public': template.get('is_public', False),
            'created_at': template.get('created_at').isoformat() if template.get('created_at') else None,
            'updated_at': template.get('updated_at').isoformat() if template.get('updated_at') else None,
        }
