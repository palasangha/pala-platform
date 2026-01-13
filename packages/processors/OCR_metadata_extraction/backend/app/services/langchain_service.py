"""LangChain integration service for Ollama LLM."""

import os
from typing import Optional, List, Dict, Any
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
import logging

logger = logging.getLogger(__name__)


class LangChainOllamaService:
    """Service for managing LangChain integration with Ollama."""
    
    def __init__(self, 
                 ollama_host: Optional[str] = None,
                 model: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 temperature: float = 0.7,
                 top_k: int = 40,
                 top_p: float = 0.9):
        """
        Initialize LangChain Ollama service.
        
        Args:
            ollama_host: Ollama server URL (default: http://localhost:11434)
            model: LLM model name (default: 'mistral')
            embedding_model: Embedding model name (default: 'nomic-embed-text')
            temperature: Model temperature (0-1)
            top_k: Top K sampling parameter
            top_p: Nucleus sampling parameter
        """
        self.ollama_host = ollama_host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'llama3.2-vision:11b')
        self.embedding_model = embedding_model or os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        
        self._llm: Optional[Ollama] = None
        self._embeddings: Optional[OllamaEmbeddings] = None
        self._conversation_chain: Optional[ConversationChain] = None
        
        logger.info(f"Initializing LangChain Ollama service with host: {self.ollama_host}")
    
    @property
    def llm(self) -> Ollama:
        """Get or initialize the LLM."""
        if self._llm is None:
            self._llm = Ollama(
                base_url=self.ollama_host,
                model=self.model,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
            )
        return self._llm
    
    @property
    def embeddings(self) -> OllamaEmbeddings:
        """Get or initialize embeddings."""
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                base_url=self.ollama_host,
                model=self.embedding_model,
            )
        return self._embeddings
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Get a completion from the LLM.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The LLM's response
        """
        try:
            response = self.llm.invoke(prompt, **kwargs)
            return response
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            raise
    
    def batch_invoke(self, prompts: List[str], **kwargs) -> List[str]:
        """
        Get completions for multiple prompts.
        
        Args:
            prompts: List of input prompts
            **kwargs: Additional parameters for the LLM
            
        Returns:
            List of LLM responses
        """
        try:
            responses = self.llm.batch(prompts, **kwargs)
            return responses
        except Exception as e:
            logger.error(f"Error in batch invoke: {e}")
            raise
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.embeddings.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def create_conversation_chain(self, memory_size: int = 10) -> Optional[Dict]:
        """
        Create a conversation chain with memory.
        
        Args:
            memory_size: Number of messages to keep in memory
            
        Returns:
            Dict-based conversation structure
        """
        try:
            # Use simple dict-based conversation
            self._conversation_chain = {
                'messages': [],
                'memory_size': memory_size
            }
            return self._conversation_chain
        except Exception as e:
            logger.error(f"Error creating conversation chain: {e}")
            self._conversation_chain = {
                'messages': [],
                'memory_size': memory_size
            }
            return self._conversation_chain
    
    def chat(self, message: str) -> str:
        """
        Chat with the LLM (requires conversation chain).
        
        Args:
            message: User message
            
        Returns:
            LLM response
        """
        if self._conversation_chain is None:
            self.create_conversation_chain()
        
        try:
            # Dict-based conversation for newer LangChain versions
            messages = self._conversation_chain['messages']
            memory_size = self._conversation_chain['memory_size']
            
            # Build context from recent messages
            context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-memory_size:]])
            if context:
                prompt = f"{context}\nUser: {message}\nAssistant:"
            else:
                prompt = f"User: {message}\nAssistant:"
            
            response = self.llm.invoke(prompt)
            
            # Store messages
            messages.append({'role': 'User', 'content': message})
            messages.append({'role': 'Assistant', 'content': response})
            
            return response
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if Ollama server is accessible.
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            # Try to invoke the LLM with a simple prompt
            self.llm.invoke("test")
            logger.info("Ollama server health check passed")
            return True
        except Exception as e:
            logger.error(f"Ollama server health check failed: {e}")
            return False
    
    def stream_invoke(self, prompt: str, **kwargs):
        """
        Stream completions from the LLM.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the LLM
            
        Yields:
            Chunks of the response
        """
        try:
            for chunk in self.llm.stream(prompt, **kwargs):
                yield chunk
        except Exception as e:
            logger.error(f"Error in stream invoke: {e}")
            raise


# Global service instance
_service_instance: Optional[LangChainOllamaService] = None


def get_langchain_service(
    ollama_host: Optional[str] = None,
    model: Optional[str] = None,
    embedding_model: Optional[str] = None
) -> LangChainOllamaService:
    """
    Get or create the global LangChain Ollama service instance.
    
    Args:
        ollama_host: Ollama server URL
        model: LLM model name
        embedding_model: Embedding model name
        
    Returns:
        LangChainOllamaService instance
    """
    global _service_instance
    
    if _service_instance is None:
        _service_instance = LangChainOllamaService(
            ollama_host=ollama_host,
            model=model,
            embedding_model=embedding_model,
        )
    
    return _service_instance
