"""
Question Generator Module

Generates natural-language questions for documents at ingestion time.
Questions are grounded in document metadata and content, then embedded
and stored for vector similarity search at query time.

FEATURES:
- Generate 8-10 contextual questions per document
- Strictly grounded in provided metadata/content (no hallucination)
- Mixed question styles: factual, reflective, practical, location-based
- Store questions with provenance, filters, and embeddings
- Regenerate questions when metadata/tags change significantly
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestion:
    """Represents a pre-generated question for a document"""
    question_id: str
    text: str
    provenance: str  # source document_id
    filters: Dict[str, Any]  # derived from document: tags, type, language, location, etc.
    suggestion_type: str  # 'question' | 'topic' | 'filter' | 'expand' | 'action'
    embedding: Optional[List[float]] = None  # vector embedding
    created_at: str = ""
    updated_at: str = ""
    model: str = "ollama"  # which model generated this


class QuestionGenerator:
    """
    Generates contextual questions for documents using Ollama (or similar LLM).
    
    Usage:
        gen = QuestionGenerator(ollama_provider)
        questions = await gen.generate_questions_for_document(doc, embedding_model)
    """
    
    def __init__(self, ollama_provider):
        """
        Initialize question generator.
        
        Args:
            ollama_provider: OllamaProvider instance for LLM calls
        """
        self.ollama_provider = ollama_provider
        logger.info("[QUESTION-GEN] Initialized QuestionGenerator with Ollama provider")
    
    def _extract_document_context(
        self,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extract contextual information from document for question generation.
        
        Returns:
            (context_string, filters_dict)
        """
        parts = []
        filters = {
            "document_id": doc_id,
            "document_type": doc_type,
        }
        
        # Handle nested structure: processed_data might be {'result': {...}} 
        if processed_data and isinstance(processed_data, dict):
            if 'result' in processed_data:
                proc_result = processed_data['result']
            else:
                proc_result = processed_data
        else:
            proc_result = {}
        
        # Extract Pala metadata (try both locations)
        pala = metadata.get("pala_metadata", {}) if isinstance(metadata, dict) else {}
        if not pala and proc_result:
            pala = proc_result.get("pala_metadata", {}) if isinstance(proc_result, dict) else {}
        
        # Title and summary
        title = pala.get("content", {}).get("title", "")
        summary = pala.get("content", {}).get("summary", "")
        if title:
            parts.append(f"Title: {title}")
        if summary:
            parts.append(f"Summary: {summary}")
        
        # Language
        language = pala.get("content", {}).get("language", "")
        if language:
            parts.append(f"Language: {language}")
            filters["language"] = language
        
        # Dates
        date_info = pala.get("content", {}).get("date_info", {})
        if isinstance(date_info, dict):
            date_str = date_info.get("date_string", "")
            if date_str:
                parts.append(f"Date: {date_str}")
                filters["date"] = date_str
        
        # Locations
        locations = pala.get("places", {}).get("locations", [])
        if locations and isinstance(locations, list):
            loc_names = [loc.get("name") for loc in locations if isinstance(loc, dict) and loc.get("name")]
            if loc_names:
                parts.append(f"Locations: {', '.join(loc_names)}")
                filters["locations"] = loc_names
        
        # Topics
        topics_data = pala.get("content", {}).get("topics", {})
        if isinstance(topics_data, dict):
            topics = topics_data.get("topics", [])
        else:
            topics = topics_data if isinstance(topics_data, list) else []
        if topics:
            parts.append(f"Topics: {', '.join(str(t) for t in topics)}")
            filters["topics"] = topics
        
        # People/entities
        people = pala.get("parties", {}).get("people", [])
        if people and isinstance(people, list):
            names = [p.get("name") for p in people if isinstance(p, dict) and p.get("name")]
            if names:
                parts.append(f"People: {', '.join(names)}")
                filters["people"] = names
        
        # App tags
        app_data = metadata.get("app_data", {}) if isinstance(metadata, dict) else {}
        if isinstance(app_data, dict):
            tags = app_data.get("tags", [])
            if tags and isinstance(tags, list):
                parts.append(f"Tags: {', '.join(str(t) for t in tags)}")
                filters["tags"] = tags
        
        # Extracted content snippet - try multiple locations
        content = ""
        if proc_result and isinstance(proc_result, dict):
            content = proc_result.get("content", "") or proc_result.get("text", "") or proc_result.get("ocr_text", "")
        if not content and processed_data and isinstance(processed_data, dict):
            content = processed_data.get("content", "") or processed_data.get("text", "") or processed_data.get("ocr_text", "")
        
        if isinstance(content, str) and content.strip():
            snippet = content.strip()[:800]  # Get more content for better context
            parts.append(f"Content snippet: {snippet}")
        
        context_str = "\n".join(parts)
        logger.debug(f"[QUESTION-GEN] Extracted context for doc {doc_id}: {len(context_str)} chars, content_len={len(str(content))}")
        
        return context_str, filters
    
    def _build_generation_prompt(self, context: str) -> str:
        """
        Build the LLM prompt for question generation.
        
        Args:
            context: Document context string
            
        Returns:
            Prompt string
        """
        prompt = f"""You are a search engine optimization expert. Your task is to generate 8-10 natural, diverse questions that a user might search to find this document.

DOCUMENT CONTEXT:
{context}

REQUIREMENTS:
1. Generate EXACTLY 8-10 questions
2. Questions must be strictly grounded in the provided context — NO HALLUCINATION
3. Vary question styles:
   - Factual questions (who, what, when, where)
   - Reflective questions (why, how, meaning)
   - Practical questions (how-to, tips)
   - Location-based questions (if location is mentioned)
   - Time-based questions (if date is mentioned)
4. Questions should be natural language, as a user would type them
5. Questions should be between 5-15 words
6. Return ONLY the list of questions, one per line, no numbering or formatting

Generate the questions now:"""
        
        return prompt
    
    async def generate_questions_for_document(
        self,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
        embedding_model,
    ) -> List[GeneratedQuestion]:
        """
        Generate questions for a single document.
        
        Args:
            doc_id: Document ID
            doc_type: Document type
            metadata: Document metadata
            processed_data: Processed/extracted content
            original_file: Original filename
            embedding_model: SentenceTransformer for embedding questions
            
        Returns:
            List of GeneratedQuestion objects
        """
        logger.info(f"[QUESTION-GEN] Generating questions for document {doc_id}")
        
        try:
            # Extract context and filters
            context, filters = self._extract_document_context(
                doc_id, doc_type, metadata, processed_data, original_file
            )
            
            if not context.strip():
                logger.warning(f"[QUESTION-GEN] No context extracted for doc {doc_id}")
                return []
            
            # Build prompt
            prompt = self._build_generation_prompt(context)
            
            # Call Ollama
            logger.debug(f"[QUESTION-GEN] Calling Ollama for doc {doc_id}")
            response = await self._call_ollama(prompt)
            
            if not response:
                logger.error(f"[QUESTION-GEN] No response from Ollama for doc {doc_id}")
                return []
            
            # Parse questions from response
            questions_text = response.strip()
            question_lines = [line.strip() for line in questions_text.split("\n") if line.strip()]
            
            # Clean up questions (remove numbering, bullets, etc.)
            questions = []
            for line in question_lines:
                # Remove common numbering patterns: "1.", "1)", "- ", "* "
                cleaned = line.lstrip("0123456789).‐-*•").strip()
                if cleaned and len(cleaned) > 5:
                    questions.append(cleaned)
            
            # Limit to 10 questions
            questions = questions[:10]
            
            if not questions:
                logger.warning(f"[QUESTION-GEN] Could not parse any questions from Ollama response for doc {doc_id}")
                return []
            
            logger.info(f"[QUESTION-GEN] Generated {len(questions)} questions for doc {doc_id}")
            
            # Create GeneratedQuestion objects with embeddings
            generated_questions = []
            now = datetime.now(timezone.utc).isoformat()
            
            for idx, question_text in enumerate(questions):
                q_id = str(uuid.uuid4())
                
                # Embed the question
                embedding = None
                if embedding_model:
                    try:
                        embedding = embedding_model.encode(question_text).tolist()
                    except Exception as e:
                        logger.warning(f"[QUESTION-GEN] Failed to embed question: {e}")
                
                q = GeneratedQuestion(
                    question_id=q_id,
                    text=question_text,
                    provenance=doc_id,
                    filters=filters,
                    suggestion_type="question",
                    embedding=embedding,
                    created_at=now,
                    updated_at=now,
                    model="ollama",
                )
                generated_questions.append(q)
            
            logger.debug(f"[QUESTION-GEN] Created {len(generated_questions)} question objects for doc {doc_id}")
            return generated_questions
            
        except Exception as e:
            logger.error(f"[QUESTION-GEN] Failed to generate questions for doc {doc_id}: {e}", exc_info=True)
            return []
    
    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call Ollama API to generate text.
        
        Args:
            prompt: Prompt string
            
        Returns:
            Generated text or None
        """
        try:
            import aiohttp
            
            base_url = self.ollama_provider.base_url
            model = self.ollama_provider.model
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                        },
                    },
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as response:
                    if response.status != 200:
                        logger.error(f"[QUESTION-GEN] Ollama API returned status {response.status}")
                        return None
                    
                    result = await response.json()
                    return result.get("response", "").strip()
        except Exception as e:
            logger.error(f"[QUESTION-GEN] Failed to call Ollama: {e}", exc_info=True)
            return None
    
    async def regenerate_questions_for_document(
        self,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
        embedding_model,
    ) -> Tuple[List[GeneratedQuestion], bool]:
        """
        Regenerate questions for an existing document.
        
        Args:
            doc_id: Document ID
            doc_type: Document type
            metadata: Updated metadata
            processed_data: Updated processed data
            original_file: Original filename
            embedding_model: SentenceTransformer
            
        Returns:
            (list of new questions, success flag)
        """
        logger.info(f"[QUESTION-GEN] Regenerating questions for document {doc_id}")
        
        try:
            questions = await self.generate_questions_for_document(
                doc_id, doc_type, metadata, processed_data, original_file, embedding_model
            )
            return questions, len(questions) > 0
        except Exception as e:
            logger.error(f"[QUESTION-GEN] Failed to regenerate questions for doc {doc_id}: {e}", exc_info=True)
            return [], False
