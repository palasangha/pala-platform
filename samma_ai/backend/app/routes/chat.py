"""
Chat Routes - Handle chat interactions with Samma AI using multi-model routing
"""

from flask import Blueprint, request, jsonify
from app.services.model_router_service import ModelRouterService
from app.services.tipitaka_service import TipitakaService
from app.services.response_formatter import ResponseFormatter
from app import mongo
import uuid
from datetime import datetime

chat_bp = Blueprint('chat', __name__)
model_router = ModelRouterService()
tipitaka_service = TipitakaService()
response_formatter = ResponseFormatter()


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Process a chat message and return a strict 8-part Dhamma response.
    
    Request:
        {
            "message": "What is the nature of suffering?",
            "conversation_id": "optional-uuid",
            "model_id": "optional-model-id (defaults to claude-sonnet-4-20250514)"
        }
    
    Response:
        {
            "id": "response-uuid",
            "conversation_id": "conversation-uuid",
            "model_used": "claude-sonnet-4-20250514",
            "response": {
                "direct_definition": "...",
                "interpretive_insight": "...",
                "canonical_teachings": [...],
                "commentary": "...",
                "tika_clarification": "...",
                "lexical_analysis": "...",
                "doctrinal_function": "...",
                "final_summary": "...",
                "formatted_text": "..."
            },
            "timestamp": "2026-02-09T10:00:00Z"
        }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    message = data['message']
    conversation_id = data.get('conversation_id', str(uuid.uuid4()))
    model_id = data.get('model_id', 'claude-sonnet-4-20250514')

    try:
        # Step 1: Query Tipitaka database for relevant passages
        passages = tipitaka_service.search_relevant_passages(message)

        # Step 2: Generate 4-part response using ModelRouter (supports Claude/OpenAI/Ollama/Copilot)
        response = model_router.generate_dhamma_response(
            question=message,
            passages=passages,
            model_id=model_id
        )

        # Step 3: Format response according to strict Samma AI protocol
        formatted_response = response_formatter.format_dhamma_response(response, passages)
        
        # Step 4: Save to MongoDB (optional - don't block on failure)
        response_id = str(uuid.uuid4())
        try:
            mongo.db.conversations.insert_one({
                'id': response_id,
                'conversation_id': conversation_id,
                'message': message,
                'model_used': model_id,
                'response': formatted_response,
                'passages_used': [str(p.get('id')) for p in passages],
                'timestamp': datetime.utcnow()
            })
        except Exception as mongo_error:
            # Log but don't fail - MongoDB is optional
            from flask import current_app
            current_app.logger.warning(f"Failed to save conversation to MongoDB: {mongo_error}")

        def sanitize_for_json(obj):
            if isinstance(obj, dict):
                return {k: sanitize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_for_json(v) for v in obj]
            elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'ObjectId':
                return str(obj)
            else:
                return obj

        response_data = {
            'id': response_id,
            'conversation_id': conversation_id,
            'model_used': model_id,
            'response': formatted_response,
            'passages': [
                {
                    'id': str(p.get('id')),
                    'pali_text': p.get('pali_text'),
                    'xml_source': p.get('xml_source_file'),
                    'paragraph_number': p.get('paragraph_number')
                }
                for p in passages
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(sanitize_for_json(response_data))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/chat/history/<conversation_id>', methods=['GET'])
def get_history(conversation_id):
    """Get chat history for a conversation."""
    try:
        history = list(mongo.db.conversations.find(
            {'conversation_id': conversation_id},
            {'_id': 0}
        ).sort('timestamp', 1))

        return jsonify({
            'conversation_id': conversation_id,
            'messages': history
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
