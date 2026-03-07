"""
Samma AI Backend - Flask Application Factory
"""

import logging
import traceback
from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo

logger = logging.getLogger(__name__)

mongo = PyMongo()


def create_app(config_name='development'):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    from config.settings import config
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    mongo.init_app(app)

    # ── Vector database (Qdrant) + Embedding service ─────────────────────────
    _init_vector_search(app)

    # ── Translation service (Ollama + Deepseek) ──────────────────────────────
    _init_translation_service(app)

    # Register blueprints
    from app.routes.chat import chat_bp
    from app.routes.lookup import lookup_bp
    from app.routes.health import health_bp
    from app.routes.models_routes import models_bp
    from app.routes.agents_routes import agents_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(lookup_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(models_bp, url_prefix='/api')
    app.register_blueprint(agents_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')

    return app


def _init_vector_search(app: Flask) -> None:
    """
    Initialise Qdrant client and EmbeddingService.
    If the Qdrant collection is empty, index all mula passages now.
    Non-fatal: if Qdrant is not running the app starts with keyword fallback.
    """
    import traceback

    qdrant_host = app.config.get('QDRANT_HOST', 'localhost')
    qdrant_port = app.config.get('QDRANT_PORT', 6333)
    collection  = app.config.get('QDRANT_COLLECTION', 'tipitaka_mula')
    db_path     = app.config.get('TIPITAKA_DB_PATH', '')
    batch_size  = app.config.get('EMBEDDING_BATCH_SIZE', 64)

    app.logger.info(
        "[_init_vector_search] Starting vector search init — "
        "qdrant=%s:%s  collection=%s  db_path=%s  batch_size=%s",
        qdrant_host, qdrant_port, collection, db_path, batch_size,
    )

    # ── Step 1: import dependencies ──────────────────────────────────────────
    try:
        from qdrant_client import QdrantClient
    except ImportError as exc:
        app.logger.error(
            "[_init_vector_search] STEP 1 FAILED — qdrant-client is NOT installed. "
            "Run: pip install qdrant-client>=1.7.0  |  error=%s", exc,
        )
        _set_fallback(app)
        return

    try:
        from app.services.embedding_service import EmbeddingService
    except ImportError as exc:
        app.logger.error(
            "[_init_vector_search] STEP 1 FAILED — Cannot import EmbeddingService. "
            "error=%s\n%s", exc, traceback.format_exc(),
        )
        _set_fallback(app)
        return

    # ── Step 2: connect to Qdrant ────────────────────────────────────────────
    try:
        qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        qdrant.get_collections()  # connectivity probe
        app.logger.info(
            "[_init_vector_search] STEP 2 OK — Qdrant connected at %s:%s",
            qdrant_host, qdrant_port,
        )
    except Exception as exc:
        app.logger.warning(
            "[_init_vector_search] STEP 2 FAILED — Cannot reach Qdrant at %s:%s. "
            "Semantic search disabled; falling back to keyword search.\n"
            "Fix: docker run -d --name qdrant -p 6333:6333 "
            "-v ~/.qdrant:/qdrant/storage qdrant/qdrant\n"
            "Full error: %s\n%s",
            qdrant_host, qdrant_port, exc, traceback.format_exc(),
        )
        _set_fallback(app)
        return

    # ── Step 3: create EmbeddingService and ensure collection ────────────────
    try:
        embedding_service = EmbeddingService()
        embedding_service.ensure_collection(qdrant, collection)
        app.logger.info(
            "[_init_vector_search] STEP 3 OK — EmbeddingService ready, "
            "collection '%s' ensured.", collection,
        )
    except Exception as exc:
        app.logger.error(
            "[_init_vector_search] STEP 3 FAILED — EmbeddingService init or "
            "collection creation failed.  collection=%s  error=%s\n%s",
            collection, exc, traceback.format_exc(),
        )
        _set_fallback(app)
        return

    app.extensions['qdrant'] = qdrant
    app.extensions['embedding_service'] = embedding_service

    # ── Step 4: check if collection is already populated ─────────────────────
    try:
        populated = embedding_service.is_collection_populated(qdrant, collection)
    except Exception as exc:
        app.logger.error(
            "[_init_vector_search] STEP 4 FAILED — is_collection_populated raised. "
            "collection=%s  error=%s\n%s", collection, exc, traceback.format_exc(),
        )
        populated = False

    if not populated:
        app.logger.info(
            "[_init_vector_search] STEP 4 — Collection '%s' is empty. "
            "Building embeddings now (takes ~2-3 min on GPU). "
            "Alternatively run: python scripts/build_embeddings.py", collection,
        )
        # ── Step 5: index passages ────────────────────────────────────────────
        try:
            indexed = embedding_service.index_all_passages(
                db_path=db_path,
                qdrant=qdrant,
                batch_size=batch_size,
                collection_name=collection,
            )
            app.logger.info(
                "[_init_vector_search] STEP 5 OK — Indexed %d passages into '%s'.",
                indexed, collection,
            )
        except Exception as exc:
            app.logger.error(
                "[_init_vector_search] STEP 5 FAILED — index_all_passages raised. "
                "db_path=%s  collection=%s  error=%s\n%s",
                db_path, collection, exc, traceback.format_exc(),
            )
            # Qdrant and embedding_service remain available for partial use
    else:
        try:
            info  = qdrant.get_collection(collection)
            count = getattr(info, 'points_count', None) or getattr(info, 'vectors_count', None)
            app.logger.info(
                "[_init_vector_search] STEP 4 OK — Qdrant collection '%s' already "
                "populated with %s vectors. Semantic search enabled.",
                collection, f"{count:,}" if count else "?",
            )
        except Exception as exc:
            app.logger.warning(
                "[_init_vector_search] Could not read collection info for '%s' — "
                "error=%s", collection, exc,
            )


def _set_fallback(app: Flask) -> None:
    """Set Qdrant and EmbeddingService to None so TipitakaService falls back to keyword search."""
    app.extensions.setdefault('qdrant', None)
    app.extensions.setdefault('embedding_service', None)
    app.logger.info(
        "[_init_vector_search] Fallback mode active — "
        "all searches will use keyword LIKE queries."
    )


def _init_translation_service(app: Flask) -> None:
    """Initialize translation service (Ollama + Deepseek with SQLite cache)."""
    if not app.config.get('OLLAMA_TRANSLATION_ENABLED', True):
        app.extensions['translation_service'] = None
        app.logger.info("[_init_translation_service] Translation service disabled via config")
        return

    try:
        # Create migration table if it doesn't exist
        _create_translation_cache_table(app)

        # Initialize service within app context
        from app.services.translation_service import TranslationService
        with app.app_context():
            translation_service = TranslationService()
            app.extensions['translation_service'] = translation_service

        app.logger.info(
            "[_init_translation_service] Translation service initialized. "
            "Model=%s  Endpoint=%s  Timeout=%s  Cache TTL=%s",
            app.config.get('OLLAMA_TRANSLATION_MODEL'),
            app.config.get('OLLAMA_TRANSLATION_ENDPOINT'),
            app.config.get('OLLAMA_TRANSLATION_TIMEOUT'),
            app.config.get('TRANSLATION_CACHE_TTL'),
        )
    except Exception as e:
        app.logger.warning(
            "[_init_translation_service] Failed to initialize translation service — %s\n%s",
            e, traceback.format_exc()
        )
        app.extensions['translation_service'] = None


def _create_translation_cache_table(app: Flask) -> None:
    """Create pali_translations table if it doesn't exist."""
    try:
        import sqlite3
        db_path = app.config.get('TIPITAKA_DB_PATH', '')

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pali_translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pali_text TEXT NOT NULL UNIQUE,
                english_translation TEXT NOT NULL,
                reference TEXT,
                model_used TEXT DEFAULT 'deepseek-r1:32b',
                source TEXT DEFAULT 'ollama',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pali_text ON pali_translations(pali_text)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON pali_translations(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON pali_translations(expires_at)")

        conn.commit()
        conn.close()

        app.logger.info("[_create_translation_cache_table] pali_translations table ready")
    except Exception as e:
        app.logger.warning(
            "[_create_translation_cache_table] Failed to create table — %s", e
        )
