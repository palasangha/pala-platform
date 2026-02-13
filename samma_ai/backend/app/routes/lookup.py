"""
Lookup Routes - Pali word lookup, sutta search, references
"""

from flask import Blueprint, request, jsonify
from app.services.tipitaka_service import TipitakaService

lookup_bp = Blueprint('lookup', __name__)
tipitaka_service = TipitakaService()


@lookup_bp.route('/lookup/<word>', methods=['GET'])
def lookup_word(word):
    """
    Look up a Pali word.

    Returns:
        {
            "word": "dukkha",
            "meaning": "suffering, unsatisfactoriness",
            "etymology": "...",
            "occurrences": 1234,
            "related_terms": [...]
        }
    """
    try:
        result = tipitaka_service.lookup_pali_word(word)
        if result:
            return jsonify(result)
        return jsonify({'error': 'Word not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lookup_bp.route('/sutta/<reference>', methods=['GET'])
def get_sutta(reference):
    """
    Get a sutta by reference (e.g., MN 10, DN 22).

    Returns:
        {
            "reference": "MN 10",
            "name_pali": "Satipatthana Sutta",
            "name_english": "The Discourse on Establishing Mindfulness",
            "paragraphs": [...],
            "tpr_reference": "...",
            "xml_reference": "..."
        }
    """
    try:
        result = tipitaka_service.get_sutta_by_reference(reference)
        if result:
            return jsonify(result)
        return jsonify({'error': 'Sutta not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@lookup_bp.route('/search', methods=['GET'])
def search():
    """
    Full-text search in Tipitaka.

    Query params:
        q: search query
        limit: max results (default 20)
        offset: pagination offset

    Returns:
        {
            "query": "mindfulness",
            "total": 142,
            "results": [...]
        }
    """
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400

    try:
        results = tipitaka_service.full_text_search(query, limit, offset)
        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
