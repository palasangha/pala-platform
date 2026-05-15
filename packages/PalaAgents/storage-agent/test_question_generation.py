"""
Tests for Question Generation and Storage

Tests the end-to-end flow:
1. Question generation for documents
2. Storage and retrieval
3. Vector similarity search
4. Regeneration after metadata changes
"""

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure local imports resolve when the test is run directly.
sys.path.append(str(Path(__file__).resolve().parent))

# Setup logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EmbeddingArray:
    """Simple wrapper that mimics numpy array behavior"""
    def __init__(self, data):
        self.data = data
    
    def tolist(self):
        return self.data


class MockEmbeddingModel:
    """Mock SentenceTransformer for testing"""
    def encode(self, text):
        """Generate a simple deterministic embedding as array-like object"""
        import hashlib
        # Create a 384-dimensional embedding (MiniLM size) based on text hash
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()  # 32 bytes
        
        embedding = []
        for i in range(384):
            # Use hash bytes cyclically, normalized to [-1, 1]
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val - 128) / 128.0)
        # Return as object with .tolist() method (like numpy arrays)
        return EmbeddingArray(embedding)


class MockOllamaProvider:
    """Mock Ollama provider for testing"""
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "mistral"
    
    async def generate_text_response(self, prompt):
        """Mock response for question generation"""
        # Return canned questions based on prompt content
        if "question" in prompt.lower():
            return """What is the main topic discussed in this document?
How does this relate to the historical context?
Who are the key figures mentioned?
What is the significance of the date provided?
What locations are referenced in this document?
What practical insights can be gained?
How does this document reflect the time period?
What questions would a researcher ask about this?"""
        return ""


async def test_evidence_snippet_preserves_line_window():
    """Test that extracted evidence keeps a readable 6-12 line window."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 0: Evidence Snippet Line Window")
    logger.info("=" * 80)

    from question_generator import QuestionGenerator

    gen = QuestionGenerator(MockOllamaProvider())
    question_text = "Why is right livelihood (sammā-ājīva) important in Buddhism?"

    processed_data = {
        "content": "\n".join([
            "Intro line 1 about the discourse.",
            "Intro line 2 about the discourse.",
            "Intro line 3 about the discourse.",
            "Intro line 4 about the discourse.",
            "Right livelihood helps one earn without harming others.",
            "This is part of moral conduct and daily practice.",
            "The teaching continues with practical examples.",
            "Additional explanation about avoiding harm.",
            "More context about the Eightfold Noble Path.",
            "Final line that closes the context window.",
        ])
    }

    evidence, answer_preview = gen._extract_evidence_for_question(question_text, processed_data)

    assert evidence, "Expected evidence to be returned"
    lines = answer_preview.splitlines()
    assert 6 <= len(lines) <= 12, f"Expected 6-12 lines, got {len(lines)}: {lines}"
    assert any("right livelihood" in line.lower() for line in lines), "Expected the matched line in the snippet"

    logger.info(f"✓ Evidence snippet returned {len(lines)} lines")
    for line in lines:
        logger.info(f"  {line}")

    return True


async def test_question_generation():
    """Test basic question generation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Basic Question Generation")
    logger.info("="*80)
    
    from question_generator import QuestionGenerator
    
    mock_ollama = MockOllamaProvider()
    gen = QuestionGenerator(mock_ollama)
    
    # Mock document
    doc_id = "test-doc-001"
    doc_type = "letter"
    metadata = {
        "pala_metadata": {
            "content": {
                "title": "Historical Letter from 1970",
                "summary": "A letter discussing Buddhist practices",
                "language": "en",
                "date_info": {"date_string": "1970-03-15"},
                "topics": {"topics": ["Buddhism", "Meditation", "Teaching"]},
            },
            "places": {
                "locations": [
                    {"name": "Bodh Gaya"},
                    {"name": "India"},
                ]
            },
            "parties": {
                "people": [
                    {"name": "Sayadaw U Pandita"},
                    {"name": "John Smith"},
                ]
            },
        },
        "app_data": {
            "tags": ["historical", "spiritual"],
        }
    }
    processed_data = {
        "content": "This is a sample letter discussing Buddhist meditation practices and teachings..."
    }
    original_file = "letter_1970.pdf"
    
    embedding_model = MockEmbeddingModel()
    
    # Patch the _call_ollama method
    async def mock_call_ollama(prompt):
        return await mock_ollama.generate_text_response(prompt)
    
    gen._call_ollama = mock_call_ollama
    
    questions = await gen.generate_questions_for_document(
        doc_id, doc_type, metadata, processed_data, original_file, embedding_model
    )
    
    assert len(questions) > 0, "Should generate questions"
    # Check that embeddings were generated (they may be None for some, but at least some should have them)
    assert any(q.embedding is not None for q in questions), "At least some questions should be embedded"
    assert all(q.provenance == doc_id for q in questions), "All questions should have correct provenance"
    
    logger.info(f"✓ Generated {len(questions)} questions")
    embedded_count = sum(1 for q in questions if q.embedding is not None)
    logger.info(f"✓ Embedded {embedded_count}/{len(questions)} questions")
    for i, q in enumerate(questions, 1):
        logger.info(f"  {i}. {q.text}")
    
    return True


async def test_questions_storage():
    """Test storing and retrieving questions"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Questions Storage and Retrieval")
    logger.info("="*80)
    
    from questions_db import QuestionsDB
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_questions.db"
        db = QuestionsDB(str(db_path))
        
        # Store a question
        q_id = "q-001"
        text = "What is the main topic?"
        provenance = "doc-001"
        filters = {"tags": ["test"], "language": "en"}
        embedding = [0.1, 0.2, 0.3] * 128  # 384 dims
        
        stored = db.store_question(
            q_id, text, provenance, filters, "question",
            embedding, "2026-05-11T00:00:00Z", "2026-05-11T00:00:00Z", "ollama"
        )
        
        assert stored, "Question should be stored"
        logger.info("✓ Stored question")
        
        # Retrieve questions for document
        questions = db.get_questions_for_document(provenance)
        assert len(questions) == 1, "Should retrieve stored question"
        assert questions[0]["text"] == text, "Retrieved question text should match"
        
        logger.info(f"✓ Retrieved {len(questions)} question(s)")
        
        return True


async def test_batch_storage():
    """Test batch storing questions"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Batch Storage")
    logger.info("="*80)
    
    from questions_db import QuestionsDB
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_batch.db"
        db = QuestionsDB(str(db_path))
        
        # Create batch of questions
        questions_batch = []
        for i in range(5):
            questions_batch.append({
                "question_id": f"q-{i:03d}",
                "text": f"Question number {i+1}?",
                "provenance": "doc-batch-001",
                "filters": {"tags": ["batch"]},
                "suggestion_type": "question",
                "embedding": [0.1] * 384,
                "created_at": "2026-05-11T00:00:00Z",
                "updated_at": "2026-05-11T00:00:00Z",
                "model": "ollama",
            })
        
        stored_count = db.store_questions_batch(questions_batch)
        assert stored_count == 5, "Should store all questions"
        
        logger.info(f"✓ Batch stored {stored_count} questions")
        
        # Verify retrieval
        retrieved = db.get_questions_for_document("doc-batch-001")
        assert len(retrieved) == 5, "Should retrieve all batch questions"
        
        logger.info(f"✓ Retrieved {len(retrieved)} questions")
        
        return True


async def test_generation_status_tracking():
    """Test tracking generation status"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Generation Status Tracking")
    logger.info("="*80)
    
    from questions_db import QuestionsDB
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_status.db"
        db = QuestionsDB(str(db_path))
        
        doc_id = "doc-status-001"
        
        # Mark as generating
        db.mark_generation_status(doc_id, "generating")
        status = db.get_generation_status(doc_id)
        assert status["status"] == "generating", "Should track generating status"
        logger.info("✓ Marked as generating")
        
        # Mark as generated
        db.mark_generation_status(doc_id, "generated", question_count=8)
        status = db.get_generation_status(doc_id)
        assert status["status"] == "generated", "Should track generated status"
        assert status["question_count"] == 8, "Should track question count"
        logger.info(f"✓ Marked as generated with {status['question_count']} questions")
        
        # Mark as failed
        db.mark_generation_status(doc_id + "-2", "failed", error_message="Test error")
        status = db.get_generation_status(doc_id + "-2")
        assert status["status"] == "failed", "Should track failed status"
        assert status["error_message"] == "Test error", "Should track error message"
        logger.info(f"✓ Marked as failed with error: {status['error_message']}")
        
        return True


async def test_vector_similarity_search():
    """Test vector similarity search"""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Vector Similarity Search")
    logger.info("="*80)
    
    from questions_db import QuestionsDB
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_search.db"
        db = QuestionsDB(str(db_path))
        
        embedding_model = MockEmbeddingModel()
        
        # Store sample questions
        questions = [
            "What is Buddhism?",
            "How do you meditate?",
            "What are the four noble truths?",
            "Where is Bodh Gaya?",
            "Who was the Buddha?",
        ]
        
        for i, q_text in enumerate(questions):
            embedding = embedding_model.encode(q_text)
            # Convert to list for storage
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
            db.store_question(
                f"q-{i:03d}", q_text, f"doc-{i:03d}", {}, "question",
                embedding_list, "2026-05-11T00:00:00Z", "2026-05-11T00:00:00Z", "ollama"
            )
        
        logger.info(f"✓ Stored {len(questions)} sample questions")
        
        # Search for similar questions
        query = "Buddhist meditation practice"
        query_embedding = embedding_model.encode(query)
        # Convert to list for search
        query_embedding_list = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else query_embedding
        
        results = db.search_questions_by_embedding(query_embedding_list, top_k=3, similarity_threshold=0.0)
        
        assert len(results) > 0, "Should find similar questions"
        logger.info(f"✓ Found {len(results)} similar questions for query: '{query}'")
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. {result['text']} (similarity: {result['similarity']:.3f})")
        
        return True


async def test_regeneration():
    """Test question regeneration"""
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Question Regeneration")
    logger.info("="*80)
    
    from questions_db import QuestionsDB
    from question_generator import QuestionGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_regen.db"
        db = QuestionsDB(str(db_path))
        
        doc_id = "doc-regen-001"
        
        # Store initial questions
        initial_questions = [
            {
                "question_id": f"q-initial-{i}",
                "text": f"Initial question {i+1}?",
                "provenance": doc_id,
                "filters": {},
                "suggestion_type": "question",
                "embedding": [0.1] * 384,
                "created_at": "2026-05-11T00:00:00Z",
                "updated_at": "2026-05-11T00:00:00Z",
                "model": "ollama",
            }
            for i in range(3)
        ]
        
        db.store_questions_batch(initial_questions)
        initial_count = len(db.get_questions_for_document(doc_id))
        assert initial_count == 3, "Should have initial questions"
        logger.info(f"✓ Stored {initial_count} initial questions")
        
        # Delete and regenerate
        deleted = db.delete_questions_for_document(doc_id)
        assert deleted == 3, "Should delete all initial questions"
        logger.info(f"✓ Deleted {deleted} initial questions")
        
        # Store new questions
        new_questions = [
            {
                "question_id": f"q-new-{i}",
                "text": f"Updated question {i+1}?",
                "provenance": doc_id,
                "filters": {"updated": True},
                "suggestion_type": "question",
                "embedding": [0.2] * 384,
                "created_at": "2026-05-11T01:00:00Z",
                "updated_at": "2026-05-11T01:00:00Z",
                "model": "ollama",
            }
            for i in range(5)
        ]
        
        db.store_questions_batch(new_questions)
        new_count = len(db.get_questions_for_document(doc_id))
        assert new_count == 5, "Should have regenerated questions"
        logger.info(f"✓ Regenerated {new_count} new questions")
        
        return True


async def main():
    """Run all tests"""
    logger.info("\n" + "="*80)
    logger.info("QUESTION GENERATION FEATURE - COMPREHENSIVE TESTS")
    logger.info("="*80 + "\n")
    
    tests = [
        ("Question Generation", test_question_generation),
        ("Storage and Retrieval", test_questions_storage),
        ("Batch Storage", test_batch_storage),
        ("Status Tracking", test_generation_status_tracking),
        ("Vector Search", test_vector_similarity_search),
        ("Regeneration", test_regeneration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASS", None))
        except AssertionError as e:
            results.append((test_name, "FAIL", str(e)))
            logger.error(f"✗ {test_name} failed: {e}")
        except Exception as e:
            results.append((test_name, "ERROR", str(e)))
            logger.error(f"✗ {test_name} error: {e}", exc_info=True)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    errors = sum(1 for _, status, _ in results if status == "ERROR")
    
    for test_name, status, error_msg in results:
        icon = "✓" if status == "PASS" else "✗"
        logger.info(f"{icon} {test_name}: {status}")
        if error_msg:
            logger.info(f"  └─ {error_msg}")
    
    logger.info("\n" + "-"*80)
    logger.info(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
    logger.info("="*80 + "\n")
    
    return failed == 0 and errors == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
