# Storage Agent

MCP agent that exposes document storage operations with automatic deduplication.

## Tools

- `store_document` - Store content with SHA-256 deduplication
- `retrieve_document` - Retrieve by content ID
- `list_documents` - List stored documents
- `list_backends` - List available storage backends
- `list_storage_providers` - List provider catalog and enabled status
- `get_stats` - Get storage statistics
- `answer_content_query` - Grounded Q&A over stored content with citations
- `delete_all_documents` - Delete all stored content and metadata

## Usage

```bash
export MCP_SERVER_URL="ws://localhost:3010"
export MCP_AGENT_ID="storage-agent"
python main.py
```

## Storage Architecture

The storage-agent is now self-contained and provider-centric.

- `metadata_db.py` manages cross-provider metadata and deduplication in SQLite.
- `providers/` contains backend-specific provider implementations.
- `providers/registry.py` maps provider IDs to backend names and enablement.

Current provider status:

- `local-provider`: enabled (default)
- `sqlite-provider`: enabled
- `s3-provider`, `gcs-provider`, `azure-provider`: scaffolded (disabled)
