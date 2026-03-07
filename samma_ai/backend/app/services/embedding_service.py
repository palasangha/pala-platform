"""
Embedding Service — multilingual-e5-large vector embeddings for Tipitaka RAG.

Handles:
- Lazy loading of the sentence-transformer model (GPU if available)
- Encoding passages and queries in E5 format (prefix "passage: " / "query: ")
- Qdrant collection management
- Bulk indexing of 22,213 mula passages from SQLite
"""

import sqlite3
import logging
import time
import traceback
from typing import List

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages multilingual-e5-large embeddings and Qdrant indexing."""

    VECTOR_DIM = 1024  # multilingual-e5-large output dimension

    def __init__(self):
        self._model = None  # lazy-loaded on first use

    # ─────────────────────────── model loading ───────────────────────────────

    def get_model(self):
        """Load model once, reuse across calls. Uses GPU if available."""
        if self._model is not None:
            return self._model

        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(
                "[EmbeddingService.get_model] torch detected — device=%s  "
                "cuda_available=%s",
                device, torch.cuda.is_available(),
            )
        except ImportError:
            device = 'cpu'
            logger.warning(
                "[EmbeddingService.get_model] torch not installed — "
                "falling back to CPU. Install torch for GPU acceleration."
            )

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            logger.critical(
                "[EmbeddingService.get_model] sentence-transformers is NOT installed. "
                "Run: pip install sentence-transformers torch  |  error=%s", exc,
            )
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers torch"
            ) from exc

        model_name = 'intfloat/multilingual-e5-large'
        logger.info(
            "[EmbeddingService.get_model] Loading model '%s' on device='%s' "
            "(first load downloads ~500 MB)", model_name, device,
        )
        try:
            self._model = SentenceTransformer(model_name, device=device)
            logger.info(
                "[EmbeddingService.get_model] Model loaded successfully. "
                "device=%s", device,
            )
        except Exception as exc:
            logger.critical(
                "[EmbeddingService.get_model] FAILED to load model '%s' — "
                "error=%s\n%s", model_name, exc, traceback.format_exc(),
            )
            raise

        return self._model

    # ─────────────────────────── encoding ────────────────────────────────────

    def encode_passages(self, texts: List[str]) -> 'np.ndarray':
        """
        Encode passage texts with 'passage: ' prefix (E5 format).
        Used during indexing.
        """
        if not texts:
            logger.warning("[EmbeddingService.encode_passages] Called with empty text list.")
            import numpy as np
            return np.array([])

        model = self.get_model()
        prefixed = [f"passage: {t}" for t in texts]
        logger.debug(
            "[EmbeddingService.encode_passages] Encoding %d passages (first 60 chars): %s...",
            len(texts), texts[0][:60],
        )
        try:
            vectors = model.encode(
                prefixed,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            logger.debug(
                "[EmbeddingService.encode_passages] Encoded %d passages → shape=%s",
                len(texts), vectors.shape,
            )
            return vectors
        except Exception as exc:
            logger.error(
                "[EmbeddingService.encode_passages] Encoding failed for batch of %d texts — "
                "error=%s\n%s", len(texts), exc, traceback.format_exc(),
            )
            raise

    def encode_query(self, query: str) -> List[float]:
        """
        Encode a single user query with 'query: ' prefix (E5 format).
        Returns a plain Python list for Qdrant compatibility.
        """
        if not query or not query.strip():
            logger.warning("[EmbeddingService.encode_query] Called with empty/blank query.")
            return [0.0] * self.VECTOR_DIM

        logger.debug(
            "[EmbeddingService.encode_query] Encoding query (len=%d): %.80r",
            len(query), query,
        )
        model = self.get_model()
        prefixed = f"query: {query}"
        try:
            vector = model.encode(
                [prefixed],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            result = vector[0].tolist()
            logger.debug(
                "[EmbeddingService.encode_query] Query encoded — "
                "vector dim=%d  first_value=%.6f", len(result), result[0],
            )
            return result
        except Exception as exc:
            logger.error(
                "[EmbeddingService.encode_query] Encoding failed for query=%.80r — "
                "error=%s\n%s", query, exc, traceback.format_exc(),
            )
            raise

    # ─────────────────────────── Qdrant collection management ────────────────

    def ensure_collection(self, qdrant, collection_name: str = 'tipitaka_mula') -> None:
        """Create Qdrant collection with cosine similarity if it doesn't exist."""
        logger.info(
            "[EmbeddingService.ensure_collection] Checking collection '%s'...",
            collection_name,
        )
        try:
            from qdrant_client.models import Distance, VectorParams
            existing = [c.name for c in qdrant.get_collections().collections]
            logger.debug(
                "[EmbeddingService.ensure_collection] Existing collections: %s", existing,
            )

            if collection_name not in existing:
                logger.info(
                    "[EmbeddingService.ensure_collection] Collection '%s' not found — creating "
                    "with dim=%d cosine distance.", collection_name, self.VECTOR_DIM,
                )
                qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_DIM,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(
                    "[EmbeddingService.ensure_collection] Collection '%s' created successfully.",
                    collection_name,
                )
            else:
                logger.info(
                    "[EmbeddingService.ensure_collection] Collection '%s' already exists.",
                    collection_name,
                )
        except Exception as exc:
            logger.error(
                "[EmbeddingService.ensure_collection] FAILED to ensure collection '%s' — "
                "error=%s\n%s", collection_name, exc, traceback.format_exc(),
            )
            raise

    def is_collection_populated(self, qdrant, collection_name: str = 'tipitaka_mula') -> bool:
        """Return True if the collection already contains vectors.

        qdrant-client >= 1.7 renamed vectors_count → points_count on CollectionInfo;
        we probe both attributes so the code works across versions.
        """
        try:
            info = qdrant.get_collection(collection_name)

            # qdrant-client >= 1.7: use points_count
            # qdrant-client < 1.7:  use vectors_count
            count = getattr(info, 'points_count', None)
            if count is None:
                count = getattr(info, 'vectors_count', None)
            if count is None:
                # Last resort: query the collection directly
                result = qdrant.count(collection_name=collection_name)
                count = result.count

            populated = count is not None and count > 0
            logger.info(
                "[EmbeddingService.is_collection_populated] collection='%s'  "
                "count=%s  populated=%s",
                collection_name, count, populated,
            )
            return populated
        except Exception as exc:
            logger.warning(
                "[EmbeddingService.is_collection_populated] Could not read collection '%s' — "
                "assuming empty.  error=%s", collection_name, exc,
            )
            return False

    # ─────────────────────────── bulk indexing ────────────────────────────────

    def index_all_passages(
        self,
        db_path: str,
        qdrant,
        batch_size: int = 64,
        collection_name: str = 'tipitaka_mula',
    ) -> int:
        """
        Read all mula passages from SQLite, embed them in batches, and upsert
        to Qdrant.  Returns the total number of passages indexed.

        Payload stored per vector:
          passage_id, book_id, paragraph_number, pali_text (first 200 chars),
          pitaka_id, nikaya_id
        """
        logger.info(
            "[EmbeddingService.index_all_passages] START  db_path=%s  "
            "collection=%s  batch_size=%d", db_path, collection_name, batch_size,
        )

        # ── Step 1: ensure collection ────────────────────────────────────────
        self.ensure_collection(qdrant, collection_name)

        # ── Step 2: read all mula passages from SQLite ───────────────────────
        logger.info(
            "[EmbeddingService.index_all_passages] Reading mula passages from SQLite..."
        )
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    par.id          AS passage_id,
                    par.book_id,
                    par.paragraph_number,
                    par.pali_text,
                    b.pitaka_id,
                    b.nikaya_id
                FROM paragraphs par
                LEFT JOIN books b ON par.book_id = b.id
                WHERE par.text_layer = 'mula'
                ORDER BY par.id
            """)
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            logger.critical(
                "[EmbeddingService.index_all_passages] FAILED reading from SQLite — "
                "db_path=%s  error=%s\n%s", db_path, exc, traceback.format_exc(),
            )
            raise

        total = len(rows)
        logger.info(
            "[EmbeddingService.index_all_passages] Read %d mula passages from SQLite.",
            total,
        )
        if total == 0:
            logger.error(
                "[EmbeddingService.index_all_passages] Zero passages returned — "
                "check that text_layer='mula' rows exist in %s", db_path,
            )
            return 0

        # ── Step 3: batch-encode and upsert ──────────────────────────────────
        from qdrant_client.models import PointStruct

        start = time.time()
        indexed = 0
        failed_batches = 0

        for batch_start in range(0, total, batch_size):
            batch = rows[batch_start: batch_start + batch_size]
            texts = [r['pali_text'] for r in batch]
            batch_num = batch_start // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.debug(
                "[EmbeddingService.index_all_passages] Batch %d/%d  "
                "passages %d–%d",
                batch_num, total_batches,
                batch_start + 1, batch_start + len(batch),
            )

            # Encode
            try:
                vectors = self.encode_passages(texts)
            except Exception as exc:
                logger.error(
                    "[EmbeddingService.index_all_passages] Encoding FAILED for batch %d/%d "
                    "(passages %d–%d) — error=%s\n%s  — SKIPPING batch.",
                    batch_num, total_batches,
                    batch_start + 1, batch_start + len(batch),
                    exc, traceback.format_exc(),
                )
                failed_batches += 1
                continue

            # Build Qdrant point structs
            points = []
            for i, row in enumerate(batch):
                point_id = batch_start + i + 1  # stable 1-indexed integer
                points.append(PointStruct(
                    id=point_id,
                    vector=vectors[i].tolist(),
                    payload={
                        'passage_id':       row['passage_id'],
                        'book_id':          row['book_id'],
                        'paragraph_number': row['paragraph_number'],
                        'pali_text':        row['pali_text'][:200],
                        'pitaka_id':        row['pitaka_id'],
                        'nikaya_id':        row['nikaya_id'],
                    },
                ))

            # Upsert to Qdrant
            try:
                qdrant.upsert(collection_name=collection_name, points=points)
                indexed += len(batch)
            except Exception as exc:
                logger.error(
                    "[EmbeddingService.index_all_passages] Qdrant upsert FAILED for batch "
                    "%d/%d (passages %d–%d) — error=%s\n%s  — SKIPPING batch.",
                    batch_num, total_batches,
                    batch_start + 1, batch_start + len(batch),
                    exc, traceback.format_exc(),
                )
                failed_batches += 1
                continue

            # Progress log every 10 batches
            if batch_num % 10 == 0 or batch_num == total_batches:
                elapsed = time.time() - start
                pct = indexed / total * 100
                rate = indexed / elapsed if elapsed > 0 else 0
                eta_secs = (total - indexed) / rate if rate > 0 else 0
                logger.info(
                    "[EmbeddingService.index_all_passages] Progress: "
                    "%d/%d (%.1f%%)  elapsed=%.1fs  rate=%.0f/s  eta=%.0fs",
                    indexed, total, pct, elapsed, rate, eta_secs,
                )

        # ── Step 4: summary ──────────────────────────────────────────────────
        elapsed = time.time() - start
        if failed_batches:
            logger.warning(
                "[EmbeddingService.index_all_passages] FINISHED with %d failed batches. "
                "indexed=%d  total=%d  elapsed=%.1fs",
                failed_batches, indexed, total, elapsed,
            )
        else:
            logger.info(
                "[EmbeddingService.index_all_passages] COMPLETE — "
                "indexed=%d passages in %.1fs  collection=%s",
                indexed, elapsed, collection_name,
            )
        return indexed
