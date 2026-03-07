#!/usr/bin/env python3
"""
build_embeddings.py — One-time script to embed all 22,213 mula passages
into the Qdrant vector database.

Usage:
    cd backend
    python scripts/build_embeddings.py

Requires:
    - Qdrant running: docker run -d --name qdrant -p 6333:6333 \
        -v ~/.qdrant:/qdrant/storage qdrant/qdrant
    - sentence-transformers and torch installed
    - .env with TIPITAKA_DB_PATH (or run from backend/ where default path resolves)

The script is idempotent: if the collection already has vectors it skips
re-indexing unless --force is passed.
"""

import sys
import os
import time
import argparse
import logging

# ── path setup so we can import from backend/ without installing ─────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Build Tipitaka vector embeddings')
    parser.add_argument('--force', action='store_true',
                        help='Re-index even if collection already populated')
    parser.add_argument('--batch-size', type=int, default=64,
                        help='Embedding batch size (default 64)')
    parser.add_argument('--db-path', type=str,
                        default=os.environ.get(
                            'TIPITAKA_DB_PATH',
                            os.path.join(BACKEND_DIR, '..', 'database', 'tipitaka_ultimate.db')
                        ),
                        help='Path to tipitaka_ultimate.db')
    parser.add_argument('--qdrant-host', type=str,
                        default=os.environ.get('QDRANT_HOST', 'localhost'))
    parser.add_argument('--qdrant-port', type=int,
                        default=int(os.environ.get('QDRANT_PORT', '6333')))
    parser.add_argument('--collection', type=str,
                        default=os.environ.get('QDRANT_COLLECTION', 'tipitaka_mula'))
    args = parser.parse_args()

    db_path = os.path.normpath(args.db_path)
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # ── connect to Qdrant ────────────────────────────────────────────────────
    logger.info(f"Connecting to Qdrant at {args.qdrant_host}:{args.qdrant_port}...")
    try:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(host=args.qdrant_host, port=args.qdrant_port)
        # Quick connectivity check
        qdrant.get_collections()
    except Exception as e:
        logger.error(
            f"Cannot connect to Qdrant: {e}\n"
            "Start Qdrant with:\n"
            "  docker run -d --name qdrant -p 6333:6333 "
            "-v ~/.qdrant:/qdrant/storage qdrant/qdrant"
        )
        sys.exit(1)

    # ── load embedding service ───────────────────────────────────────────────
    from app.services.embedding_service import EmbeddingService
    svc = EmbeddingService()

    # ── check if already indexed ─────────────────────────────────────────────
    svc.ensure_collection(qdrant)
    if svc.is_collection_populated(qdrant) and not args.force:
        info = qdrant.get_collection(args.collection)
        logger.info(
            f"Collection '{args.collection}' already has {info.vectors_count} vectors. "
            "Use --force to re-index."
        )
        sys.exit(0)

    # ── run indexing ─────────────────────────────────────────────────────────
    logger.info(f"Database: {db_path}")
    logger.info(f"Batch size: {args.batch_size}")

    t0 = time.time()
    total = svc.index_all_passages(
        db_path=db_path,
        qdrant=qdrant,
        batch_size=args.batch_size,
        collection_name=args.collection,
    )
    elapsed = time.time() - t0

    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    print(f"\n✅ Indexed {total:,} passages in {mins}m {secs}s")
    print(f"   Collection: {args.collection}  |  Host: {args.qdrant_host}:{args.qdrant_port}")


if __name__ == '__main__':
    main()
