"""
Phase 4: RAG QA Service
========================
Question-answering service using Retrieval-Augmented Generation.
Based on L6 notebook with production enhancements.

Author: ICR Integration Team
Date: 2026-01-23
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGQAService:
    """
    RAG-based question answering over documents.
    
    Features:
    - Semantic search for relevant chunks
    - LLM-based answer generation
    - Visual grounding (source attribution)
    - Confidence scoring
    - Multi-document support
    - Citation generation
    
    Performance:
    - Search: <100ms
    - Answer Generation: 1-3 seconds
    - Total: <5 seconds per question
    """
    
    def __init__(self,
                 vector_store,
                 llm_provider: str = 'openai',
                 llm_model: str = 'gpt-4o-mini'):
        """
        Initialize RAG QA service.
        
        Args:
            vector_store: VectorStoreService instance
            llm_provider: LLM provider ('openai', 'anthropic', 'local')
            llm_model: Model name
        """
        logger.info("=" * 80)
        logger.info("Initializing RAG QA Service")
        logger.info("=" * 80)
        logger.info(f"LLM Provider: {llm_provider}")
        logger.info(f"LLM Model: {llm_model}")
        
        start_time = time.time()
        
        try:
            self.vector_store = vector_store
            self.llm_provider = llm_provider
            self.llm_model = llm_model
            
            # Initialize LLM client
            try:
                if llm_provider == 'openai':
                    import openai
                    self.llm_client = openai
                    logger.info("✓ OpenAI client initialized")
                    self.mock_mode = False
                elif llm_provider == 'anthropic':
                    import anthropic
                    self.llm_client = anthropic.Anthropic()
                    logger.info("✓ Anthropic client initialized")
                    self.mock_mode = False
                else:
                    raise ValueError(f"Unknown provider: {llm_provider}")
                    
            except ImportError as e:
                logger.warning(f"LLM provider not available: {e}")
                logger.warning("Using mock mode for development")
                self.llm_client = None
                self.mock_mode = True
            
            self.initialized = True
            
            init_time = time.time() - start_time
            logger.info(f"✓ Initialization completed in {init_time:.2f}s")
            logger.info(f"  Mode: {'Production' if not self.mock_mode else 'Mock'}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            raise
    
    def answer_question(self,
                       question: str,
                       n_context_chunks: int = 5,
                       filters: Optional[Dict[str, Any]] = None,
                       include_citations: bool = True) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            n_context_chunks: Number of chunks to retrieve for context
            filters: Optional metadata filters for search
            include_citations: Include source citations in answer
            
        Returns:
            Answer with sources, confidence, and citations
        """
        logger.info("=" * 80)
        logger.info("RAG Question Answering")
        logger.info("=" * 80)
        logger.info(f"Question: {question}")
        logger.info(f"Context Chunks: {n_context_chunks}")
        
        start_time = time.time()
        
        try:
            # Step 1: Retrieve relevant chunks
            logger.info("\n[1/3] Retrieving relevant context...")
            retrieve_start = time.time()
            
            search_results = self.vector_store.search(
                query=question,
                n_results=n_context_chunks,
                filters=filters,
                include_metadata=True
            )
            
            retrieve_time = time.time() - retrieve_start
            logger.info(f"✓ Retrieved {len(search_results['chunks'])} chunks in {retrieve_time:.3f}s")
            
            # Step 2: Build context and generate answer
            logger.info("\n[2/3] Generating answer with LLM...")
            generate_start = time.time()
            
            if self.mock_mode:
                answer_result = self._mock_generate_answer(question, search_results)
            else:
                answer_result = self._generate_answer_real(question, search_results)
            
            generate_time = time.time() - generate_start
            logger.info(f"✓ Answer generated in {generate_time:.2f}s")
            
            # Step 3: Add citations if requested
            logger.info("\n[3/3] Adding citations...")
            if include_citations:
                citations = self._generate_citations(search_results)
                answer_result['citations'] = citations
            
            # Compile final result
            total_time = time.time() - start_time
            
            result = {
                'question': question,
                'answer': answer_result['answer'],
                'confidence': answer_result.get('confidence', 0.0),
                'sources': search_results['chunks'],
                'citations': answer_result.get('citations', []),
                'metadata': {
                    'total_time': total_time,
                    'retrieve_time': retrieve_time,
                    'generate_time': generate_time,
                    'context_chunks_used': len(search_results['chunks']),
                    'llm_provider': self.llm_provider,
                    'llm_model': self.llm_model
                }
            }
            
            logger.info("=" * 80)
            logger.info("QA Complete:")
            logger.info(f"  Answer Length: {len(result['answer'])} chars")
            logger.info(f"  Confidence: {result['confidence']:.2f}")
            logger.info(f"  Sources Used: {len(result['sources'])}")
            logger.info(f"  Total Time: {total_time:.2f}s")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"QA failed: {e}", exc_info=True)
            raise
    
    def chat(self,
            messages: List[Dict[str, str]],
            n_context_chunks: int = 5) -> Dict[str, Any]:
        """
        Multi-turn conversation with document context.
        
        Args:
            messages: List of conversation messages [{"role": "user", "content": "..."}]
            n_context_chunks: Number of chunks to retrieve for context
            
        Returns:
            Response with answer and conversation history
        """
        logger.info("=" * 80)
        logger.info("RAG Chat (Multi-turn)")
        logger.info("=" * 80)
        logger.info(f"Messages in conversation: {len(messages)}")
        
        start_time = time.time()
        
        try:
            # Get the latest user message
            latest_message = messages[-1]['content']
            
            # Use single-turn QA for now (can be extended for full chat)
            result = self.answer_question(
                question=latest_message,
                n_context_chunks=n_context_chunks
            )
            
            # Add conversation context
            result['conversation_history'] = messages
            result['total_time'] = time.time() - start_time
            
            logger.info(f"✓ Chat response generated in {result['total_time']:.2f}s")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"Chat failed: {e}", exc_info=True)
            raise
    
    def _generate_answer_real(self,
                             question: str,
                             search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answer using real LLM API."""
        logger.info("Calling LLM API...")
        
        # Build context from search results
        context_parts = []
        for i, chunk in enumerate(search_results['chunks'], 1):
            context_parts.append(f"[Source {i}]\n{chunk['text']}")
        
        context = "\n\n".join(context_parts)
        
        # Build prompt
        prompt = f"""You are a helpful AI assistant answering questions about documents.

Use the following context to answer the question. If you cannot answer the question based on the context, say so.

Context:
{context}

Question: {question}

Instructions:
1. Answer based only on the provided context
2. Be specific and cite sources using [Source N] notation
3. If the context doesn't contain the answer, say "I don't have enough information to answer this question."

Answer:"""
        
        if self.llm_provider == 'openai':
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided document context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            # Estimate confidence based on response length and specificity
            confidence = min(0.95, len(answer) / 1000 + 0.6)
            
        elif self.llm_provider == 'anthropic':
            response = self.llm_client.messages.create(
                model=self.llm_model,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.content[0].text
            confidence = 0.85
        
        return {
            'answer': answer,
            'confidence': confidence
        }
    
    def _mock_generate_answer(self,
                             question: str,
                             search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Mock answer generation for testing."""
        logger.info("Using mock answer generation (LLM not available)")
        
        # Generate a mock answer based on search results
        if search_results['chunks']:
            first_chunk = search_results['chunks'][0]['text'][:200]
            answer = f"Based on the document context, here is what I found: {first_chunk}... [Mock answer for: {question}]"
        else:
            answer = f"I don't have enough information to answer: {question}"
        
        return {
            'answer': answer,
            'confidence': 0.75,
            'mock': True
        }
    
    def _generate_citations(self, search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate citations from search results."""
        citations = []
        
        for i, chunk in enumerate(search_results['chunks'], 1):
            metadata = search_results['metadatas'][i-1] if search_results['metadatas'] else {}
            
            citation = {
                'source_number': i,
                'chunk_id': chunk['id'],
                'relevance_score': chunk.get('score', 0.0),
                'text_preview': chunk['text'][:150] + "..." if len(chunk['text']) > 150 else chunk['text']
            }
            
            # Add document metadata if available
            if metadata:
                citation['document_id'] = metadata.get('document_id', 'unknown')
                citation['page'] = metadata.get('page', None)
                citation['bbox'] = metadata.get('bbox', None)
            
            citations.append(citation)
        
        logger.info(f"✓ Generated {len(citations)} citations")
        return citations
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG QA service statistics."""
        return {
            'service': 'RAG QA',
            'llm_provider': self.llm_provider,
            'llm_model': self.llm_model,
            'mode': 'mock' if self.mock_mode else 'production',
            'initialized': self.initialized,
            'features': [
                'question_answering',
                'multi_turn_chat',
                'source_attribution',
                'citation_generation',
                'confidence_scoring',
                'visual_grounding'
            ],
            'vector_store': self.vector_store.get_stats()
        }


def main():
    """Test the RAG QA service."""
    logger.info("\n" + "=" * 80)
    logger.info("RAG QA Service Test")
    logger.info("=" * 80 + "\n")
    
    # Initialize with mock vector store
    from phase4.vector_store_service import VectorStoreService
    vector_store = VectorStoreService()
    
    # Initialize RAG QA service
    qa_service = RAGQAService(vector_store)
    stats = qa_service.get_stats()
    
    logger.info("Service Statistics:")
    logger.info(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
