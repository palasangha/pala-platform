"""
Chat Routes - Handle chat interactions with Samma AI using multi-model routing
"""

import uuid
import traceback
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app.services.model_router_service import ModelRouterService
from app.services.tipitaka_service import TipitakaService
from app.services.response_formatter import ResponseFormatter
from app import mongo

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)
model_router = ModelRouterService()
tipitaka_service = TipitakaService()
response_formatter = ResponseFormatter()


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Process a chat message and return a strict 8-part Dhamma response.
    """
    request_id = str(uuid.uuid4())[:8]          # short ID for log correlation
    logger.info("[chat] ── NEW REQUEST ── request_id=%s", request_id)

    # ── Input validation ──────────────────────────────────────────────────────
    data = request.get_json(silent=True)
    if not data:
        logger.warning("[chat:%s] STEP 0 FAILED — request body is empty or not JSON.", request_id)
        return jsonify({'error': 'Request body must be JSON'}), 400

    if 'message' not in data:
        logger.warning(
            "[chat:%s] STEP 0 FAILED — 'message' key missing from body. keys=%s",
            request_id, list(data.keys()),
        )
        return jsonify({'error': 'Message is required'}), 400

    message          = data['message']
    conversation_id  = data.get('conversation_id', str(uuid.uuid4()))
    model_id         = data.get('model_id', 'copilot')

    logger.info(
        "[chat:%s] STEP 0 OK — message=%.80r  model_id=%s  conversation_id=%s",
        request_id, message, model_id, conversation_id,
    )

    try:
        # ── STEP 1: Tipitaka search ───────────────────────────────────────────
        logger.info("[chat:%s] STEP 1 — querying Tipitaka for relevant passages...", request_id)
        try:
            passages = tipitaka_service.search_relevant_passages(message)
            logger.info(
                "[chat:%s] STEP 1 OK — found %d passage(s).  passage_ids=%s",
                request_id, len(passages),
                [p.get('id') for p in passages[:5]],
            )
            if not passages:
                logger.warning(
                    "[chat:%s] STEP 1 WARNING — zero passages returned for message=%.80r. "
                    "LLM will receive no Tipitaka context. Check vector/FTS5/keyword search logs.",
                    request_id, message,
                )
        except Exception as exc:
            logger.error(
                "[chat:%s] STEP 1 FAILED — tipitaka_service.search_relevant_passages raised. "
                "message=%.80r  error=%s\n%s",
                request_id, message, exc, traceback.format_exc(),
            )
            raise

        # ── STEP 1.5: Enrich passages with translations ──────────────────────
        logger.info("[chat:%s] STEP 1.5 — enriching passages with translations...", request_id)
        try:
            translation_service = current_app.extensions.get('translation_service')
            if translation_service:
                passages = translation_service.enrich_passages_with_translations(passages)
                translated_count = sum(
                    1 for p in passages if p.get('translation_source') == 'ollama'
                )
                logger.info(
                    "[chat:%s] STEP 1.5 OK — enriched %d passages with Deepseek translations",
                    request_id, translated_count
                )
            else:
                logger.debug("[chat:%s] STEP 1.5 SKIPPED — translation service not available", request_id)
        except Exception as exc:
            logger.warning(
                "[chat:%s] STEP 1.5 WARNING — translation enrichment failed (non-critical). "
                "Continuing with original Pali. error=%s",
                request_id, exc
            )

        # ── STEP 2: Generate LLM response ────────────────────────────────────
        logger.info(
            "[chat:%s] STEP 2 — generating Dhamma response via model_id=%s ...",
            request_id, model_id,
        )
        try:
            response = model_router.generate_dhamma_response(
                question=message,
                passages=passages,
                model_id=model_id,
            )
            # Summarise which sections are non-empty
            non_empty = [k for k, v in response.items()
                         if k != 'raw_response' and v]
            empty = [k for k, v in response.items()
                     if k != 'raw_response' and not v]
            logger.info(
                "[chat:%s] STEP 2 OK — model_id=%s  non_empty_sections=%s  empty_sections=%s  "
                "canonical_teachings_count=%d  raw_response_len=%d",
                request_id, model_id, non_empty, empty,
                len(response.get('canonical_teachings', [])),
                len(response.get('raw_response', '')),
            )
            if empty:
                logger.warning(
                    "[chat:%s] STEP 2 WARNING — these response sections are empty: %s. "
                    "This usually means the LLM did not follow the 8-part format, or "
                    "passages were irrelevant. raw_response (first 300 chars): %.300s",
                    request_id, empty, response.get('raw_response', ''),
                )
        except Exception as exc:
            logger.error(
                "[chat:%s] STEP 2 FAILED — model_router.generate_dhamma_response raised. "
                "model_id=%s  passages_count=%d  error=%s\n%s",
                request_id, model_id, len(passages), exc, traceback.format_exc(),
            )
            raise

        # ── STEP 3: Format response ───────────────────────────────────────────
        logger.info("[chat:%s] STEP 3 — formatting response...", request_id)
        try:
            formatted_response = response_formatter.format_dhamma_response(response, passages)
            logger.info(
                "[chat:%s] STEP 3 OK — formatted_text_len=%d  canonical_teachings=%d",
                request_id,
                len(formatted_response.get('formatted_text', '')),
                len(formatted_response.get('canonical_teachings', [])),
            )
        except Exception as exc:
            logger.error(
                "[chat:%s] STEP 3 FAILED — response_formatter.format_dhamma_response raised. "
                "error=%s\n%s",
                request_id, exc, traceback.format_exc(),
            )
            raise

        # ── STEP 4: Persist to MongoDB (non-blocking) ─────────────────────────
        response_id = str(uuid.uuid4())
        logger.info("[chat:%s] STEP 4 — saving to MongoDB (response_id=%s)...", request_id, response_id)
        try:
            mongo.db.conversations.insert_one({
                'id': response_id,
                'conversation_id': conversation_id,
                'message': message,
                'model_used': model_id,
                'response': formatted_response,
                'passages_used': [str(p.get('id')) for p in passages],
                'timestamp': datetime.utcnow(),
            })
            logger.info("[chat:%s] STEP 4 OK — saved to MongoDB.", request_id)
        except Exception as mongo_error:
            logger.warning(
                "[chat:%s] STEP 4 WARNING — MongoDB save failed (non-fatal). "
                "error=%s\n%s",
                request_id, mongo_error, traceback.format_exc(),
            )

        # ── STEP 5: Build and return JSON ─────────────────────────────────────
        def sanitize_for_json(obj):
            if isinstance(obj, dict):
                return {k: sanitize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_for_json(v) for v in obj]
            elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'ObjectId':
                return str(obj)
            return obj

        response_data = {
            'id': response_id,
            'conversation_id': conversation_id,
            'model_used': model_id,
            'raw_response': response.get('raw_response', ''),
            'response': formatted_response,
            'passages': [
                {
                    'id': str(p.get('id')),
                    'pali_text': p.get('pali_text'),
                    'english_text': p.get('english_text'),  # NEW: from DB or translation
                    'translation_source': p.get('translation_source', 'db'),  # NEW: 'db' or 'ollama'
                    'xml_source': p.get('xml_source_file'),
                    'paragraph_number': p.get('paragraph_number'),
                }
                for p in passages
            ],
            'timestamp': datetime.utcnow().isoformat(),
        }

        logger.info(
            "[chat:%s] ── COMPLETE ── response_id=%s  passages=%d  "
            "canonical_teachings=%d",
            request_id, response_id, len(passages),
            len(formatted_response.get('canonical_teachings', [])),
        )
        return jsonify(sanitize_for_json(response_data))

    except Exception as exc:
        logger.error(
            "[chat:%s] UNHANDLED EXCEPTION — message=%.80r  model_id=%s  "
            "error=%s\n%s",
            request_id, message, model_id, exc, traceback.format_exc(),
        )
        return jsonify({'error': str(exc)}), 500


@chat_bp.route('/chat/history/<conversation_id>', methods=['GET'])
def get_history(conversation_id):
    """Get chat history for a conversation."""
    logger.debug("[chat.get_history] conversation_id=%s", conversation_id)
    try:
        history = list(mongo.db.conversations.find(
            {'conversation_id': conversation_id},
            {'_id': 0},
        ).sort('timestamp', 1))
        logger.info(
            "[chat.get_history] conversation_id=%s  messages=%d",
            conversation_id, len(history),
        )
        return jsonify({'conversation_id': conversation_id, 'messages': history})
    except Exception as exc:
        logger.error(
            "[chat.get_history] FAILED — conversation_id=%s  error=%s\n%s",
            conversation_id, exc, traceback.format_exc(),
        )
        return jsonify({'error': str(exc)}), 500
