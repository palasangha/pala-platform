from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _collect_text(value: Any, fragments: List[str]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key == "embedding_vector":
                continue
            _collect_text(nested_value, fragments)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text(item, fragments)
        return
    if isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        if text:
            fragments.append(text)


def combine_searchable_text(metadata: Dict[str, Any], processed_data: Dict[str, Any], original_file: str) -> str:
    """Combine metadata, extracted text, and file info into searchable text."""
    parts: List[str] = []

    if original_file:
        parts.append(f"File: {original_file}")

    if metadata and isinstance(metadata, dict):
        pala = metadata.get("pala_metadata", {})
        if isinstance(pala, dict):
            content = pala.get("content", {}) if isinstance(pala.get("content"), dict) else {}
            if content.get("summary"):
                parts.append(f"Summary: {content['summary']}")
            if content.get("topics"):
                topics = content["topics"]
                if isinstance(topics, dict):
                    topics_list = topics.get("topics", [])
                else:
                    topics_list = topics
                parts.append(f"Topics: {', '.join(str(t) for t in topics_list)}")

            parties = pala.get("parties", {})
            if isinstance(parties, dict):
                people = parties.get("people", [])
                if people:
                    names = [p.get("name") for p in people if isinstance(p, dict) and p.get("name")]
                    if names:
                        parts.append(f"People: {', '.join(names)}")

            places = pala.get("places", {})
            if isinstance(places, dict):
                locations = places.get("locations", [])
                if locations:
                    loc_names = [loc.get("name") for loc in locations if isinstance(loc, dict) and loc.get("name")]
                    if loc_names:
                        parts.append(f"Places: {', '.join(loc_names)}")

    if processed_data and isinstance(processed_data, dict):
        if processed_data.get("extracted_fields"):
            extracted = processed_data["extracted_fields"]
            if isinstance(extracted, dict):
                if extracted.get("summary"):
                    parts.append(f"Extracted Summary: {extracted['summary']}")
                if extracted.get("key_topics"):
                    topics = extracted["key_topics"]
                    if topics:
                        parts.append(f"Extracted Topics: {', '.join(str(t) for t in topics)}")

        for key in ("content", "text", "ocr_text"):
            value = processed_data.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(f"Content: {value[:2000]}")
                break

        if processed_data.get("result"):
            _collect_text(processed_data.get("result"), parts)

    searchable_text = "\n".join(parts)
    logger.debug("[SEARCH-UTILS] Combined searchable text length=%d", len(searchable_text))
    return searchable_text


def split_text_into_chunks(text: str, chunk_size: int = 900, overlap: int = 150) -> List[Dict[str, Any]]:
    """Split text into overlapping character chunks."""
    if not text:
        return []

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunk_size = max(int(chunk_size), 100)
    overlap = max(0, min(int(overlap), chunk_size - 1))
    step = max(1, chunk_size - overlap)

    chunks: List[Dict[str, Any]] = []
    start = 0
    index = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunk_text = normalized[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_index": index,
                    "text": chunk_text,
                    "start_char": start,
                    "end_char": end,
                }
            )
            index += 1
        if end >= len(normalized):
            break
        start += step
    return chunks


def extract_passage_around_query(content: str, query_terms: List[str], window_size: int = 150) -> str:
    """Extract a passage around the first query term match."""
    if not content:
        return ""
    if not query_terms:
        return content[:300]

    content_lower = content.lower()
    best_pos = -1
    best_term = ""
    for term in query_terms:
        term_lower = term.lower().strip()
        if not term_lower:
            continue
        pos = content_lower.find(term_lower)
        if pos >= 0 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_term = term_lower

    if best_pos == -1:
        return content[:300]

    start = max(0, best_pos - window_size)
    end = min(len(content), best_pos + len(best_term) + window_size)
    passage = content[start:end].strip()

    if not passage:
        return content[:300]
    return passage


def _tokenize_search_text(text: str) -> List[str]:
    stopwords = {
        "a", "an", "are", "as", "at", "be", "by", "do", "does", "for", "from",
        "have", "in", "is", "it", "of", "on", "or", "the", "to", "was", "were",
        "what", "when", "where", "who", "why", "with", "any", "document", "documents",
        "archive", "content", "reference", "references", "mentioned", "mentions", "mention",
        "place", "organization", "organizations", "person", "people", "related", "about",
    }
    tokens: List[str] = []
    seen = set()
    for raw_token in re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", (text or "").lower()):
        if len(raw_token) < 3 or raw_token in stopwords or raw_token in seen:
            continue
        seen.add(raw_token)
        tokens.append(raw_token)
    return tokens


def _normalize_search_token(token: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", (token or "").lower())
    if len(normalized) > 4:
        if normalized.endswith("ies"):
            return normalized[:-3] + "y"
        if normalized.endswith("es") and len(normalized) > 5:
            return normalized[:-2]
        if normalized.endswith("s") and len(normalized) > 4:
            return normalized[:-1]
    return normalized


def _token_overlap_score(text: str, query_terms: List[str]) -> float:
    if not text or not query_terms:
        return 0.0

    text_tokens = set(_tokenize_search_text(text))
    normalized_text_tokens = {_normalize_search_token(token) for token in text_tokens}
    if not text_tokens:
        return 0.0

    matched = []
    for term in query_terms:
        normalized_term = _normalize_search_token(term)
        if term in text_tokens or normalized_term in text_tokens or normalized_term in normalized_text_tokens:
            matched.append(term)
    if not matched:
        return 0.0

    overlap = len(matched) / max(len(query_terms), 1)
    return min(0.45 + (overlap * 0.4), 0.9)


def _parse_embedding(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None
    if isinstance(value, list):
        try:
            return [float(item) for item in value]
        except Exception:
            return None
    return None


def _find_nested_text(value: Any, min_length: int = 50) -> str:
    """Recursively extract substantive text from nested structure.
    
    Prioritizes:
    1. Strings longer than min_length (default 50 chars) via preferred keys
    2. Strings longer than min_length via any key
    3. Falls back to shorter strings as last resort
    
    This avoids matching short version strings, timestamps, etc.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        preferred_keys = ["content", "text", "ocr_text", "summary", "body", "transcript"]
        
        # Phase 1: Look for substantive text (min_length chars) in preferred keys
        for key in preferred_keys:
            nested = value.get(key)
            text = _find_nested_text(nested, min_length=min_length)
            if text and len(text) >= min_length:
                return text
        
        # Phase 2: Look for substantive text in all keys
        for nested in value.values():
            text = _find_nested_text(nested, min_length=min_length)
            if text and len(text) >= min_length:
                return text
        
        # Phase 3: Fallback to any non-empty text (for very short documents)
        for key in preferred_keys:
            nested = value.get(key)
            text = _find_nested_text(nested, min_length=0)
            if text:
                return text
        
        for nested in value.values():
            text = _find_nested_text(nested, min_length=0)
            if text:
                return text
        
        return ""
    if isinstance(value, list):
        for item in value:
            text = _find_nested_text(item, min_length=min_length)
            if text:
                return text
        return ""
    return ""


def select_best_search_chunk(
    search_chunks: List[Dict[str, Any]],
    query: str,
    query_terms: Optional[List[str]] = None,
    query_embedding: Optional[List[float]] = None,
    cosine_similarity_fn: Optional[Callable[[List[float], List[float]], float]] = None,
) -> Optional[Dict[str, Any]]:
    """Select the best matching chunk using embeddings and/or token overlap."""
    if not search_chunks:
        return None

    best_chunk: Optional[Dict[str, Any]] = None
    best_score = 0.0
    best_method = "none"

    for chunk in search_chunks:
        if not isinstance(chunk, dict):
            continue

        text = chunk.get("text") or ""
        if not text:
            continue

        score = 0.0
        method = "keyword"
        chunk_embedding = _parse_embedding(chunk.get("embedding_vector"))
        if query_embedding and chunk_embedding and cosine_similarity_fn:
            raw_similarity = cosine_similarity_fn(query_embedding, chunk_embedding)
            score = (raw_similarity + 1.0) / 2.0
            method = "semantic"

        overlap_score = _token_overlap_score(text, query_terms or _tokenize_search_text(query))
        if overlap_score > score:
            score = overlap_score
            method = "keyword"

        current_kind = chunk.get("kind") or "content"
        best_kind = best_chunk.get("kind") if isinstance(best_chunk, dict) else None
        is_better_score = score > best_score + 1e-9
        is_tie_but_prefer_content = (
            abs(score - best_score) <= 1e-9
            and current_kind == "content"
            and best_kind != "content"
        )

        if is_better_score or is_tie_but_prefer_content:
            best_score = score
            best_chunk = chunk
            best_method = method

    if not best_chunk or best_score <= 0.0:
        return None

    matched_path = best_chunk.get("source") or "processed_data.content"
    if best_chunk.get("kind") == "metadata":
        matched_path = best_chunk.get("source") or "metadata.summary"

    return {
        "score": best_score,
        "method": best_method,
        "matched_path": matched_path,
        "matched_text": best_chunk.get("text") or "",
        "chunk_index": best_chunk.get("chunk_index"),
        "start_char": best_chunk.get("start_char"),
        "end_char": best_chunk.get("end_char"),
        "chunk": best_chunk,
    }


def build_document_search_index(
    metadata: Dict[str, Any],
    processed_data: Dict[str, Any],
    original_file: str,
    generate_embedding_fn: Optional[Callable[[str], Optional[List[float]]]] = None,
    chunk_size: int = 900,
    overlap: int = 150,
) -> Dict[str, Any]:
    """Build a searchable index payload with chunk passages and embeddings."""
    metadata = metadata or {}
    processed_data = processed_data or {}

    searchable_text = combine_searchable_text(metadata, processed_data, original_file)

    content_text = _first_non_empty(
        processed_data.get("content"),
        processed_data.get("text"),
        processed_data.get("ocr_text"),
        processed_data.get("result", {}).get("content") if isinstance(processed_data.get("result"), dict) else "",
        _find_nested_text(processed_data.get("result")),
    )

    summary_text = _first_non_empty(
        metadata.get("summary"),
        metadata.get("content", {}).get("summary") if isinstance(metadata.get("content"), dict) else "",
        processed_data.get("summary") if isinstance(processed_data.get("summary"), str) else "",
        processed_data.get("result", {}).get("summary", {}).get("text")
        if isinstance(processed_data.get("result"), dict) and isinstance(processed_data.get("result", {}).get("summary"), dict)
        else "",
    )

    search_chunks: List[Dict[str, Any]] = []
    if content_text:
        for chunk in split_text_into_chunks(content_text, chunk_size=chunk_size, overlap=overlap):
            chunk_payload = {
                **chunk,
                "source": "processed_data.content",
                "kind": "content",
            }
            if generate_embedding_fn:
                try:
                    chunk_payload["embedding_vector"] = generate_embedding_fn(chunk_payload["text"])
                except Exception as exc:
                    logger.warning("[SEARCH-UTILS] Failed to embed content chunk %s: %s", chunk_payload.get("chunk_index"), exc)
                    chunk_payload["embedding_vector"] = None
            search_chunks.append(chunk_payload)

    if summary_text:
        metadata_chunk = {
            "chunk_index": len(search_chunks),
            "text": summary_text,
            "start_char": None,
            "end_char": None,
            "source": "metadata.summary",
            "kind": "metadata",
        }
        if generate_embedding_fn:
            try:
                metadata_chunk["embedding_vector"] = generate_embedding_fn(summary_text)
            except Exception as exc:
                logger.warning("[SEARCH-UTILS] Failed to embed metadata summary: %s", exc)
                metadata_chunk["embedding_vector"] = None
        search_chunks.append(metadata_chunk)

    doc_embedding = None
    embedding_generated = False
    if generate_embedding_fn and searchable_text:
        try:
            doc_embedding = generate_embedding_fn(searchable_text)
            embedding_generated = doc_embedding is not None
        except Exception as exc:
            logger.warning("[SEARCH-UTILS] Failed to embed searchable text: %s", exc)
            doc_embedding = None

    payload = {
        "search_index_version": 1,
        "searchable_text": searchable_text,
        "search_chunks": search_chunks,
        "search_chunk_count": len(search_chunks),
        "search_content_length": len(content_text) if content_text else 0,
        "embedding_generated": embedding_generated,
        "embedding_model": "all-MiniLM-L6-v2" if embedding_generated else None,
        "embedding_timestamp": datetime.now(timezone.utc).isoformat() if embedding_generated else None,
        "embedding_vector": doc_embedding,
    }

    logger.info(
        "[SEARCH-UTILS] Built search index: original_file=%s content_len=%d chunks=%d embedding=%s",
        original_file,
        payload["search_content_length"],
        payload["search_chunk_count"],
        embedding_generated,
    )
    if search_chunks:
        preview = [
            {
                "chunk_index": chunk.get("chunk_index"),
                "source": chunk.get("source"),
                "text_preview": (chunk.get("text") or "")[:80],
            }
            for chunk in search_chunks[:3]
        ]
        logger.debug("[SEARCH-UTILS] Chunk preview=%s", preview)

    return payload


def format_search_document_result(
    doc: Dict[str, Any],
    rank: int,
    include_original: bool,
) -> Dict[str, Any]:
    """Normalize a search result for the timeline UI."""
    return {
        "rank": rank,
        "document_id": doc.get("document_id"),
        "filename": doc.get("original_file"),
        "type": doc.get("type"),
        "relevance_score": round(float(doc.get("relevance_score", 0) or 0), 3),
        "created_at": doc.get("created_at"),
        "summary": doc.get("summary"),
        "topics": doc.get("topics"),
        "places": doc.get("places"),
        "excerpt": doc.get("excerpt"),
        "matched_text": doc.get("matched_text"),
        "matched_path": doc.get("matched_path"),
        "match_method": doc.get("match_method"),
        "matched_chunk_index": doc.get("matched_chunk_index"),
        "matched_chunk_start": doc.get("matched_chunk_start"),
        "matched_chunk_end": doc.get("matched_chunk_end"),
        "original_file_data": doc.get("original_file_data") if include_original else None,
    }