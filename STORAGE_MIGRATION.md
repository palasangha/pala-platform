# Storage Architecture Migration

## Overview
The storage layer has been migrated from a Flask HTTP server architecture to an MCP agent architecture for consistency with the rest of the platform.

## Changes Made

### 1. New Storage Agent
**Created:** `packages/agents/storage-agent/`
- `main.py` - Complete MCP agent implementation
- `requirements.txt` - Dependencies (websockets>=12.0)
- `README.md` - Documentation

**Tools Exposed:**
- `store_document` - Store documents with SHA-256 deduplication
- `retrieve_document` - Retrieve documents by content_id
- `list_documents` - List documents with filtering and pagination
- `list_backends` - List available storage backends
- `get_stats` - Get storage statistics

### 2. Frontend Updates
**Updated:** `apps/web/components/Dashboard.tsx`
- Changed `loadAvailableBackends()` from HTTP fetch to MCP WebSocket
- Changed `handleStore()` from HTTP fetch to MCP WebSocket
- Added WebSocket connection checks before invoking storage tools

**Updated:** `apps/web/components/DocumentBrowser.tsx`
- Changed `loadDocuments()` from HTTP fetch to MCP WebSocket
- Changed `loadStats()` from HTTP fetch to MCP WebSocket
- Changed `viewDocument()` from HTTP fetch to MCP WebSocket
- Added WebSocket connection checks for all storage operations

**Already Fixed:** `apps/web/hooks/useWebSocket.ts`
- Memoized `send` function to prevent infinite re-renders

### 3. Startup Script
**Updated:** `start-dev.sh`
- Added storage-agent startup section (step 4/5)
- Added storage-agent logs to the output
- Updated service count from 4 to 5

## Files to Remove (Old Architecture)

### Flask HTTP Server
These files are no longer needed as storage is now an MCP agent:
- `packages/storage/api/flask_server.py` - Flask HTTP server on port 5001
- Any Flask-specific configuration files

### Frontend HTTP Proxy Routes
These Next.js API routes are no longer needed as frontend calls storage via WebSocket:
- `apps/web/app/api/storage/backends/route.ts`
- `apps/web/app/api/storage/store/route.ts`
- `apps/web/app/api/storage/list/route.ts`
- `apps/web/app/api/storage/retrieve/[id]/route.ts`
- `apps/web/app/api/storage/stats/route.ts`
- `apps/web/app/api/storage/sign/route.ts`

**Note:** The entire `apps/web/app/api/storage/` directory can be removed.

## Architecture Benefits

### Before (HTTP)
```
Frontend (Next.js on :3001)
  ↓ HTTP fetch
Next.js API Routes (/api/storage/*)
  ↓ HTTP fetch
Flask Server (:5001)
  ↓ Python imports
Storage Package (packages/storage)
```

### After (MCP Agent)
```
Frontend (Next.js on :3001)
  ↓ WebSocket (MCP)
MCP Server (:3000)
  ↓ Tool invocation
Storage Agent (packages/agents/storage-agent)
  ↓ Python imports
Storage Package (packages/storage)
```

### Improvements
1. **Consistency** - All backend operations now use MCP tools (metadata extraction, storage, etc.)
2. **Simplicity** - No HTTP server management, no port conflicts, no API route proxying
3. **WebSocket Benefits** - Single persistent connection, bidirectional communication, lower latency
4. **Deduplication Maintained** - SHA-256 deduplication still works through agent tools
5. **Single Transport** - Frontend only needs WebSocket connection, not HTTP + WebSocket

## Storage Backend Preserved

The core storage implementation in `packages/storage/` remains unchanged:
- `api/storage_api.py` - StorageAPI class with deduplication
- `backends/` - Local, SQLite, S3, GCS, Azure backends
- All SHA-256 deduplication logic intact

The storage-agent simply wraps this existing package and exposes it via MCP tools.

## Testing Steps

1. **Start all services:**
   ```bash
   ./start-dev.sh
   ```

2. **Verify storage-agent connects:**
   ```bash
   tail -f logs/storage-agent.log
   # Should see: "Storage Agent connected to MCP server"
   ```

3. **Upload a document:**
   - Go to http://localhost:3001
   - Upload an image
   - Run OCR extraction
   - Extract metadata
   - Click "Store Document"
   - Should see success message

4. **Test deduplication:**
   - Upload the same file again
   - Go through OCR and metadata steps
   - Click "Store Document"
   - Should see: "⚠️ Duplicate document detected and not re-stored"

5. **Browse documents:**
   - Click "Document Browser" tab
   - Should see stored documents listed
   - Click a document to view details
   - Should see OCR text and metadata

## Rollback (if needed)

If issues arise, rollback by:
1. Revert changes to `Dashboard.tsx`, `DocumentBrowser.tsx`, `start-dev.sh`
2. Start Flask server: `cd packages/storage/api && python flask_server.py`
3. Frontend will fall back to HTTP API routes

## Next Steps

After confirming everything works:
1. Remove old Flask server files
2. Remove old API route files
3. Update documentation to reflect MCP-only architecture
4. Remove HTTP-related environment variables if any
