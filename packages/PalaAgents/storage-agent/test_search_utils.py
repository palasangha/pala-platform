import asyncio
import tempfile

import pytest

from main import _first_text_from_nested
from search_utils import (
    build_document_search_index,
    extract_passage_around_query,
    extract_line_window_around_query,
    format_search_document_result,
    split_text_into_chunks,
)
from sqlite_provider import SQLiteProvider


def test_first_text_from_nested_extracts_deep_text():
    payload = {
        "success": True,
        "result": {
            "pala_metadata": {
                "content": {
                    "summary": {
                        "text": "This is the extracted summary text.",
                        "confidence": 1,
                    },
                    "topics": {"topics": ["meditation", "retreat"]},
                }
            }
        },
    }

    text = _first_text_from_nested(payload)

    assert text == "This is the extracted summary text."


def test_split_text_into_chunks_creates_overlap_and_passages():
    text = "Paragraph one about Paris peace talks. " + ("A" * 1000) + " Final section mentions New Delhi and India."

    chunks = split_text_into_chunks(text, chunk_size=200, overlap=40)

    assert len(chunks) >= 2
    assert chunks[0]["chunk_index"] == 0
    assert "Paris peace talks" in chunks[0]["text"]
    assert chunks[0]["end_char"] > chunks[0]["start_char"]


def test_extract_passage_around_query_prefers_hit_window():
    content = "Intro text. The Paris Peace Talks were discussed in detail with India. Closing text."

    passage = extract_passage_around_query(content, ["Paris", "India"], window_size=20)

    assert "Paris Peace Talks" in passage
    assert "Intro text" in passage or "The Paris" in passage


def test_extract_line_window_around_query_includes_surrounding_lines():
    content = "Line 1\nLine 2\nThe mother appeared here\nLine 4\nLine 5\nLine 6"

    window = extract_line_window_around_query(content, ["mother"], window_lines=3)

    assert "Line 1" in window
    assert "The mother appeared here" in window
    assert "Line 6" in window


def test_build_document_search_index_adds_chunks_and_embeddings():
    metadata = {"summary": "A memo about Vietnam negotiations.", "topics": ["Vietnam", "peace talks"]}
    processed_data = {
        "result": {
            "pala_metadata": {
                "content": {
                    "summary": {
                        "text": "Vietnam negotiations were discussed in Paris and New Delhi.",
                        "confidence": 1,
                    }
                }
            }
        }
    }

    def fake_embedding(text: str):
        return [float(len(text)), 1.0]

    index = build_document_search_index(
        metadata=metadata,
        processed_data=processed_data,
        original_file="memo.pdf",
        generate_embedding_fn=fake_embedding,
        chunk_size=40,
        overlap=10,
    )

    assert index["search_index_version"] == 1
    assert index["embedding_generated"] is True
    assert index["embedding_vector"] is not None
    assert index["search_chunk_count"] >= 1
    assert index["search_content_length"] > 0
    assert any(chunk["source"] == "processed_data.content" for chunk in index["search_chunks"])
    assert any(chunk["source"] == "metadata.summary" for chunk in index["search_chunks"])


def test_format_search_document_result_includes_passage_fields():
    formatted = format_search_document_result(
        {
            "document_id": "doc-1",
            "original_file": "memo.pdf",
            "type": "memo",
            "relevance_score": 0.91,
            "created_at": "2026-05-05T00:00:00Z",
            "summary": "Summary text",
            "topics": ["topic"],
            "places": ["place"],
            "excerpt": "Passage excerpt",
            "matched_text": "Real passage text",
            "matched_path": "processed_data.content",
            "match_method": "semantic_chunk",
            "match_reason": "Content match in processed_data.content",
            "matched_chunk_index": 3,
            "matched_chunk_start": 90,
            "matched_chunk_end": 210,
            "original_file_data": "abc",
        },
        rank=1,
        include_original=True,
    )

    assert formatted["matched_text"] == "Real passage text"
    assert formatted["matched_path"] == "processed_data.content"
    assert formatted["match_reason"] == "Content match in processed_data.content"
    assert formatted["matched_chunk_index"] == 3
    assert formatted["original_file_data"] == "abc"


def test_sqlite_search_returns_chunk_passage(tmp_path):
    async def run_test():
        db_path = tmp_path / "storage.db"
        provider = SQLiteProvider(db_path=str(db_path))

        processed_data = {
            "content": "The Paris Peace Talks were discussed in New Delhi with India as a key participant.",
        }
        metadata = {"summary": "Diplomatic memo about Vietnam and Paris negotiations."}
        app_data = {
            "embedding_vector": [1.0, 0.0],
            "search_chunks": [
                {
                    "chunk_index": 0,
                    "text": "The Paris Peace Talks were discussed in New Delhi with India as a key participant.",
                    "start_char": 0,
                    "end_char": 92,
                    "source": "processed_data.content",
                    "kind": "content",
                    "embedding_vector": [1.0, 0.0],
                },
                {
                    "chunk_index": 1,
                    "text": "Diplomatic memo about Vietnam and Paris negotiations.",
                    "start_char": None,
                    "end_char": None,
                    "source": "metadata.summary",
                    "kind": "metadata",
                    "embedding_vector": [0.0, 1.0],
                },
            ],
        }

        await provider.store_document(
            type="memo",
            original_file="memo.pdf",
            file_format="pdf",
            processed_data=processed_data,
            metadata=metadata,
            app_data=app_data,
            created_by="pytest",
            file_hash="hash-1",
        )

        results = await provider.search_documents(
            query="Paris Peace Talks",
            query_embedding=[1.0, 0.0],
            limit=5,
            min_confidence=0.2,
        )

        assert results
        top = results[0]
        assert "Paris Peace Talks" in top["matched_text"]
        assert top["matched_path"] == "processed_data.content"
        assert top["match_method"] in {"semantic_chunk", "keyword_chunk"}
        assert top["match_reason"] in {"Content match in processed_data.content", "Metadata and Content match"}
        assert top["matched_chunk_index"] == 0
        assert "Paris Peace Talks" in top["excerpt"]

    asyncio.run(run_test())