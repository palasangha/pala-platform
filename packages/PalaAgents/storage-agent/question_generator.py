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

import asyncio
import json
import logging
import re
import textwrap
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field

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
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    answer_preview: str = ""
    answer_span: Optional[Dict[str, Any]] = None
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

    def _extract_evidence_for_question(
        self,
        question_text: str,
        processed_data: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Extract verbatim evidence snippets from document text for a question.
        
        Algorithm:
        1. Extract keywords from question (excluding stop words)
        2. Score each line by keyword match count
        3. Penalize very short lines (likely filler/metadata)
        4. Return single best match only (not top 2) to avoid irrelevant results
        5. Calculate confidence as keyword_match_ratio, with minimum of 0.5 for any match
        
        Returns:
            (evidence_list, answer_preview) where evidence_list contains one dict with:
            - source_path: where content came from
            - line_start/line_end: line numbers (1-indexed)
            - snippet: excerpt (max 300 chars)
            - confidence: 0.0-1.0 score
        """
        if not isinstance(processed_data, dict):
            return [], ""

        content_text = ""
        source_path = "processed_data.content"

        result_payload = processed_data.get("result") if isinstance(processed_data.get("result"), dict) else {}

        for key, path in (
            ("content", "processed_data.content"),
            ("text", "processed_data.text"),
            ("ocr_text", "processed_data.ocr_text"),
        ):
            value = processed_data.get(key)
            if isinstance(value, str) and value.strip():
                content_text = value
                source_path = path
                break

        if not content_text:
            for key, path in (
                ("content", "processed_data.result.content"),
                ("text", "processed_data.result.text"),
                ("ocr_text", "processed_data.result.ocr_text"),
            ):
                value = result_payload.get(key)
                if isinstance(value, str) and value.strip():
                    content_text = value
                    source_path = path
                    break

        if not content_text:
            return [], ""

        lines = [line.strip() for line in content_text.splitlines() if line.strip()]
        if not lines:
            lines = [content_text.strip()]

        def format_snippet_lines(snippet_lines: List[str], max_chars_per_line: int = 130) -> List[str]:
            formatted_lines: List[str] = []
            for snippet_line in snippet_lines:
                compact_line = re.sub(r"\s+", " ", snippet_line).strip()
                if not compact_line:
                    continue

                wrapped_lines = textwrap.wrap(
                    compact_line,
                    width=max_chars_per_line,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                formatted_lines.extend(wrapped_lines if wrapped_lines else [compact_line])
            return formatted_lines

        def build_snippet_text(snippet_lines: List[str]) -> str:
            formatted_lines = format_snippet_lines(snippet_lines)
            return "\n".join(formatted_lines).strip()

        # Extract meaningful keywords from question, allowing some short but important words
        stop_words = {"what", "when", "where", "which", "how", "why", "was", "were", "the", "and", "or", "in", "of", "to", "a", "an", "is", "be", "by", "for", "on", "at", "as", "about", "their", "there", "these", "those", "would", "could", "should", "document", "context", "from", "during", "that"}
        question_terms = [
            token
            for token in re.findall(r"[A-Za-z0-9]+", question_text.lower())
            if len(token) > 2 and token not in stop_words
        ]

        if not question_terms:
            # Return a compact 6-line preview when no strong question terms
            snippet_lines = format_snippet_lines(lines[0:6])
            snippet = build_snippet_text(snippet_lines)
            return [
                {
                    "source_path": source_path,
                    "line_start": 1,
                    "line_end": min(6, len(lines)),
                    "span": {"line_start": 1, "line_end": min(6, len(lines))},
                    "snippet": snippet,
                    "confidence": 0.3,
                }
            ], snippet

        scored_lines: List[Tuple[int, int, str]] = []
        for idx, line in enumerate(lines):
            lower = line.lower()
            # Count matching keywords
            score = sum(1 for term in question_terms if term in lower)
            # Penalize very short lines (likely filler)
            line_length_penalty = 0 if len(line) >= 50 else -0.5
            adjusted_score = score + line_length_penalty
            
            if score > 0:
                scored_lines.append((adjusted_score, score, idx, line))
                # Detailed per-line debug logging to help trace evidence selection
                logger.debug(
                    "[EVIDENCE-SCORE] question=%s line_index=%d raw_score=%s len=%d length_penalty=%s adjusted_score=%s snippet=%s",
                    question_text[:80].replace("\n", " "),
                    idx,
                    score,
                    len(line),
                    line_length_penalty,
                    adjusted_score,
                    (line[:160].replace('\n',' '))
                )

        if not scored_lines:
            # No exact match found - try partial matching with any keyword appearing in any line
            partial_matches: List[Tuple[int, int, str]] = []
            for idx, line in enumerate(lines):
                lower = line.lower()
                # Count ANY keyword match (even partial word matches)
                partial_score = sum(1 for term in question_terms if term in lower)
                if partial_score > 0:
                    partial_matches.append((partial_score, idx, line))
            
            if partial_matches:
                # Found partial matches - use the best one
                partial_matches.sort(key=lambda x: (-x[0], x[1]))  # Sort by score desc, then index asc
                best_partial = partial_matches[0]
                score, idx, line = best_partial
                # Provide a wider context window: aim for 6-12 lines with matched line in middle
                lines_before = 4
                lines_after = 5
                start_idx = max(0, idx - lines_before)
                end_idx = min(len(lines), idx + lines_after + 1)
                # Adjust to ensure we get 6-12 lines
                actual_lines = end_idx - start_idx
                if actual_lines < 6 and len(lines) >= 6:
                    if start_idx == 0:
                        end_idx = min(len(lines), 9)
                    else:
                        start_idx = max(0, end_idx - 9)
                snippet_lines = format_snippet_lines(lines[start_idx:end_idx])
                snippet = build_snippet_text(snippet_lines)
                confidence = round(min(score / max(len(question_terms), 1), 1.0), 3)
                confidence = max(confidence, 0.4)
            else:
                # Still no match - return first 6-9 lines as last resort
                snippet_lines = format_snippet_lines(lines[0:9])
                snippet = build_snippet_text(snippet_lines)
                start_idx = 0
                end_idx = len(snippet_lines)
                idx = 0
                confidence = 0.25
            
            return [
                {
                    "source_path": source_path,
                    "line_start": start_idx + 1,
                    "line_end": end_idx,
                    "span": {"line_start": start_idx + 1, "line_end": end_idx},
                    "snippet": snippet,
                    "confidence": confidence,
                }
            ], snippet

        # Sort by adjusted score (descending), then raw score (descending), then position (ascending)
        scored_lines.sort(key=lambda item: (-item[0], -item[1], item[2]))
        
        # Only take the top match (single best evidence)
        best_match = scored_lines[0]
        adjusted_score, raw_score, idx, line = best_match
        # Log the top candidates for further inspection
        try:
            top_preview = [
                {
                    'rank': i+1,
                    'adjusted_score': float(item[0]),
                    'raw_score': int(item[1]),
                    'line_index': int(item[2]),
                    'snippet': (item[3][:180].replace('\n',' ')),
                }
                for i, item in enumerate(scored_lines[:6])
            ]
            logger.debug("[EVIDENCE-TOP-CANDIDATES] question=%s top_candidates=%s", question_text[:80].replace("\n"," "), top_preview)
        except Exception:
            logger.debug("[EVIDENCE-TOP-CANDIDATES] could not format top candidates for question: %s", question_text[:80].replace("\n"," "))
        
        # Calculate confidence: raw_score / max_possible_terms
        max_terms = len(question_terms)
        confidence = round(min(raw_score / max(max_terms, 1), 1.0), 3)
        
        # Ensure minimum confidence even for partial matches
        confidence = max(confidence, 0.5) if raw_score > 0 else 0.3

        logger.debug(
            "[EVIDENCE-SELECTED] question=%s selected_index=%d raw_score=%s adjusted_score=%s confidence=%s snippet=%s",
            question_text[:120].replace("\n"," "),
            idx,
            raw_score,
            adjusted_score,
            confidence,
            (line[:240].replace('\n',' '))
        )

        # Build a context window: aim for 6-12 lines with matched line in middle
        lines_before = 4
        lines_after = 5
        start_idx = max(0, idx - lines_before)
        end_idx = min(len(lines), idx + lines_after + 1)
        
        # Adjust to ensure we get 6-12 lines
        actual_lines = end_idx - start_idx
        if actual_lines < 6 and len(lines) >= 6:
            if start_idx == 0:
                end_idx = min(len(lines), 9)
            else:
                start_idx = max(0, end_idx - 9)
        
        preview_lines = format_snippet_lines(lines[start_idx:end_idx])
        snippet_text = build_snippet_text(preview_lines)
        evidence = [
            {
                "source_path": source_path,
                "line_start": start_idx + 1,
                "line_end": end_idx,
                "span": {"line_start": start_idx + 1, "line_end": end_idx},
                "snippet": snippet_text,
                "confidence": confidence,
            }
        ]

        return evidence, evidence[0]["snippet"] if evidence else ""
    
    async def generate_questions_for_document(
        self,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
        embedding_model,
            verify_with_llm: bool = False,
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

                evidence, answer_preview = self._extract_evidence_for_question(
                    question_text=question_text,
                    processed_data=processed_data,
                )
                answer_span = evidence[0].get("span") if evidence else None
                
                q = GeneratedQuestion(
                    question_id=q_id,
                    text=question_text,
                    provenance=doc_id,
                    filters=filters,
                    suggestion_type="question",
                    embedding=embedding,
                    evidence=evidence,
                    answer_preview=answer_preview,
                    answer_span=answer_span,
                    created_at=now,
                    updated_at=now,
                    model="ollama",
                )
                generated_questions.append(q)
            
            logger.debug(f"[QUESTION-GEN] Created {len(generated_questions)} question objects for doc {doc_id}")
            # Post-process: embedding-based fallback for low-confidence or repeated snippets
            try:
                # Build mapping of snippet -> count
                snippet_counts = {}
                for q in generated_questions:
                    ev = q.evidence or []
                    sn = (ev[0]['snippet'].strip() if ev else '')
                    if sn:
                        snippet_counts[sn] = snippet_counts.get(sn, 0) + 1

                # Prepare document text for embedding fallback
                content_text = ''
                if isinstance(processed_data, dict):
                    # try same order as extractor
                    for key in ('content', 'text', 'ocr_text'):
                        val = processed_data.get(key)
                        if isinstance(val, str) and val.strip():
                            content_text = val
                            break
                    if not content_text:
                        res = processed_data.get('result') if isinstance(processed_data.get('result'), dict) else {}
                        for key in ('content', 'text', 'ocr_text'):
                            val = res.get(key)
                            if isinstance(val, str) and val.strip():
                                content_text = val
                                break

                # If embedding model is available, compute sentence embeddings once
                sentence_list = []
                sentence_embeddings = None
                if embedding_model and content_text and isinstance(content_text, str):
                    # Split into sentences (simple splitter)
                    import re
                    sentence_list = [s.strip() for s in re.split(r'(?<=[\.!?])\s+', content_text) if s.strip()]
                    if sentence_list:
                        try:
                            sentence_embeddings = embedding_model.encode(sentence_list)
                        except Exception as e:
                            logger.debug(f"[EVIDING-FALLBACK] Failed to encode sentences: {e}")

                # Helper to run embedding fallback for single question
                def _embedding_fallback_for_question(q_text: str):
                    if not sentence_list or sentence_embeddings is None:
                        return None
                    try:
                        q_emb = embedding_model.encode([q_text])[0]
                        # cosine similarity
                        import math
                        best_idx = None
                        best_sim = -1.0
                        for i, sent_emb in enumerate(sentence_embeddings):
                            # some encoders return lists, ensure numeric arrays
                            numer = sum(float(a) * float(b) for a, b in zip(q_emb, sent_emb))
                            denom_a = math.sqrt(sum(float(a) * float(a) for a in q_emb))
                            denom_b = math.sqrt(sum(float(b) * float(b) for b in sent_emb))
                            sim = numer / (denom_a * denom_b + 1e-12)
                            if sim > best_sim:
                                best_sim = sim
                                best_idx = i
                        if best_idx is None:
                            return None
                        chosen = sentence_list[best_idx]
                        # scale similarity to confidence-like value
                        conf = round(float(best_sim), 3)
                        return {
                            'source_path': 'processed_data.content',
                            'line_start': best_idx + 1,
                            'line_end': best_idx + 1,
                            'span': {'line_start': best_idx + 1, 'line_end': best_idx + 1},
                            'snippet': chosen[:300],
                            'confidence': conf,
                        }
                    except Exception as e:
                        logger.debug(f"[EVIDENCE-FALLBACK] Exception during embedding fallback: {e}")
                        return None

                # Apply fallback where needed
                for q in generated_questions:
                    ev = q.evidence or []
                    sn = (ev[0]['snippet'].strip() if ev else '')
                    conf = float(ev[0].get('confidence', 0.0)) if ev else 0.0

                    need_fallback = False
                    # condition: low confidence or snippet repeated many times
                    # Tighten baseline threshold: require confidence >= 0.65 to avoid weak replacements
                    if conf < 0.65:
                        need_fallback = True
                    if sn and snippet_counts.get(sn, 0) > 1:
                        need_fallback = True

                    if need_fallback and embedding_model and sentence_list:
                        fallback = _embedding_fallback_for_question(q.text)
                        # Only accept fallback if embedding similarity/confidence meets threshold
                        if fallback and float(fallback.get('confidence', 0.0)) >= 0.65:
                            # Optionally verify with LLM if requested and provider available
                            verified = True
                            if verify_with_llm and hasattr(self, '_call_ollama') and callable(self._call_ollama):
                                try:
                                    # Run verification synchronously in event loop
                                    async def _verify():
                                        return await self._verify_evidence_with_ollama(q.text, fallback['snippet'])
                                    verified = asyncio.get_event_loop().run_until_complete(_verify())
                                except Exception:
                                    verified = True

                            if verified:
                                # Keep the fallback snippet exactly as extracted so line counts stay stable.
                                snippet = fallback.get('snippet', '')
                                q.evidence = [fallback]
                                q.evidence[0]['snippet'] = snippet
                                q.answer_preview = q.evidence[0]['snippet']
                                q.answer_span = fallback.get('span')

            except Exception as e:
                logger.debug(f"[QUESTION-GEN] Post-process embedding fallback failed: {e}")

            # Apply quality gate: balance between quality and quantity
            # More lenient than before to ensure we get enough questions
            MIN_QUESTIONS = 3  # Lowered to 3 to avoid being too strict
            CONFIDENCE_FLOOR = 0.55  # Lowered to 0.55 to allow more questions
            
            # First pass: count snippet occurrences to identify heavily redundant ones
            snippet_counts = {}
            for q in generated_questions:
                ev = q.evidence or []
                snippet = ev[0].get('snippet', '').strip() if ev else ''
                if snippet:
                    snippet_key = snippet[:100].lower()
                    snippet_counts[snippet_key] = snippet_counts.get(snippet_key, 0) + 1
            
            # Identify redundant snippet keys (shared by 3+ questions - heavily redundant)
            # Only reject if shared by 3+ questions, not just 2 (allows some related questions)
            redundant_snippets = {key for key, count in snippet_counts.items() if count > 2}
            
            quality_filtered = []
            
            for q in generated_questions:
                ev = q.evidence or []
                conf = float(ev[0].get('confidence', 0.0)) if ev else 0.0
                snippet = ev[0].get('snippet', '').strip() if ev else ''
                
                # Reject if snippet is heavily redundant (shared by 3+ questions)
                if snippet:
                    snippet_key = snippet[:100].lower()
                    if snippet_key in redundant_snippets:
                        logger.info(f"[QUALITY-GATE] REJECT question (snippet shared by {snippet_counts[snippet_key]} questions): {q.text[:80]}")
                        continue
                
                # Accept question if confidence meets floor
                if conf >= CONFIDENCE_FLOOR:
                    quality_filtered.append(q)
                    logger.debug(f"[QUALITY-GATE] ACCEPT question: conf={conf:.2f}, q={q.text[:80]}")
                else:
                    logger.info(f"[QUALITY-GATE] REJECT question (conf={conf:.2f} < {CONFIDENCE_FLOOR}): {q.text[:80]}")
            
            logger.info(f"[QUESTION-GEN] Quality gate: {len(generated_questions)} candidates → {len(quality_filtered)} passed (confidence >= {CONFIDENCE_FLOOR})")
            
            # If below minimum, regenerate for more questions
            if len(quality_filtered) < MIN_QUESTIONS:
                logger.info(f"[QUESTION-GEN] Only {len(quality_filtered)} questions; regenerating for more diversity...")
                
                # Ask for additional diverse questions
                regen_prompt = f"""{self._build_generation_prompt(context)}

NOTE: You previously generated: {', '.join(q.text[:50] + '...' for q in generated_questions[:3])}

Please generate 8-10 COMPLETELY DIFFERENT questions covering other aspects and details not in the above list."""
                
                try:
                    regen_response = await self._call_ollama(regen_prompt)
                    
                    if regen_response:
                        regen_lines = [line.strip() for line in regen_response.split("\n") if line.strip()]
                        regen_questions_text = []
                        for line in regen_lines:
                            cleaned = line.lstrip("0123456789).‐-*•").strip()
                            if cleaned and len(cleaned) > 5:
                                regen_questions_text.append(cleaned)
                        
                        logger.info(f"[QUESTION-GEN] Regenerated {len(regen_questions_text)} additional questions")
                        
                        # Process regenerated questions
                        now = datetime.now(timezone.utc).isoformat()
                        for regen_q_text in regen_questions_text:
                            if len(quality_filtered) >= MIN_QUESTIONS:
                                break
                            
                            q_id = str(uuid.uuid4())
                            
                            # Embed
                            embedding = None
                            if embedding_model:
                                try:
                                    embedding = embedding_model.encode(regen_q_text).tolist()
                                except Exception:
                                    pass
                            
                            # Extract evidence
                            evidence, answer_preview = self._extract_evidence_for_question(
                                question_text=regen_q_text,
                                processed_data=processed_data,
                            )
                            answer_span = evidence[0].get("span") if evidence else None
                            
                            q = GeneratedQuestion(
                                question_id=q_id,
                                text=regen_q_text,
                                provenance=doc_id,
                                filters=filters,
                                suggestion_type="question",
                                embedding=embedding,
                                evidence=evidence,
                                answer_preview=answer_preview,
                                answer_span=answer_span,
                                created_at=now,
                                updated_at=now,
                                model="ollama",
                            )
                            
                            # Check quality
                            ev = q.evidence or []
                            conf = float(ev[0].get('confidence', 0.0)) if ev else 0.0
                            snippet = ev[0].get('snippet', '').strip() if ev else ''
                            
                            # Reject if snippet is redundant (shared by multiple questions)
                            if snippet:
                                snippet_key = snippet[:100].lower()
                                if snippet_key in redundant_snippets:
                                    logger.info(f"[QUALITY-GATE] REJECT regenerated (snippet shared): {q.text[:80]}")
                                    continue
                            
                            if conf >= CONFIDENCE_FLOOR:
                                quality_filtered.append(q)
                                logger.debug(f"[QUALITY-GATE] ACCEPT regenerated: conf={conf:.2f}, q={q.text[:80]}")
                            else:
                                logger.info(f"[QUALITY-GATE] REJECT regenerated (conf={conf:.2f} < {CONFIDENCE_FLOOR}): {q.text[:80]}")
                except Exception as e:
                    logger.warning(f"[QUESTION-GEN] Regeneration failed: {e}")
            
            # Return best effort: cap at 10, or return what we have
            final_questions = quality_filtered[:10]
            logger.info(f"[QUESTION-GEN] Returning {len(final_questions)} questions (minimum target: {MIN_QUESTIONS})")
            
            return final_questions if final_questions else generated_questions[:min(3, len(generated_questions))]
            
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
            import json as json_module
            from urllib import request as urllib_request
            from urllib.error import URLError, HTTPError
            
            base_url = self.ollama_provider.base_url
            model = self.ollama_provider.model

            def _post_ollama() -> Optional[str]:
                payload = json_module.dumps({
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                    },
                }).encode("utf-8")

                req = urllib_request.Request(
                    f"{base_url}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                try:
                    with urllib_request.urlopen(req, timeout=120) as response:
                        if getattr(response, "status", 200) != 200:
                            logger.error(f"[QUESTION-GEN] Ollama API returned status {getattr(response, 'status', 'unknown')}")
                            return None
                        body = response.read().decode("utf-8")
                        result = json_module.loads(body)
                        return str(result.get("response", "")).strip()
                except HTTPError as error:
                    logger.error(f"[QUESTION-GEN] Ollama HTTP error: {error}")
                    return None
                except URLError as error:
                    logger.error(f"[QUESTION-GEN] Ollama URL error: {error}")
                    return None

            return await asyncio.to_thread(_post_ollama)
        except Exception as e:
            logger.error(f"[QUESTION-GEN] Failed to call Ollama: {e}", exc_info=True)
            return None

    async def _verify_evidence_with_ollama(self, question_text: str, snippet: str) -> bool:
        """Ask the LLM to verify whether `snippet` answers `question_text`."""
        try:
            verify_prompt = f"Question: {question_text}\n\nSnippet: {snippet}\n\nDoes the snippet directly answer the question above? Answer with 'Yes' or 'No' and one short sentence justification."
            resp = await self._call_ollama(verify_prompt)
            if not resp:
                return False
            low = resp.strip().lower()
            if low.startswith('yes') or ' yes' in low.split()[:2]:
                return True
            if 'no' in low.split()[:2] or low.startswith('no'):
                return False
            # fallback: if response contains clear affirmative
            if 'yes' in low:
                return True
            return False
        except Exception as e:
            logger.debug(f"[EVIDENCE-VERIFY] Ollama verification failed: {e}")
            return False
    
    async def regenerate_questions_for_document(
        self,
        doc_id: str,
        doc_type: str,
        metadata: Dict[str, Any],
        processed_data: Dict[str, Any],
        original_file: str,
        embedding_model,
        verify_with_llm: bool = False,
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
                doc_id, doc_type, metadata, processed_data, original_file, embedding_model, verify_with_llm=verify_with_llm
            )
            return questions, len(questions) > 0
        except Exception as e:
            logger.error(f"[QUESTION-GEN] Failed to regenerate questions for doc {doc_id}: {e}", exc_info=True)
            return [], False
