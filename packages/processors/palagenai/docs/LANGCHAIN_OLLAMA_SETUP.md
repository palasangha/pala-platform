# LangChain Ollama Setup Guide

## Overview

LangChain has been integrated with your Ollama server for advanced LLM capabilities including:
- Direct LLM invocations
- Batch processing
- Text embeddings
- Conversation chains with memory
- Streaming responses
- Server health checks

## Installation

The dependencies have been added to `requirements.txt`:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install langchain>=0.1.0
pip install langchain-community>=0.0.1
pip install ollama>=0.1.0
```

## Configuration

LangChain uses the following environment variables (optional - defaults provided):

```bash
# Ollama server URL (default: http://localhost:11434)
OLLAMA_HOST=http://ollama:11434

# LLM model name (default: mistral)
OLLAMA_MODEL=mistral

# Embedding model name (default: nomic-embed-text)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

Add these to your `.env` file:

```
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=mistral
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## API Endpoints

All LangChain endpoints are prefixed with `/api/langchain/`:

### 1. Health Check

**GET** `/api/langchain/health`

Check if Ollama server is accessible.

**Response (200):**
```json
{
  "status": "healthy",
  "model": "mistral",
  "host": "http://ollama:11434"
}
```

**Response (503):**
```json
{
  "status": "unhealthy",
  "error": "Cannot connect to Ollama server"
}
```

### 2. Invoke LLM

**POST** `/api/langchain/invoke`

Get a single completion from the LLM.

**Request Body:**
```json
{
  "prompt": "What is machine learning?",
  "temperature": 0.7
}
```

**Response:**
```json
{
  "prompt": "What is machine learning?",
  "response": "Machine learning is a subset of artificial intelligence...",
  "model": "mistral"
}
```

### 3. Batch Invoke

**POST** `/api/langchain/batch`

Get completions for multiple prompts.

**Request Body:**
```json
{
  "prompts": [
    "What is AI?",
    "What is ML?",
    "What is DL?"
  ]
}
```

**Response:**
```json
{
  "prompts": ["What is AI?", "What is ML?", "What is DL?"],
  "responses": [
    "AI is artificial intelligence...",
    "ML is machine learning...",
    "DL is deep learning..."
  ],
  "model": "mistral"
}
```

### 4. Get Embeddings

**POST** `/api/langchain/embed`

Get embeddings for one or more texts.

**Request Body (single text):**
```json
{
  "texts": "Your text here"
}
```

**Request Body (multiple texts):**
```json
{
  "texts": ["Text 1", "Text 2", "Text 3"]
}
```

**Response (single):**
```json
{
  "text": "Your text here",
  "embedding": [0.123, 0.456, ...],
  "model": "nomic-embed-text"
}
```

**Response (multiple):**
```json
{
  "texts": ["Text 1", "Text 2"],
  "embeddings": [[0.123, 0.456, ...], [0.789, 0.012, ...]],
  "model": "nomic-embed-text"
}
```

### 5. Chat with Memory

**POST** `/api/langchain/chat`

Chat with the LLM maintaining conversation history.

**Request Body:**
```json
{
  "message": "Hello, how are you?"
}
```

**Response:**
```json
{
  "message": "Hello, how are you?",
  "response": "I'm doing well, thank you for asking!",
  "model": "mistral"
}
```

### 6. Stream Response

**POST** `/api/langchain/stream`

Stream completions from the LLM (Server-Sent Events).

**Request Body:**
```json
{
  "prompt": "Write a poem about AI"
}
```

**Response:** Server-Sent Events stream
```
data: <chunk1>
data: <chunk2>
data: <chunk3>
...
```

### 7. Get Configuration

**GET** `/api/langchain/config`

Get current LangChain configuration.

**Response:**
```json
{
  "ollama_host": "http://ollama:11434",
  "model": "mistral",
  "embedding_model": "nomic-embed-text",
  "temperature": 0.7,
  "top_k": 40,
  "top_p": 0.9
}
```

## Usage Examples

### Python Client

```python
import requests

# Initialize service in Python
from app.services.langchain_service import get_langchain_service

service = get_langchain_service()

# Simple invocation
response = service.invoke("What is Python?")
print(response)

# Batch invocation
responses = service.batch_invoke([
    "What is Python?",
    "What is JavaScript?"
])
print(responses)

# Get embeddings
embeddings = service.get_embeddings(["Hello", "World"])
print(embeddings)

# Chat with memory
service.create_conversation_chain()
response = service.chat("What is AI?")
print(response)
response = service.chat("Tell me more about it")  # Remembers context
print(response)

# Health check
is_healthy = service.health_check()
print(f"Ollama is {'healthy' if is_healthy else 'unhealthy'}")
```

### cURL Examples

**Health Check:**
```bash
curl http://localhost:5000/api/langchain/health
```

**Invoke LLM:**
```bash
curl -X POST http://localhost:5000/api/langchain/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

**Get Embeddings:**
```bash
curl -X POST http://localhost:5000/api/langchain/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello", "World"]}'
```

**Chat:**
```bash
curl -X POST http://localhost:5000/api/langchain/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is AI?"}'
```

### JavaScript/Node.js

```javascript
// Health check
fetch('/api/langchain/health')
  .then(r => r.json())
  .then(data => console.log(data));

// Invoke LLM
fetch('/api/langchain/invoke', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({prompt: 'What is AI?'})
})
  .then(r => r.json())
  .then(data => console.log(data.response));

// Get embeddings
fetch('/api/langchain/embed', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({texts: ['Hello', 'World']})
})
  .then(r => r.json())
  .then(data => console.log(data.embeddings));
```

## Integration with Existing Code

### In Flask Routes

```python
from app.services.langchain_service import get_langchain_service

@app.route('/my-endpoint', methods=['POST'])
def my_endpoint():
    service = get_langchain_service()
    user_input = request.json.get('input')
    response = service.invoke(user_input)
    return jsonify({'result': response})
```

### In Background Tasks

```python
from app.services.langchain_service import get_langchain_service

def process_text_with_llm(text):
    service = get_langchain_service()
    result = service.invoke(text)
    # Do something with result
    return result
```

### In Docker

The Ollama server should be running on your Docker network. Ensure `OLLAMA_HOST` is correctly set to point to your Ollama container:

```yaml
services:
  app:
    environment:
      - OLLAMA_HOST=http://ollama:11434
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
```

## Troubleshooting

### Connection Errors

If you get "Cannot connect to Ollama server":

1. Verify Ollama is running:
   ```bash
   curl http://OLLAMA_HOST:11434/api/tags
   ```

2. Check environment variable:
   ```bash
   echo $OLLAMA_HOST
   ```

3. Test from Flask app:
   ```bash
   python -c "from app.services.langchain_service import get_langchain_service; print(get_langchain_service().health_check())"
   ```

### Model Not Found

If you get "model not found" errors:

1. List available models:
   ```bash
   curl http://OLLAMA_HOST:11434/api/tags
   ```

2. Pull a model:
   ```bash
   ollama pull mistral
   ollama pull nomic-embed-text
   ```

3. Update environment variables with available model names

### Slow Responses

- Increase timeout in requests if needed
- Ensure sufficient GPU/CPU resources for Ollama
- Check Ollama logs for performance issues

## Architecture

```
┌─────────────────────────────────────┐
│     Flask Application               │
│  ┌─────────────────────────────────┤
│  │ Routes (langchain_routes.py)    │
│  │  ├─ /health                     │
│  │  ├─ /invoke                     │
│  │  ├─ /batch                      │
│  │  ├─ /embed                      │
│  │  ├─ /chat                       │
│  │  └─ /stream                     │
│  └──────────────────┬──────────────┤
│                     │               │
│     ┌───────────────▼───────────┐  │
│     │ LangChainOllamaService    │  │
│     │ (langchain_service.py)    │  │
│     │  ├─ invoke()              │  │
│     │  ├─ batch_invoke()        │  │
│     │  ├─ get_embeddings()      │  │
│     │  ├─ chat()                │  │
│     │  └─ stream_invoke()       │  │
│     └───────────────┬───────────┘  │
└─────────────────────┼──────────────┘
                      │
         ┌────────────▼──────────┐
         │  LangChain Library    │
         │  ├─ Ollama LLM        │
         │  └─ OllamaEmbeddings  │
         └────────────┬──────────┘
                      │
         ┌────────────▼──────────┐
         │   Ollama Server       │
         │  (http://ollama:11434)│
         └───────────────────────┘
```

## Files Created/Modified

- **Created**: `/backend/app/services/langchain_service.py` - LangChain service wrapper
- **Created**: `/backend/app/routes/langchain_routes.py` - Flask API endpoints
- **Modified**: `/backend/app/routes/__init__.py` - Blueprint registration
- **Modified**: `/backend/requirements.txt` - Added LangChain dependencies

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Test health check: `curl http://localhost:5000/api/langchain/health`
3. Ensure Ollama is running with required models
4. Start using the API endpoints
5. Integrate with your application logic as needed

## Support

For issues or questions:
1. Check Ollama logs
2. Verify environment variables
3. Test connectivity to Ollama server
4. Check Flask application logs
