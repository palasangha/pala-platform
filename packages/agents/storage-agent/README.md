# Storage Agent

MCP agent that exposes document storage operations with automatic deduplication.

## Tools

- `store_document` - Store content with SHA-256 deduplication
- `retrieve_document` - Retrieve by content ID
- `list_documents` - List stored documents
- `list_backends` - List available storage backends
- `get_stats` - Get storage statistics

## Usage

```bash
export MCP_SERVER_URL="ws://localhost:3000"
export MCP_AGENT_ID="storage-agent"
python main.py
```

## Storage Backend

Uses the `packages/storage` backend with:
- SHA-256 content deduplication
- Multiple backend support (local, S3, GCS, Azure)
- Version control
- Metadata storage in SQLite
