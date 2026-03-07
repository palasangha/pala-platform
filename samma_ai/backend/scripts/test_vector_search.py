#!/usr/bin/env python3
"""
test_vector_search.py — Smoke-test the Qdrant vector search without starting Flask.

Usage:
    cd backend
    python scripts/test_vector_search.py

Checks:
  1. "What is dukkha?"          → expect passage containing 'dukkha' from SN/DN
  2. "What causes suffering?"   → expect passage about tanha / dependent origination
  3. "mindfulness of breathing" → expect ānāpānasati related passage
"""

import sys
import os
import logging

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

logging.basicConfig(level=logging.WARNING)

QUERIES = [
    {
        'query': 'What is dukkha?',
        'expect_pali': ['dukkh'],  # any form of dukkha
        'expect_nikaya': None,     # ideally SN or DN
        'description': 'Definition of dukkha (suffering)',
    },
    {
        'query': 'What causes suffering?',
        'expect_pali': ['tanh', 'samudaya', 'pa\u1e6diccasamuppāda', 'pa\u1e6diccasamuppada'],
        'expect_nikaya': None,
        'description': 'Cause of suffering (tanha / dependent origination)',
    },
    {
        'query': 'mindfulness of breathing',
        'expect_pali': ['ānāpāna', 'anapana', '\u0101n\u0101p\u0101na'],
        'expect_nikaya': None,
        'description': 'Ānāpānasati (mindfulness of breathing)',
    },
]


def _contains_any(text: str, fragments: list) -> bool:
    text_lower = text.lower()
    return any(f.lower() in text_lower for f in fragments)


def main():
    # Connect to Qdrant
    qdrant_host = os.environ.get('QDRANT_HOST', 'localhost')
    qdrant_port = int(os.environ.get('QDRANT_PORT', '6333'))
    collection  = os.environ.get('QDRANT_COLLECTION', 'tipitaka_mula')
    db_path     = os.environ.get(
        'TIPITAKA_DB_PATH',
        os.path.join(BACKEND_DIR, '..', 'database', 'tipitaka_ultimate.db'),
    )
    db_path = os.path.normpath(db_path)

    print(f"\n{'='*60}")
    print(" Samma AI — Vector Search Smoke Test")
    print(f"{'='*60}")
    print(f"  Qdrant : {qdrant_host}:{qdrant_port}  collection={collection}")
    print(f"  DB     : {db_path}")
    print()

    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        info = qdrant.get_collection(collection)
        count = getattr(info, 'points_count', None) or getattr(info, 'vectors_count', None)
        print(f"  ✓ Qdrant connected — {count:,} vectors\n")
    except Exception as e:
        print(f"  ✗ Cannot connect to Qdrant: {e}")
        print("  Start with: docker run -d --name qdrant -p 6333:6333 "
              "-v ~/.qdrant:/qdrant/storage qdrant/qdrant")
        sys.exit(1)

    from app.services.embedding_service import EmbeddingService
    svc = EmbeddingService()

    passed = 0
    failed = 0

    for i, test in enumerate(QUERIES, 1):
        query = test['query']
        print(f"Query {i}: \"{query}\"")
        print(f"  Checking: {test['description']}")

        q_vec = svc.encode_query(query)
        result = qdrant.query_points(
            collection_name=collection,
            query=q_vec,
            limit=5,
            with_payload=True,
        )
        hits = result.points

        if not hits:
            print(f"  ✗ No results returned!\n")
            failed += 1
            continue

        top = hits[0]
        pali_snippet = top.payload.get('pali_text', '')[:120]
        passage_id   = top.payload.get('passage_id', '?')
        score        = top.score

        print(f"  Top result: {passage_id}  (score={score:.4f})")
        print(f"  Pali: {pali_snippet}...")

        # Check expectation
        if test['expect_pali']:
            if _contains_any(pali_snippet, test['expect_pali']):
                print(f"  ✓ PASS — found expected Pali fragment\n")
                passed += 1
            else:
                print(f"  ✗ FAIL — expected one of {test['expect_pali']} in top result\n")
                # Show all 5 hits for debugging
                for j, h in enumerate(hits, 1):
                    print(f"    Hit {j}: {h.payload.get('passage_id')} "
                          f"score={h.score:.4f}  "
                          f"{h.payload.get('pali_text', '')[:80]}...")
                print()
                failed += 1
        else:
            print(f"  ✓ PASS (no strict expectation)\n")
            passed += 1

    print(f"{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed out of {len(QUERIES)} tests")
    print(f"{'='*60}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
