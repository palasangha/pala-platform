# MCP Server UI Integration Guide

**Date**: January 17, 2026  
**MCP Server Version**: 0.1.0  
**Status**: Production Ready

---

## 📡 MCP Server Overview

The MCP (Model Context Protocol) Server is a WebSocket-based orchestration hub that:
- Manages connections from 5 specialized AI agents
- Routes tool invocations between clients and agents
- Provides JSON-RPC 2.0 protocol for bidirectional communication
- Supports JWT-based authentication

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UI/Client Layer                          │
│  (Frontend, REST APIs, or External Clients)                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
          WebSocket (ws://mcp-server:3000)
                     │
┌─────────────────────────────────────────────────────────────┐
│                  MCP Server (Node.js)                       │
│  ├─ Protocol Handler (JSON-RPC 2.0)                        │
│  ├─ Tool Registry                                           │
│  ├─ WebSocket Transport                                    │
│  └─ Authentication (JWT)                                   │
└────────┬────────────────────────────────┬────────────────────┘
         │                                │
    ┌────────────┐              ┌──────────────────┐
    │   Agents   │              │   Tool Registry  │
    ├────────────┤              ├──────────────────┤
    │ Metadata   │              │ metadata tools   │
    │ Entity     │              │ entity tools     │
    │ Structure  │              │ structure tools  │
    │ Content    │              │ context tools    │
    │ Context    │              │ content tools    │
    └────────────┘              └──────────────────┘
```

---

## 🔌 Accessing the MCP Server

### Direct WebSocket Connection

**URL**: `ws://localhost:3001` (or `ws://mcp-server:3000` from Docker network)

**Parameters**:
- `port`: 3001 (external), 3000 (internal)
- `protocol`: WebSocket with JSON-RPC 2.0
- `authentication`: Optional JWT (configurable)

### Using the Backend API

The backend API provides REST endpoints that internally communicate with the MCP server via WebSocket.

**Available Backend Routes** (in `/app/routes/`):
- `/api/system/status` - Service status including MCP server
- `/api/enrichment/*` - Enrichment service routes
- `/api/projects/*` - Project management
- `/api/ocr/*` - OCR processing routes

---

## 📊 Using MCP Server from UI - Implementation Guide

### Option 1: Direct WebSocket Client (JavaScript/TypeScript)

```typescript
// Import or include WebSocket client library
const ws = new WebSocket('ws://localhost:3001');

// Connection handlers
ws.onopen = () => {
  console.log('Connected to MCP Server');
  
  // Register as a client
  const registerMsg = {
    jsonrpc: '2.0',
    id: '1',
    method: 'register_client',
    params: {
      client_type: 'ui',
      client_name: 'enrichment-ui'
    }
  };
  
  ws.send(JSON.stringify(registerMsg));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received from MCP:', message);
  
  if (message.result) {
    // Handle result
    console.log('Result:', message.result);
  }
  
  if (message.error) {
    // Handle error
    console.error('Error:', message.error);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from MCP Server');
};

// Send a request to MCP
function invokeAgent(agentId, toolName, params) {
  const message = {
    jsonrpc: '2.0',
    id: generateUUID(),
    method: 'invoke_tool',
    params: {
      agent_id: agentId,
      tool_name: toolName,
      parameters: params
    }
  };
  
  ws.send(JSON.stringify(message));
}

// Example usage
invokeAgent('metadata-agent', 'classify_document', {
  document_type: 'letter',
  content: 'Dear Sir...'
});
```

### Option 2: REST API Client (Through Backend)

```javascript
// Call backend endpoint that routes to MCP server
async function enrichDocument(documentId, content) {
  try {
    const response = await fetch('/api/enrichment/enrich', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({
        document_id: documentId,
        content: content,
        run_all_agents: true
      })
    });
    
    if (!response.ok) throw new Error('Enrichment failed');
    
    const result = await response.json();
    console.log('Enrichment result:', result);
    return result;
  } catch (error) {
    console.error('Error enriching document:', error);
  }
}

// Usage
enrichDocument('doc123', 'Dear Sir, This is a historical letter...');
```

### Option 3: React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function MCPClientComponent() {
  const [status, setStatus] = useState('disconnected');
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [tools, setTools] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch available agents and tools on mount
    fetchAgentsAndTools();
  }, []);

  const fetchAgentsAndTools = async () => {
    try {
      const response = await fetch('/api/system/status');
      const data = await response.json();
      
      // Extract MCP information
      const mcpStatus = data.status.mcp_server;
      setAgents(mcpStatus.available_agents || []);
      setStatus(mcpStatus.status);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const handleAgentSelect = async (agentId) => {
    setSelectedAgent(agentId);
    
    try {
      const response = await fetch(`/api/mcp/agents/${agentId}/tools`);
      const data = await response.json();
      setTools(data.tools || []);
    } catch (error) {
      console.error('Error fetching tools:', error);
    }
  };

  const handleInvokeTool = async (toolName, toolParams) => {
    setLoading(true);
    
    try {
      const response = await fetch('/api/mcp/invoke', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          agent_id: selectedAgent,
          tool_name: toolName,
          parameters: toolParams
        })
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error invoking tool:', error);
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mcp-client">
      <h2>MCP Server Client</h2>
      
      <div className="status-bar">
        <span className={`status-indicator ${status}`}></span>
        <span>{status}</span>
      </div>

      <div className="agent-selector">
        <h3>Available Agents</h3>
        <select onChange={(e) => handleAgentSelect(e.target.value)}>
          <option value="">Select an agent...</option>
          {agents.map(agent => (
            <option key={agent.id} value={agent.id}>
              {agent.name} - {agent.status}
            </option>
          ))}
        </select>
      </div>

      {selectedAgent && (
        <div className="tools-panel">
          <h3>Available Tools</h3>
          <div className="tools-list">
            {tools.map(tool => (
              <div key={tool.id} className="tool-card">
                <h4>{tool.name}</h4>
                <p>{tool.description}</p>
                <button 
                  onClick={() => handleInvokeTool(tool.name, {})}
                  disabled={loading}
                >
                  Invoke
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="result-panel">
          <h3>Result</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default MCPClientComponent;
```

---

## 🛠️ Available Agents and Tools

### 1. Metadata Agent
**Agent ID**: `metadata-agent`
**Purpose**: Extract document metadata and classification

**Available Tools**:
```
├─ document_classifier
│  └─ Determines document type (letter, form, etc.)
├─ storage_extractor
│  └─ Extracts storage location and format info
└─ access_determiner
   └─ Determines access restrictions
```

**Example Invocation**:
```json
{
  "method": "invoke_tool",
  "params": {
    "agent_id": "metadata-agent",
    "tool_name": "document_classifier",
    "parameters": {
      "document_content": "Dear Sir or Madam...",
      "document_format": "pdf"
    }
  }
}
```

### 2. Entity Agent
**Agent ID**: `entity-agent`
**Purpose**: Extract people, organizations, locations, events

**Available Tools**:
- `person_extractor` - Extract people and roles
- `organization_extractor` - Extract organizations
- `location_extractor` - Extract locations
- `event_extractor` - Extract historical events

### 3. Structure Agent
**Agent ID**: `structure-agent`
**Purpose**: Analyze document structure and components

**Available Tools**:
- `salutation_analyzer` - Extract greeting/salutation
- `body_analyzer` - Extract main content
- `closing_analyzer` - Extract closing/signature
- `signature_detector` - Identify signatures

### 4. Content Agent
**Agent ID**: `content-agent`
**Purpose**: Generate summaries and extract key information (uses Claude Sonnet)

**Available Tools**:
- `summarizer` - Create document summary
- `keyword_extractor` - Extract key terms
- `subject_classifier` - Classify subject matter

### 5. Context Agent
**Agent ID**: `context-agent`
**Purpose**: Add historical context (uses Claude Opus)

**Available Tools**:
- `context_generator` - Generate historical context
- `significance_analyzer` - Analyze historical significance
- `date_contextualizer` - Add temporal context

---

## 📝 JSON-RPC Message Format

### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "invoke_tool|register_client|list_agents|list_tools",
  "params": {
    "agent_id": "agent-name",
    "tool_name": "tool-name",
    "parameters": { /* tool parameters */ }
  }
}
```

### Response Format (Success)
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "status": "success",
    "data": { /* tool result */ },
    "execution_time_ms": 250
  }
}
```

### Response Format (Error)
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": "Additional error details"
  }
}
```

---

## 🔐 Authentication

### Optional JWT Authentication

If `MCP_JWT_SECRET` is set, include JWT token:

```javascript
const token = generateJWT({
  aud: 'mcp-server',
  client_id: 'enrichment-ui'
});

const ws = new WebSocket(`ws://localhost:3001?token=${encodeURIComponent(token)}`);
```

### Without Authentication (Development)

Just connect directly:
```javascript
const ws = new WebSocket('ws://localhost:3001');
```

---

## 🎯 Real-World Example: Document Enrichment Workflow

```javascript
class DocumentEnricher {
  constructor() {
    this.mcp = new MCPClient('ws://localhost:3001');
  }

  async enrichDocument(document) {
    console.log('Starting enrichment for:', document.id);

    // Step 1: Classify document (Metadata Agent)
    const metadata = await this.mcp.invoke('metadata-agent', 'document_classifier', {
      document_content: document.content,
      document_format: document.format
    });
    console.log('Metadata:', metadata);

    // Step 2: Extract entities (Entity Agent)
    const entities = await this.mcp.invoke('entity-agent', 'person_extractor', {
      document_content: document.content
    });
    console.log('Entities:', entities);

    // Step 3: Analyze structure (Structure Agent)
    const structure = await this.mcp.invoke('structure-agent', 'body_analyzer', {
      document_content: document.content
    });
    console.log('Structure:', structure);

    // Step 4: Generate summary (Content Agent)
    const summary = await this.mcp.invoke('content-agent', 'summarizer', {
      document_content: document.content,
      metadata: metadata
    });
    console.log('Summary:', summary);

    // Step 5: Add context (Context Agent)
    const context = await this.mcp.invoke('context-agent', 'context_generator', {
      document_content: document.content,
      entities: entities,
      metadata: metadata
    });
    console.log('Context:', context);

    // Combine results
    return {
      document_id: document.id,
      metadata,
      entities,
      structure,
      summary,
      context,
      enriched_at: new Date().toISOString()
    };
  }
}

// Usage
const enricher = new DocumentEnricher();
const result = await enricher.enrichDocument({
  id: 'doc123',
  content: 'Dear Sir, This is a historical letter from 1950...',
  format: 'text'
});

console.log('Final enriched document:', result);
```

---

## 🔌 Integration with Existing APIs

### Backend Route to MCP

```python
from flask import Blueprint, request, jsonify
from app.services.mcp_client import MCPClient

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')
mcp_client = MCPClient('ws://mcp-server:3000')

@mcp_bp.route('/invoke', methods=['POST'])
def invoke_agent_tool():
    """Invoke a tool on an agent"""
    data = request.json
    
    try:
        result = mcp_client.invoke(
            agent_id=data.get('agent_id'),
            tool_name=data.get('tool_name'),
            parameters=data.get('parameters', {})
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mcp_bp.route('/agents', methods=['GET'])
def list_agents():
    """List available agents"""
    agents = mcp_client.list_agents()
    
    return jsonify({
        'success': True,
        'agents': agents
    })

@mcp_bp.route('/agents/<agent_id>/tools', methods=['GET'])
def list_agent_tools(agent_id):
    """List tools for a specific agent"""
    tools = mcp_client.get_agent_tools(agent_id)
    
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'tools': tools
    })
```

---

## 📊 Monitoring & Debugging

### Check MCP Server Status

```bash
# Direct connection test
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:3001/health

# Check via system API
curl http://localhost:5000/api/system/status | jq '.status.mcp_server'

# View server logs
docker-compose logs -f mcp-server

# View agent logs
docker-compose logs -f metadata-agent
```

### Debug WebSocket Connection

```javascript
// Enable detailed logging
const ws = new WebSocket('ws://localhost:3001');

ws.addEventListener('open', (event) => {
  console.log('WebSocket opened:', event);
});

ws.addEventListener('message', (event) => {
  console.log('Received message:', event.data);
});

ws.addEventListener('error', (event) => {
  console.error('WebSocket error:', event);
});

ws.addEventListener('close', (event) => {
  console.log('WebSocket closed:', event);
});
```

---

## ⚡ Performance Tips

1. **Connection Pooling**: Reuse WebSocket connection
2. **Batch Requests**: Group multiple tool invocations
3. **Timeout Handling**: Set request timeouts for client calls
4. **Caching**: Cache agent tool lists and responses
5. **Error Handling**: Implement retry logic with exponential backoff

---

## 🚀 Production Deployment

### Environment Variables

```bash
# MCP Server configuration
MCP_SERVER_URL=ws://mcp-server:3000        # Internal
MCP_JWT_SECRET=your-secret-key             # Optional
MCP_LOG_LEVEL=info                         # debug|info|warn|error
MCP_AUTH_ENABLED=true                      # Enable JWT auth

# Client configuration
MCP_CLIENT_TIMEOUT=30000                   # Timeout in ms
MCP_CLIENT_RETRY_COUNT=3                   # Retry attempts
MCP_CLIENT_RETRY_DELAY=1000                # Retry delay in ms
```

### Docker Environment

```yaml
environment:
  - MCP_SERVER_URL=ws://mcp-server:3000
  - MCP_JWT_SECRET=${MCP_JWT_SECRET}
  - MCP_LOG_LEVEL=info
  - MCP_AUTH_ENABLED=true
```

---

## 📚 Additional Resources

- **MCP Server Source**: `/packages/mcp-server/src/`
- **Agent Implementations**: `/packages/agents/*/`
- **Backend Routes**: `/backend/app/routes/`
- **Frontend Components**: `/frontend/src/components/`

---

## Summary

The MCP Server provides:
✅ WebSocket-based agent communication  
✅ JSON-RPC 2.0 protocol  
✅ Optional JWT authentication  
✅ 5 specialized AI agents  
✅ Extensible tool registry  
✅ Full REST API integration  

**Access from UI**: Via WebSocket client library or REST API endpoints  
**Status**: Production-ready and fully operational  
**Next Steps**: Implement enrichment services using MCP agents

---

**Document Version**: 1.0  
**Last Updated**: January 17, 2026  
**Status**: Complete & Ready to Use
