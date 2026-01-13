# LangChain Ollama Quick Reference

## Quick Start

1. **Install dependencies:**
   ```bash
   cd /backend
   pip install -r requirements.txt
   ```

2. **Ensure Ollama is running:**
   ```bash
   ollama serve
   # or via Docker
   docker run -d -p 11434:11434 ollama/ollama
   ```

3. **Pull models:**
   ```bash
   ollama pull mistral         # LLM model
   ollama pull nomic-embed-text  # Embedding model
   ```

4. **Set environment (optional, defaults work):**
   ```bash
   export OLLAMA_HOST=http://localhost:11434
   export OLLAMA_MODEL=mistral
   export OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```

5. **Start Flask app:**
   ```bash
   python run.py  # or python -m flask run
   ```

## API Quick Commands

```bash
# Health check
curl http://localhost:5000/api/langchain/health

# Get single response
curl -X POST http://localhost:5000/api/langchain/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Get batch responses
curl -X POST http://localhost:5000/api/langchain/batch \
  -H "Content-Type: application/json" \
  -d '{"prompts": ["What is AI?", "What is ML?"]}'

# Get embeddings
curl -X POST http://localhost:5000/api/langchain/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["text1", "text2"]}'

# Chat (with memory)
curl -X POST http://localhost:5000/api/langchain/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# Get config
curl http://localhost:5000/api/langchain/config

# Stream response
curl -X POST http://localhost:5000/api/langchain/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a poem"}' \
  --no-buffer
```

## Python Integration

```python
from app.services.langchain_service import get_langchain_service

service = get_langchain_service()

# Single invoke
response = service.invoke("What is AI?")

# Batch invoke
responses = service.batch_invoke(["Q1?", "Q2?", "Q3?"])

# Embeddings
embeds = service.get_embeddings(["text1", "text2"])

# Chat with memory
service.create_conversation_chain()
resp1 = service.chat("What is AI?")
resp2 = service.chat("Explain more")  # remembers context

# Health check
is_ok = service.health_check()

# Streaming
for chunk in service.stream_invoke("Tell me a story"):
    print(chunk, end="")
```

## Docker Compose

```yaml
version: '3'
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama_data:/root/.ollama

  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=mistral
      - OLLAMA_EMBEDDING_MODEL=nomic-embed-text
    depends_on:
      - ollama

volumes:
  ollama_data:
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to Ollama" | Verify Ollama running: `curl http://OLLAMA_HOST:11434/api/tags` |
| "Model not found" | Pull model: `ollama pull mistral` |
| Slow responses | Check Ollama logs, ensure sufficient GPU/CPU |
| ImportError: No module | Run: `pip install -r requirements.txt` |
| Port 11434 in use | Change OLLAMA_HOST or stop other Ollama instances |

## Environment Variables

```bash
OLLAMA_HOST=http://ollama:11434       # Ollama server URL
OLLAMA_MODEL=mistral                   # LLM model name
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # Embedding model
```

## Available Models

**LLM Models:**
- `mistral` - Fast, good quality (recommended)
- `neural-chat` - Optimized for conversations
- `dolphin-mixtral` - High quality
- `llama2` - General purpose

**Embedding Models:**
- `nomic-embed-text` - Best quality (recommended)
- `all-minilm` - Faster, reasonable quality

Pull with: `ollama pull MODEL_NAME`

## Files Modified/Created

- ✅ `backend/requirements.txt` - Added dependencies
- ✅ `backend/app/services/langchain_service.py` - Main service
- ✅ `backend/app/routes/langchain_routes.py` - API endpoints
- ✅ `backend/app/routes/__init__.py` - Blueprint registration
- ✅ `LANGCHAIN_OLLAMA_SETUP.md` - Full documentation

## Next Steps

1. Install: `pip install -r backend/requirements.txt`
2. Test: `curl http://localhost:5000/api/langchain/health`
3. Integrate into your app routes as needed
4. Refer to full guide: `LANGCHAIN_OLLAMA_SETUP.md`
