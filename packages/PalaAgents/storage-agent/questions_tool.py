"""
Storage Agent Tool: Question Management

MCP tool interface for generating, retrieving, and managing pre-generated questions.
Integrates with the storage pipeline at document ingestion time.

TOOLS:
- generate_questions: Generate questions for a single document
- retrieve_questions: Get questions for a document
- regenerate_questions: Regenerate questions for a document
- search_questions: Search pre-generated questions by vector similarity
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class QuestionsTool:
    """MCP tool wrapper for question management"""
    
    def __init__(
        self,
        question_generator,
        questions_db,
        embedding_model,
    ):
        """
        Initialize questions tool.
        
        Args:
            question_generator: QuestionGenerator instance
            questions_db: QuestionsDB instance
            embedding_model: SentenceTransformer for embeddings
        """
        self.question_generator = question_generator
        self.questions_db = questions_db
        self.embedding_model = embedding_model
        logger.info("[QUESTIONS-TOOL] Initialized QuestionsTool")
    
    async def generate_questions(
        self,
        document_id: str,
        document_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
    ) -> Dict[str, Any]:
        """
        Generate questions for a document at ingestion time.
        
        Args:
            document_id: Document ID
            document_type: Document type
            metadata: Document metadata
            processed_data: Processed/extracted content
            original_file: Original filename
            
        Returns:
            Result dict with question_count and questions
        """
        logger.info(f"[QUESTIONS-TOOL] Generating questions for {document_id}")
        
        try:
            # Check if already generated
            status = self.questions_db.get_generation_status(document_id)
            if status and status["status"] == "generated":
                logger.info(f"[QUESTIONS-TOOL] Questions already generated for {document_id}")
                existing = self.questions_db.get_questions_for_document(document_id)
                return {
                    "success": True,
                    "document_id": document_id,
                    "question_count": len(existing),
                    "questions": existing,
                    "status": "already_generated",
                }
            
            # Mark as generating
            self.questions_db.mark_generation_status(document_id, "generating")
            
            # Generate questions
            generated_questions = await self.question_generator.generate_questions_for_document(
                document_id,
                document_type,
                metadata,
                processed_data,
                original_file,
                self.embedding_model,
            )
            
            if not generated_questions:
                self.questions_db.mark_generation_status(
                    document_id,
                    "failed",
                    error_message="No questions generated"
                )
                logger.warning(f"[QUESTIONS-TOOL] No questions generated for {document_id}")
                return {
                    "success": False,
                    "document_id": document_id,
                    "question_count": 0,
                    "error": "No questions generated",
                }
            
            # Store questions
            questions_list = [
                {
                    "question_id": q.question_id,
                    "text": q.text,
                    "provenance": q.provenance,
                    "filters": q.filters,
                    "suggestion_type": q.suggestion_type,
                    "embedding": q.embedding,
                    "created_at": q.created_at,
                    "updated_at": q.updated_at,
                    "model": q.model,
                }
                for q in generated_questions
            ]
            
            stored = self.questions_db.store_questions_batch(questions_list)
            
            # Update status
            self.questions_db.mark_generation_status(
                document_id,
                "generated",
                question_count=stored,
            )
            
            logger.info(f"[QUESTIONS-TOOL] Successfully generated and stored {stored} questions for {document_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "question_count": stored,
                "questions": questions_list,
                "status": "generated",
            }
            
        except Exception as e:
            logger.error(f"[QUESTIONS-TOOL] Failed to generate questions for {document_id}: {e}", exc_info=True)
            self.questions_db.mark_generation_status(
                document_id,
                "failed",
                error_message=str(e),
            )
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
            }
    
    async def retrieve_questions(self, document_id: str) -> Dict[str, Any]:
        """
        Retrieve pre-generated questions for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Result dict with questions list
        """
        try:
            questions = self.questions_db.get_questions_for_document(document_id)
            status = self.questions_db.get_generation_status(document_id)
            
            return {
                "success": True,
                "document_id": document_id,
                "question_count": len(questions),
                "questions": questions,
                "generation_status": status,
            }
        except Exception as e:
            logger.error(f"[QUESTIONS-TOOL] Failed to retrieve questions for {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
            }
    
    async def regenerate_questions(
        self,
        document_id: str,
        document_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
    ) -> Dict[str, Any]:
        """
        Regenerate questions for a document (e.g., after metadata update).
        
        Args:
            document_id: Document ID
            document_type: Document type
            metadata: Updated metadata
            processed_data: Updated processed data
            original_file: Original filename
            
        Returns:
            Result dict
        """
        logger.info(f"[QUESTIONS-TOOL] Regenerating questions for {document_id}")
        
        try:
            # Delete old questions
            self.questions_db.delete_questions_for_document(document_id)
            
            # Mark as regenerating
            self.questions_db.mark_generation_status(document_id, "regenerating")
            
            # Generate new questions
            generated_questions = await self.question_generator.generate_questions_for_document(
                document_id,
                document_type,
                metadata,
                processed_data,
                original_file,
                self.embedding_model,
            )
            
            if not generated_questions:
                self.questions_db.mark_generation_status(
                    document_id,
                    "failed",
                    error_message="No questions regenerated"
                )
                return {
                    "success": False,
                    "document_id": document_id,
                    "error": "No questions regenerated",
                }
            
            # Store new questions
            questions_list = [
                {
                    "question_id": q.question_id,
                    "text": q.text,
                    "provenance": q.provenance,
                    "filters": q.filters,
                    "suggestion_type": q.suggestion_type,
                    "embedding": q.embedding,
                    "created_at": q.created_at,
                    "updated_at": q.updated_at,
                    "model": q.model,
                }
                for q in generated_questions
            ]
            
            stored = self.questions_db.store_questions_batch(questions_list)
            
            # Update status
            self.questions_db.mark_generation_status(
                document_id,
                "generated",
                question_count=stored,
            )
            
            logger.info(f"[QUESTIONS-TOOL] Regenerated {stored} questions for {document_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "question_count": stored,
                "questions": questions_list,
                "status": "regenerated",
            }
            
        except Exception as e:
            logger.error(f"[QUESTIONS-TOOL] Failed to regenerate questions for {document_id}: {e}", exc_info=True)
            self.questions_db.mark_generation_status(
                document_id,
                "failed",
                error_message=str(e),
            )
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
            }
    
    async def search_questions(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Search pre-generated questions by vector similarity.
        
        Args:
            query: User search query
            top_k: Number of results
            similarity_threshold: Minimum similarity
            
        Returns:
            Result dict with matching questions
        """
        logger.info(f"[QUESTIONS-TOOL] Searching questions for: {query}")
        
        try:
            # Embed query
            if not self.embedding_model:
                return {
                    "success": False,
                    "error": "Embedding model not available",
                }
            
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search
            results = self.questions_db.search_questions_by_embedding(
                query_embedding,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
            
            logger.info(f"[QUESTIONS-TOOL] Found {len(results)} matching questions")
            
            return {
                "success": True,
                "query": query,
                "result_count": len(results),
                "results": results,
            }
            
        except Exception as e:
            logger.error(f"[QUESTIONS-TOOL] Search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
