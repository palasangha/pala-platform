# Metadata Writer Tool Documentation

## Overview

The Metadata Writer Tool is an MCP tool that enables writing, reading, and updating enriched metadata to JSON files alongside original documents. It's part of the context-agent and integrates seamlessly with the OCR metadata extraction and enrichment pipeline.

## Features

1. **Write Metadata**: Create new metadata JSON files alongside original documents
2. **Read Metadata**: Read existing metadata from JSON files
3. **Update Metadata**: Merge or replace metadata in existing files
4. **Batch Operations**: Write metadata for multiple files at once
5. **AMI Integration**: Works seamlessly with AMI filename parser

## MCP Tools

### 1. `write_metadata`

Write enriched metadata to a JSON file alongside the original document.

**Parameters:**
- `file_path` (string, required): Path to the original document file
- `metadata` (object, required): Metadata dictionary to write
- `output_filename` (string, optional): Custom output filename (defaults to `{original}_metadata.json`)

**Returns:**
```json
{
  "success": true,
  "output_path": "/data/documents/letter001_metadata.json",
  "original_file": "/data/documents/letter001.jpg",
  "bytes_written": 1234,
  "metadata_keys": ["document_type", "sender", "recipient", ...]
}
```

**Example Usage:**
```python
result = await mcp_client.invoke_tool(
    "write_metadata",
    {
        "file_path": "/data/letters/sample_letter.jpg",
        "metadata": {
            "document_type": "Letter",
            "sender": "S.N. Goenka",
            "recipient": "Student",
            "date": "1990-05-15",
            "subjects": ["Buddhism", "Vipassana"],
            "summary": "A letter discussing meditation practices.",
            "historical_context": "Written during Vipassana expansion..."
        }
    }
)
```

### 2. `update_metadata`

Update an existing metadata JSON file by merging new fields or replacing entirely.

**Parameters:**
- `metadata_file_path` (string, required): Path to the existing metadata JSON file
- `updates` (object, required): Dictionary of fields to update or add
- `merge` (boolean, optional): If true, merge with existing data; if false, replace entirely (default: true)

**Returns:**
```json
{
  "success": true,
  "metadata_path": "/data/documents/letter001_metadata.json",
  "updated_fields": ["reviewed_by", "quality_score"],
  "merge_mode": true
}
```

**Example Usage:**
```python
result = await mcp_client.invoke_tool(
    "update_metadata",
    {
        "metadata_file_path": "/data/letters/sample_letter_metadata.json",
        "updates": {
            "reviewed_by": "Admin User",
            "review_date": "2025-01-15",
            "quality_score": 95
        },
        "merge": True
    }
)
```

### 3. `read_metadata`

Read metadata from an existing JSON file.

**Parameters:**
- `metadata_file_path` (string, required): Path to the metadata JSON file to read

**Returns:**
```json
{
  "success": true,
  "metadata": {
    "document_type": "Letter",
    "sender": "S.N. Goenka",
    ...
  },
  "metadata_path": "/data/documents/letter001_metadata.json"
}
```

**Example Usage:**
```python
result = await mcp_client.invoke_tool(
    "read_metadata",
    {
        "metadata_file_path": "/data/letters/sample_letter_metadata.json"
    }
)
```

## Metadata Structure

The tool automatically adds tracking fields to all metadata:

```json
{
  "document_type": "Letter",
  "sender": "S.N. Goenka",
  "recipient": "Student",
  "date": "1990-05-15",
  "subjects": ["Buddhism", "Vipassana", "Meditation"],
  "summary": "A letter discussing meditation practices...",
  "historical_context": "Written during the period of...",

  "_metadata_written_at": "2026-01-29T09:58:19.385403",
  "_original_file": "/data/letters/sample_letter.jpg",
  "_metadata_file": "/data/letters/sample_letter_metadata.json",
  "_metadata_updated_at": "2026-01-29T10:15:22.123456"
}
```

## Integration Examples

### With OCR Pipeline

```python
# After OCR and enrichment
enriched_data = await orchestrator.enrich_document(
    document_id=doc_id,
    ocr_data=ocr_data
)

# Write metadata to file
result = await mcp_client.invoke_tool(
    "write_metadata",
    {
        "file_path": f"/data/documents/{filename}",
        "metadata": enriched_data
    }
)
```

### With AMI Parser

```python
# Parse AMI filename
parsed = await mcp_client.invoke_tool(
    "parse_ami_filename",
    {"filename": "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"}
)

# Add enrichment
enriched_metadata = {**parsed, **enrichment_results}

# Write to file
result = await mcp_client.invoke_tool(
    "write_metadata",
    {
        "file_path": f"/data/letters/{parsed['filename']}",
        "metadata": enriched_metadata
    }
)
```

### Batch Operations

For batch operations, use the Python class directly:

```python
from tools.metadata_writer import MetadataWriter

writer = MetadataWriter(base_path='/data')

batch = [
    {
        'file_path': '/data/letters/letter1.jpg',
        'metadata': enriched_data_1
    },
    {
        'file_path': '/data/letters/letter2.jpg',
        'metadata': enriched_data_2
    }
]

result = writer.write_batch_metadata(batch)
print(f"Wrote {result['successful']}/{result['total']} files")
```

## Configuration

The tool uses the following environment variables:

- `METADATA_BASE_PATH`: Base directory for metadata files (default: `/data`)

Set in your environment or docker-compose:

```yaml
environment:
  - METADATA_BASE_PATH=/data/enriched_metadata
```

## File Organization

By default, metadata files are created in the same directory as the original file:

```
/data/letters/
├── letter001.jpg
├── letter001_metadata.json
├── letter002.jpg
├── letter002_metadata.json
└── ...
```

You can customize the output filename using the `output_filename` parameter:

```python
result = await mcp_client.invoke_tool(
    "write_metadata",
    {
        "file_path": "/data/letters/letter001.jpg",
        "metadata": {...},
        "output_filename": "letter001_enriched.json"  # Custom name
    }
)
```

## Error Handling

All tools return a result dictionary with a `success` field:

```python
result = await mcp_client.invoke_tool("write_metadata", {...})

if result['success']:
    print(f"Metadata written to {result['output_path']}")
else:
    print(f"Error: {result['error']}")
```

Common errors:
- File path not found
- Permission denied
- Invalid JSON in existing metadata
- Disk space issues

## Testing

Run the test suite:

```bash
cd agents/context-agent
python3 test_metadata_writer.py
```

Tests cover:
1. Write metadata to file
2. Read metadata from file
3. Update existing metadata
4. Batch write operations
5. AMI parser integration

## Best Practices

1. **Always validate metadata** before writing to ensure schema compliance
2. **Use merge mode** when updating to preserve existing fields
3. **Include tracking fields** like `reviewed_by`, `review_date`, `quality_score`
4. **Handle errors gracefully** and log failures for debugging
5. **Use batch operations** for bulk processing to improve performance
6. **Back up metadata files** regularly as they contain enrichment results

## Searchability Enhancements

The metadata files can include searchability enhancements:

```json
{
  "document_type": "Letter",
  "sender": "S.N. Goenka",

  "searchable_fields": {
    "full_text_search": "Combined OCR text + summary + context...",
    "faceted_search": {
      "subjects": ["Buddhism", "Vipassana"],
      "people": ["S.N. Goenka", "Student Name"],
      "locations": ["India", "Igatpuri"],
      "time_period": "1990s"
    },
    "semantic_search": {
      "keywords": ["meditation", "dhamma", "course"],
      "concepts": ["mindfulness", "impermanence"]
    }
  }
}
```

## Future Enhancements

Planned features:
1. Support for sidecar XML/RDF formats (Dublin Core, METS)
2. Automatic backup before updates
3. Metadata versioning and history
4. Validation against custom schemas
5. Integration with Archipelago digital repository
6. Support for embedded metadata (EXIF, IPTC, XMP)

## Troubleshooting

### Permission denied errors
```bash
# Check directory permissions
ls -la /data/letters/

# Ensure the agent has write access
chmod -R 755 /data/letters/
```

### File not found
```python
# Always check if file exists before writing
from pathlib import Path
if Path(file_path).exists():
    result = await mcp_client.invoke_tool("write_metadata", {...})
```

### JSON encoding errors
```python
# Ensure all data is JSON-serializable
import json
try:
    json.dumps(metadata)
except TypeError as e:
    print(f"Invalid metadata: {e}")
```

## Support

For issues or questions:
1. Check the test suite: `test_metadata_writer.py`
2. Review the source code: `tools/metadata_writer.py`
3. Check MCP server logs for tool registration
4. Verify agent connection and tool availability

## Related Documentation

- [AMI Metadata Parser Documentation](./AMI_METADATA_PARSER_DOCUMENTATION.md)
- [Enrichment Service Documentation](../../processors/OCR_metadata_extraction/ENRICHMENT_DEBUG_GUIDE.md)
- [MCP Tools Documentation](../../mcp-server/README.md)
