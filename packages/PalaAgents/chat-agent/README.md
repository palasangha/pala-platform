# Chat Agent

Orchestrates document search and response generation for the Pala Platform RAG (Retrieval-Augmented Generation) system.

## Features

- **Semantic Search**: Calls storage-agent to search documents using embeddings
- **Cited Responses**: Generates responses with [doc-ID] citations
- **Fallback Search**: Gracefully degrades to keyword search if embeddings unavailable
- **Ollama Integration**: Generates conversational responses using local LLM

## Tool: `chat_with_documents`

Complete chat experience - searches documents and generates cited response.

### Parameters

- `query` (string, required): User's question or prompt
- `search_limit` (number, optional): Max documents to retrieve (default: 5)
- `min_confidence` (number, optional): Minimum relevance score 0-1 (default: 0.5)
- `include_file_content` (boolean, optional): Include original file data (default: false)

### Response Format

```json
{
  "success": true,
  "answer": "Based on the documents...",
  "source_documents": [
    {
      "document_id": "doc-123",
      "filename": "file.pdf",
      "relevance_score": 0.95,
      "summary": "...",
      "excerpt": "..."
    }
  ],
  "search_query": "user query",
  "search_method": "semantic",
  "embedding_used": true,
  "num_documents": 2,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
export MCP_SERVER_URL="ws://localhost:3000"
export MCP_AGENT_ID="chat-agent"
export MCP_AGENT_TOKEN="your-token"

python main.py
```

## Architecture

The chat-agent follows this flow:

1. **Receives Query**: User asks a question
2. **Searches Documents**: Calls `storage-agent.semantic_search_documents()`
3. **Formats Context**: Prepares retrieved documents for LLM
4. **Generates Response**: Calls Ollama with documents + system prompt
5. **Cites Sources**: Returns response with [doc-ID] citations
6. **Returns Result**: Full result with source documents and metadata

## Integration

The chat-agent is consumed by:
- **PalaWebDashboard**: Chat tab calls this agent's `chat_with_documents` tool
- **API Gateway**: Could expose this as REST endpoint
- **Other Agents**: Can call this for document-aware responses

## Logging

All operations are logged to `logs/chat-agent.log` with tags:

- `[CHAT-AGENT]`: General agent operations
- `[CHAT-AGENT-TOOL]`: Tool invocation and execution
- `[CHAT-AGENT-STARTUP]`: Startup/initialization
- `[ORCHESTRATION]`: Cross-agent communication

## Debugging

To see detailed debug logs:

```bash
grep "\[CHAT-AGENT\]" logs/chat-agent.log
grep "\[ERROR\]" logs/chat-agent.log
```

## Future Enhancements

- [ ] Implement real Ollama integration (currently using template responses)
- [ ] Add conversation history tracking
- [ ] Implement response streaming
- [ ] Add user feedback scoring for relevance
- [ ] Cache frequently asked questions
- [ ] Multi-language support
- [ ] Document summarization before LLM
- [ ] Real-time document processing tracking
