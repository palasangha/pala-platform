# Metadata Writer Tool - Quick Start Guide

## What It Does

The Metadata Writer Tool allows you to write enriched metadata to JSON files alongside your original documents. It's now part of the context-agent and available through the MCP server.

## Quick Usage

### 1. Write Metadata to File

```python
from enrichment_service.mcp_client.client import MCPClient

mcp_client = MCPClient()

result = await mcp_client.invoke_tool(
    "write_metadata",
    {
        "file_path": "/data/letters/letter001.jpg",
        "metadata": {
            "document_type": "Letter",
            "sender": "S.N. Goenka",
            "recipient": "Student",
            "date": "1990-05-15",
            "subjects": ["Buddhism", "Vipassana", "Meditation"],
            "summary": "A letter discussing meditation practices.",
            "historical_context": "Written during Vipassana expansion."
        }
    }
)

print(f"Metadata written to: {result['output_path']}")
```

**Output:** `/data/letters/letter001_metadata.json`

### 2. Update Existing Metadata

```python
result = await mcp_client.invoke_tool(
    "update_metadata",
    {
        "metadata_file_path": "/data/letters/letter001_metadata.json",
        "updates": {
            "reviewed_by": "Admin User",
            "quality_score": 95
        },
        "merge": True  # Merge with existing data
    }
)
```

### 3. Read Metadata

```python
result = await mcp_client.invoke_tool(
    "read_metadata",
    {
        "metadata_file_path": "/data/letters/letter001_metadata.json"
    }
)

metadata = result['metadata']
print(f"Document type: {metadata['document_type']}")
print(f"Sender: {metadata['sender']}")
```

## Integration with Enrichment Pipeline

Add this to your enrichment workflow:

```python
# In enrichment_worker.py or agent_orchestrator.py

async def enrich_and_write_metadata(document_id, ocr_data):
    # 1. Enrich the document
    enriched_data = await orchestrator.enrich_document(
        document_id=document_id,
        ocr_data=ocr_data
    )

    # 2. Write metadata to file
    result = await mcp_client.invoke_tool(
        "write_metadata",
        {
            "file_path": ocr_data['file_path'],
            "metadata": enriched_data
        }
    )

    if result['success']:
        logger.info(f"✓ Metadata written: {result['output_path']}")
    else:
        logger.error(f"✗ Failed to write metadata: {result['error']}")

    return enriched_data
```

## Use with AMI Parser

Parse filename and write metadata in one go:

```python
# Parse AMI filename
parsed = await mcp_client.invoke_tool(
    "parse_ami_filename",
    {"filename": "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"}
)

if parsed['parsed']:
    # Write the parsed metadata
    result = await mcp_client.invoke_tool(
        "write_metadata",
        {
            "file_path": f"/data/letters/{parsed['filename']}",
            "metadata": {
                **parsed,
                "archipelago_fields": parsed['archipelago_fields']
            }
        }
    )
```

## Configuration

Set the base path for metadata files:

```yaml
# docker-compose.yml
services:
  context-agent:
    environment:
      - METADATA_BASE_PATH=/data/enriched_metadata
```

## File Structure

Metadata files are created alongside originals:

```
/data/letters/
├── letter001.jpg                  # Original file
├── letter001_metadata.json        # Generated metadata
├── letter002.jpg
├── letter002_metadata.json
```

## Metadata Format

```json
{
  "document_type": "Letter",
  "sender": "S.N. Goenka",
  "recipient": "Student",
  "date": "1990-05-15",
  "subjects": ["Buddhism", "Vipassana"],
  "summary": "A letter discussing meditation...",
  "historical_context": "Written during...",

  "_metadata_written_at": "2026-01-29T09:58:19.385403",
  "_original_file": "/data/letters/letter001.jpg",
  "_metadata_file": "/data/letters/letter001_metadata.json"
}
```

## Testing

Run the test suite:

```bash
cd packages/agents/context-agent
python3 test_metadata_writer.py
```

Expected output:
```
✓ PASS: write
✓ PASS: read
✓ PASS: update
✓ PASS: batch
✓ PASS: ami_integration

Total: 5/5 tests passed
🎉 All tests passed!
```

## Available Tools

The context-agent now provides 7 MCP tools:

1. ✅ `research_historical_context` - Generate historical context
2. ✅ `assess_significance` - Assess historical significance
3. ✅ `generate_biographies` - Create biographies
4. ✅ `parse_ami_filename` - Parse AMI filenames
5. ✅ **`write_metadata`** - Write metadata to file (NEW)
6. ✅ **`update_metadata`** - Update existing metadata (NEW)
7. ✅ **`read_metadata`** - Read metadata from file (NEW)

## Error Handling

```python
result = await mcp_client.invoke_tool("write_metadata", {...})

if not result['success']:
    logger.error(f"Failed to write metadata: {result['error']}")
    # Handle error (retry, skip, alert, etc.)
```

## Common Issues

### Permission Denied
```bash
chmod -R 755 /data/letters/
```

### File Not Found
```python
from pathlib import Path
if Path(file_path).exists():
    # Write metadata
```

### Invalid JSON
```python
import json
try:
    json.dumps(metadata)  # Validate before writing
except TypeError:
    # Handle non-serializable data
```

## Next Steps

1. ✅ Tools are implemented and tested
2. ✅ Tools are registered with MCP server
3. 🔄 Integrate into enrichment pipeline
4. 🔄 Add to Archipelago export workflow
5. 🔄 Create searchability index from metadata files

## Full Documentation

For detailed documentation, see:
- [METADATA_WRITER_DOCUMENTATION.md](./METADATA_WRITER_DOCUMENTATION.md)
- [AMI_METADATA_PARSER_DOCUMENTATION.md](./AMI_METADATA_PARSER_DOCUMENTATION.md)

## Support

Check tool status:
```python
from main import ContextAgent
agent = ContextAgent()
tools = agent.get_tool_definitions()
print(f"Registered {len(tools)} tools")
```

Should output:
```
Registered 7 tools
```
