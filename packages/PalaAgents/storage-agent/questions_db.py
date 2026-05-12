"""
Questions Database Module

Manages persistent storage of pre-generated questions.
Questions are stored with provenance, filters, embeddings, and metadata.

SCHEMA:
- question_id: UUID
- text: the question string
- provenance: source document_id
- filters: JSON (tags, type, language, location, etc.)
- suggestion_type: 'question', 'topic', 'filter', etc.
- embedding: JSON array of floats (vector)
- created_at: ISO 8601 timestamp
- updated_at: ISO 8601 timestamp
- model: 'ollama' or other model name
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class QuestionsDB:
    """
    Manages persistent storage of pre-generated questions.
    Separate from content_metadata; this is purely for search suggestions.
    """
    
    def __init__(self, db_path: str = "./questions_metadata.db"):
        """
        Initialize questions database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"[QUESTIONS-DB] Initialized: {db_path}")
    
    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                question_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                provenance TEXT NOT NULL,
                filters TEXT NOT NULL,
                suggestion_type TEXT NOT NULL,
                embedding TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model TEXT NOT NULL
            )
        ''')
        
        # Index on provenance (find all questions for a doc)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_questions_provenance
            ON questions(provenance)
        ''')
        
        # Index on suggestion_type for filtering
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_questions_type
            ON questions(suggestion_type)
        ''')
        
        # Status table to track which documents have had questions generated
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_status (
                document_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                generated_at TEXT,
                question_count INTEGER DEFAULT 0,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("[QUESTIONS-DB] Schema initialized")
    
    def store_question(
        self,
        question_id: str,
        text: str,
        provenance: str,
        filters: Dict[str, Any],
        suggestion_type: str,
        embedding: Optional[List[float]],
        created_at: str,
        updated_at: str,
        model: str,
    ) -> bool:
        """
        Store a single question.
        
        Args:
            question_id: UUID
            text: Question text
            provenance: Source document_id
            filters: JSON-serializable dict
            suggestion_type: 'question', 'topic', etc.
            embedding: Optional list of floats
            created_at: ISO 8601 timestamp
            updated_at: ISO 8601 timestamp
            model: Model name
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            filters_json = json.dumps(filters)
            embedding_json = json.dumps(embedding) if embedding else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO questions
                (question_id, text, provenance, filters, suggestion_type, embedding, created_at, updated_at, model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_id, text, provenance, filters_json, suggestion_type,
                embedding_json, created_at, updated_at, model
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to store question {question_id}: {e}")
            return False
    
    def store_questions_batch(self, questions: List[Dict[str, Any]]) -> int:
        """
        Store multiple questions in one transaction.
        
        Args:
            questions: List of question dicts OR GeneratedQuestion objects with all required fields
            
        Returns:
            Number successfully stored
        """
        if not questions:
            return 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            success_count = 0
            for q in questions:
                try:
                    # Handle both dict and GeneratedQuestion objects
                    if hasattr(q, '__dict__'):
                        # It's an object, convert to dict
                        q_dict = vars(q) if not isinstance(q, dict) else q
                    else:
                        q_dict = q
                    
                    filters_json = json.dumps(q_dict.get("filters", {}))
                    embedding_json = json.dumps(q_dict.get("embedding")) if q_dict.get("embedding") else None
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO questions
                        (question_id, text, provenance, filters, suggestion_type, embedding, created_at, updated_at, model)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        q_dict["question_id"],
                        q_dict["text"],
                        q_dict["provenance"],
                        filters_json,
                        q_dict.get("suggestion_type", "question"),
                        embedding_json,
                        q_dict["created_at"],
                        q_dict["updated_at"],
                        q_dict.get("model", "ollama")
                    ))
                    success_count += 1
                except Exception as e:
                    logger.warning(f"[QUESTIONS-DB] Failed to store question {q_dict.get('question_id')}: {e}")
            
            conn.commit()
            conn.close()
            logger.info(f"[QUESTIONS-DB] Stored {success_count}/{len(questions)} questions")
            return success_count
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Batch insert failed: {e}")
            return 0
    
    def get_questions_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all questions for a specific document.
        
        Args:
            document_id: Source document ID
            
        Returns:
            List of question dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT question_id, text, provenance, filters, suggestion_type, embedding, created_at, updated_at, model
                FROM questions
                WHERE provenance = ?
                ORDER BY created_at DESC
            ''', (document_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            questions = []
            for row in rows:
                q = {
                    "question_id": row[0],
                    "text": row[1],
                    "provenance": row[2],
                    "filters": json.loads(row[3]) if row[3] else {},
                    "suggestion_type": row[4],
                    "embedding": json.loads(row[5]) if row[5] else None,
                    "created_at": row[6],
                    "updated_at": row[7],
                    "model": row[8],
                }
                questions.append(q)
            
            return questions
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to retrieve questions for {document_id}: {e}")
            return []
    
    def delete_questions_for_document(self, document_id: str) -> int:
        """
        Delete all questions for a document (before regeneration).
        
        Args:
            document_id: Source document ID
            
        Returns:
            Number of rows deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM questions WHERE provenance = ?', (document_id,))
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"[QUESTIONS-DB] Deleted {deleted} questions for document {document_id}")
            return deleted
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to delete questions for {document_id}: {e}")
            return 0
    
    def mark_generation_status(
        self,
        document_id: str,
        status: str,
        question_count: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Mark generation status for a document.
        
        Args:
            document_id: Document ID
            status: 'pending', 'generated', 'failed', 'regenerating'
            question_count: Number of questions generated
            error_message: Error message if failed
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now(timezone.utc).isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO generation_status
                (document_id, status, generated_at, question_count, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (document_id, status, now if status == "generated" else None, question_count, error_message))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"[QUESTIONS-DB] Marked {document_id} as {status}")
            return True
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to update generation status for {document_id}: {e}")
            return False
    
    def get_generation_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get generation status for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Status dict or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT document_id, status, generated_at, question_count, error_message
                FROM generation_status
                WHERE document_id = ?
            ''', (document_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "document_id": row[0],
                    "status": row[1],
                    "generated_at": row[2],
                    "question_count": row[3],
                    "error_message": row[4],
                }
            return None
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to get generation status for {document_id}: {e}")
            return None
    
    def get_documents_pending_generation(self) -> List[str]:
        """
        Get list of document IDs that need question generation.
        
        Returns:
            List of document IDs
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find documents not yet in generation_status
            cursor.execute('''
                SELECT DISTINCT provenance FROM questions
                WHERE provenance NOT IN (SELECT document_id FROM generation_status)
                LIMIT 100
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to get pending documents: {e}")
            return []
    
    def search_questions_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Search questions by vector similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of questions ranked by similarity
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT question_id, text, provenance, filters, embedding FROM questions')
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return []
            
            # Simple cosine similarity
            import math
            
            def cosine_similarity(a: List[float], b: List[float]) -> float:
                if not a or not b or len(a) != len(b):
                    return 0.0
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot / (norm_a * norm_b)
            
            results = []
            for row in rows:
                embedding = json.loads(row[4]) if row[4] else None
                if embedding:
                    sim = cosine_similarity(query_embedding, embedding)
                    if sim >= similarity_threshold:
                        results.append({
                            "question_id": row[0],
                            "text": row[1],
                            "provenance": row[2],
                            "filters": json.loads(row[3]) if row[3] else {},
                            "similarity": sim,
                        })
            
            # Sort by similarity descending
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"[QUESTIONS-DB] Failed to search questions by embedding: {e}")
            return []
