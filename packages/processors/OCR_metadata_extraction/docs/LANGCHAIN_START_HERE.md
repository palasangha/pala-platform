# LangChain Ollama Integration - Start Here 🚀

## What Was Just Set Up?

Your GVPOCR project now has **complete LangChain integration** with your Ollama server! This enables:

- 🤖 LLM-powered document analysis
- 🔍 Semantic search with embeddings
- 💬 Conversational AI with memory
- ⚡ Streaming real-time responses
- 📦 Batch processing capabilities

## 📋 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Ollama (if not already running)
```bash
ollama serve
# or with Docker:
docker run -d -p 11434:11434 ollama/ollama
```

### 3. Pull Models
```bash
ollama pull mistral           # LLM for text generation
ollama pull nomic-embed-text  # Embedding model
```

### 4. Start Your Flask App
```bash
python backend/run.py
```

### 5. Test It
```bash
curl http://localhost:5000/api/langchain/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model": "mistral",
  "host": "http://ollama:11434"
}
```

## 📚 Documentation Structure

Read these in order based on your needs:

### 🏃 For Quick Integration (15 mins)
→ **LANGCHAIN_QUICK_REFERENCE.md**
- Install & test commands
- API endpoints
- Code snippets

### 🏗️ For Full Understanding (30 mins)
→ **LANGCHAIN_OLLAMA_SETUP.md**
- Complete API documentation
- Configuration options
- Architecture diagram
- Troubleshooting guide

### 💡 For Code Examples (20 mins)
→ **LANGCHAIN_INTEGRATION_EXAMPLES.py**
- Real-world use cases
- Flask route examples
- Integration patterns
- Error handling

### 📊 For Overview (5 mins)
→ **LANGCHAIN_SETUP_SUMMARY.md**
- What was added
- Features enabled
- Next steps

## 🎯 Available API Endpoints

All endpoints are under `/api/langchain/`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Check Ollama status |
| POST | `/invoke` | Single LLM completion |
| POST | `/batch` | Multiple completions |
| POST | `/embed` | Get text embeddings |
| POST | `/chat` | Chat with memory |
| POST | `/stream` | Streaming responses |
| GET | `/config` | View configuration |

## 🐍 Python Usage (In Your Routes)

```python
from app.services.langchain_service import get_langchain_service

# Get the service
service = get_langchain_service()

# Single completion
response = service.invoke("What is machine learning?")

# Multiple completions
responses = service.batch_invoke(["Q1?", "Q2?"])

# Embeddings for search
embeddings = service.get_embeddings(["doc1", "doc2"])

# Chat with context
service.create_conversation_chain()
answer1 = service.chat("What is AI?")
answer2 = service.chat("Tell me more")  # Remembers context
```

## 🌐 REST API Usage (From Frontend)

```javascript
// Health check
const health = await fetch('/api/langchain/health').then(r => r.json());

// Get completion
const result = await fetch('/api/langchain/invoke', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({prompt: 'What is AI?'})
}).then(r => r.json());

console.log(result.response);
```

## 🚀 Common Use Cases

### 1. Document Analysis
```python
# Analyze OCR results with LLM
ocr_text = "... extracted text ..."
analysis = service.invoke(f"Summarize: {ocr_text}")
```

### 2. Semantic Search
```python
# Find similar documents
query_embedding = service.get_embedding(search_query)
doc_embeddings = service.get_embeddings(documents)
# Calculate similarity and rank results
```

### 3. Batch Processing
```python
# Process multiple documents in parallel
prompts = [f"Analyze: {doc}" for doc in documents]
results = service.batch_invoke(prompts)
```

### 4. Interactive Q&A
```python
# User asks questions about a document
service.create_conversation_chain()
answer = service.chat("What is in this document?")
followup = service.chat("Tell me more about X")  # Remembers context
```

## 🔧 Configuration

Edit `.env` if you want custom settings:

```bash
# Ollama server location
OLLAMA_HOST=http://ollama:11434

# LLM model (mistral, neural-chat, dolphin-mixtral, llama2)
OLLAMA_MODEL=mistral

# Embedding model (nomic-embed-text, all-minilm)
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## 📁 Files Added/Modified

### New Files:
- ✅ `backend/app/services/langchain_service.py` - Core service
- ✅ `backend/app/routes/langchain_routes.py` - API endpoints
- ✅ `LANGCHAIN_OLLAMA_SETUP.md` - Full documentation
- ✅ `LANGCHAIN_QUICK_REFERENCE.md` - Quick ref
- ✅ `LANGCHAIN_SETUP_SUMMARY.md` - Overview
- ✅ `LANGCHAIN_INTEGRATION_EXAMPLES.py` - Code examples
- ✅ `LANGCHAIN_START_HERE.md` - This file

### Modified Files:
- ✅ `backend/requirements.txt` - Added dependencies
- ✅ `backend/app/routes/__init__.py` - Registered blueprint

## ⚡ Performance Tips

1. **Model Selection**: `mistral` is fast and good quality
2. **Batch Operations**: Process multiple items at once
3. **Caching**: Embeddings can be cached for reuse
4. **Streaming**: Use `/stream` for large responses
5. **GPU**: Ollama uses GPU if available for faster inference

## 🐛 Troubleshooting

### "Cannot connect to Ollama"
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check OLLAMA_HOST in .env
echo $OLLAMA_HOST
```

### "Model not found"
```bash
# List available models
ollama list

# Pull missing model
ollama pull mistral
```

### ImportError
```bash
# Reinstall dependencies
pip install -r backend/requirements.txt --force-reinstall
```

See **LANGCHAIN_OLLAMA_SETUP.md** for more troubleshooting.

## 🎓 Next Steps

1. ✅ **Install & test** - Follow "Quick Start" above
2. 📖 **Read documentation** - Pick relevant doc based on needs
3. 💻 **Try examples** - Run code from LANGCHAIN_INTEGRATION_EXAMPLES.py
4. 🔌 **Integrate** - Add LangChain to your routes/workflows
5. 🧪 **Test thoroughly** - Test with real data
6. 📊 **Monitor** - Check Flask logs for issues

## 🆘 Need Help?

1. Check relevant documentation file
2. Review code examples in LANGCHAIN_INTEGRATION_EXAMPLES.py
3. Check Flask application logs
4. Verify Ollama logs: `ollama logs`
5. Test basic connectivity: `curl http://OLLAMA_HOST:11434/api/tags`

## 📞 Support Resources

| Need | File |
|------|------|
| Quick commands | LANGCHAIN_QUICK_REFERENCE.md |
| Full API docs | LANGCHAIN_OLLAMA_SETUP.md |
| Code examples | LANGCHAIN_INTEGRATION_EXAMPLES.py |
| Setup overview | LANGCHAIN_SETUP_SUMMARY.md |
| Getting started | LANGCHAIN_START_HERE.md (this file) |

---

**Status**: ✅ Setup Complete and Ready to Use

**Next**: Install dependencies and test the API!

```bash
# Copy-paste quick start:
cd backend && pip install -r requirements.txt
python -c "from app.services.langchain_service import get_langchain_service; print('✅ Import successful!')"
```
