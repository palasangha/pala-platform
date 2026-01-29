# EXIF Metadata Tools Documentation

## Overview

The EXIF Metadata Tools enable reading and writing metadata directly to image files, creating enriched copies with embedded metadata, and managing both JSON sidecar files and EXIF-embedded metadata.

## Features

1. **Read EXIF**: Extract existing EXIF/IPTC/XMP metadata from images
2. **Write EXIF**: Embed enriched metadata into image EXIF tags
3. **Create Enriched Copies**: Generate new images with both embedded EXIF and JSON sidecar files
4. **Batch Processing**: Process multiple images efficiently
5. **Format Support**: JPEG, TIFF (full support), PNG (limited)

## MCP Tools

### 1. `read_image_exif`

Read EXIF/IPTC metadata from an image file.

**Parameters:**
- `image_path` (string, required): Path to image file

**Returns:**
```json
{
  "success": true,
  "image_path": "/data/images/photo.jpg",
  "exif": {
    "ImageDescription": "Historical letter",
    "Artist": "S.N. Goenka",
    "DateTime": "1990:05:15 10:30:00",
    "Software": "Heritage Platform",
    "Copyright": "VRI"
  },
  "image_info": {
    "format": "JPEG",
    "mode": "RGB",
    "size": [800, 600],
    "width": 800,
    "height": 600
  }
}
```

**Example:**
```python
result = await mcp_client.invoke_tool(
    "read_image_exif",
    {"image_path": "/data/letters/letter001.jpg"}
)
```

### 2. `write_image_exif`

Write enriched metadata to image EXIF tags.

**Parameters:**
- `image_path` (string, required): Path to source image
- `metadata` (object, required): Metadata to embed
- `output_path` (string, optional): Output path (defaults to overwrite)

**Metadata Mapping:**
- `title` or `summary` → **ImageDescription** (EXIF tag 270)
- `sender`, `author`, `creator` → **Artist** (tag 315)
- `date`, `original_date` → **DateTime** (tag 306)
- `copyright` → **Copyright** (tag 33432)
- `summary`, `historical_context` → **UserComment** (tag 37510)
- Minimal structured data → **MakerNote** (JSON)

**Returns:**
```json
{
  "success": true,
  "output_path": "/data/letters/letter001_enriched.jpg",
  "original_path": "/data/letters/letter001.jpg",
  "metadata_keys": ["title", "sender", "date", "summary"]
}
```

**Example:**
```python
result = await mcp_client.invoke_tool(
    "write_image_exif",
    {
        "image_path": "/data/letters/letter001.jpg",
        "metadata": {
            "title": "Letter from S.N. Goenka",
            "sender": "S.N. Goenka",
            "date": "1990-05-15T10:30:00",
            "summary": "Discussion of meditation practices",
            "copyright": "Vipassana Research Institute"
        },
        "output_path": "/data/letters/letter001_with_exif.jpg"
    }
)
```

### 3. `create_enriched_copy` ⭐ **Recommended**

Create a copy of an image with **both** embedded EXIF metadata **and** a JSON sidecar file.

**Parameters:**
- `image_path` (string, required): Path to original image
- `metadata` (object, required): Enriched metadata
- `output_dir` (string, optional): Output directory (defaults to same as source)
- `suffix` (string, optional): Filename suffix (default: `_enriched`)

**What it creates:**
1. **Enriched Image**: Copy with embedded EXIF metadata
2. **JSON Sidecar**: Complete metadata in JSON format
3. **Preserved Original**: Original file remains untouched

**Returns:**
```json
{
  "success": true,
  "original_image": "/data/letters/letter001.jpg",
  "enriched_image": "/data/letters/letter001_enriched.jpg",
  "metadata_json": "/data/letters/letter001_enriched_metadata.json",
  "exif_embedded": true,
  "file_sizes": {
    "original": 245680,
    "enriched_image": 246120,
    "metadata_json": 1523
  }
}
```

**Example:**
```python
result = await mcp_client.invoke_tool(
    "create_enriched_copy",
    {
        "image_path": "/data/letters/original_letter.jpg",
        "metadata": {
            "document_type": "Letter",
            "sender": "S.N. Goenka",
            "recipient": "Student",
            "date": "1990-05-15",
            "subjects": ["Buddhism", "Vipassana"],
            "summary": "A letter discussing meditation practices...",
            "historical_context": "Written during...",
            "significance": "High historical importance",
            "biographies": {...}
        },
        "output_dir": "/data/enriched",
        "suffix": "_enriched"
    }
)
```

## File Organization

### Default Behavior (same directory)
```
/data/letters/
├── letter001.jpg                          # Original
├── letter001_enriched.jpg                 # Copy with EXIF
└── letter001_enriched_metadata.json       # Complete metadata
```

### Custom Output Directory
```
/data/letters/letter001.jpg                # Original (untouched)

/data/enriched/
├── letter001_enriched.jpg                 # Copy with EXIF
└── letter001_enriched_metadata.json       # Complete metadata
```

## Metadata Format

### JSON Sidecar File
```json
{
  "document_type": "Letter",
  "sender": "S.N. Goenka",
  "recipient": "Student",
  "date": "1990-05-15",
  "subjects": ["Buddhism", "Vipassana", "Meditation"],
  "summary": "A letter discussing meditation practices...",
  "historical_context": "Written during Vipassana expansion...",
  "significance": "High historical importance",
  "biographies": {
    "S.N. Goenka": "Renowned teacher..."
  },

  "_metadata_written_at": "2026-01-29T10:00:00",
  "_original_file": "/data/letters/letter001.jpg",
  "_enriched_image": "/data/letters/letter001_enriched.jpg",
  "_metadata_file": "/data/letters/letter001_enriched_metadata.json"
}
```

### EXIF Embedded Fields
```
ImageDescription: "A letter discussing meditation practices..."
Artist: "S.N. Goenka"
DateTime: "1990:05:15 10:30:00"
Software: "Heritage Platform - AI Enriched 2026-01-29"
Copyright: "Vipassana Research Institute"
UserComment: "A letter discussing meditation practices..."
MakerNote: {"document_type":"Letter","sender":"S.N. Goenka",...}
```

## Integration Examples

### Complete Enrichment Pipeline

```python
from enrichment_service.mcp_client.client import MCPClient

mcp_client = MCPClient()

# 1. Parse AMI filename
parsed = await mcp_client.invoke_tool(
    "parse_ami_filename",
    {"filename": "MSALTMEBA00100004.00_LT_MIX_1990_GOENKA_TO_STUDENT.JPG"}
)

# 2. Enrich with AI
enriched = await orchestrator.enrich_document(
    document_id="DOC001",
    ocr_data=ocr_data
)

# 3. Combine AMI + Enrichment
full_metadata = {
    **parsed,
    **enriched,
    "archipelago_fields": parsed["archipelago_fields"]
}

# 4. Create enriched copy (EXIF + JSON)
result = await mcp_client.invoke_tool(
    "create_enriched_copy",
    {
        "image_path": f"/data/originals/{parsed['filename']}",
        "metadata": full_metadata,
        "output_dir": "/data/enriched",
        "suffix": "_enriched"
    }
)

print(f"✓ Created: {result['enriched_image']}")
print(f"✓ Metadata: {result['metadata_json']}")
```

### Batch Processing

```python
from tools.exif_metadata_handler import ExifMetadataHandler

handler = ExifMetadataHandler()

# Prepare batch
batch = []
for doc in documents:
    batch.append({
        "image_path": doc["file_path"],
        "metadata": doc["enriched_metadata"],
        "suffix": "_enriched"
    })

# Process all at once
result = handler.batch_create_copies(batch, output_dir="/data/enriched")

print(f"Processed: {result['successful']}/{result['total']}")
```

### Archive Creation Workflow

```python
# For each collection, create enriched archive
for collection in collections:
    for document in collection.documents:
        # Parse filename
        parsed = await mcp_client.invoke_tool("parse_ami_filename", ...)

        # Enrich content
        enriched = await orchestrator.enrich_document(...)

        # Create enriched copy for archive
        result = await mcp_client.invoke_tool(
            "create_enriched_copy",
            {
                "image_path": document.path,
                "metadata": {**parsed, **enriched},
                "output_dir": f"/archive/collections/{collection.id}/enriched",
                "suffix": "_archive"
            }
        )

        # Archive both original + enriched
        archive.add(document.path)  # Original
        archive.add(result["enriched_image"])  # With EXIF
        archive.add(result["metadata_json"])  # Metadata
```

## Format Support

| Format | Read EXIF | Write EXIF | Notes |
|--------|-----------|------------|-------|
| JPEG   | ✅ Full   | ✅ Full    | Best support |
| TIFF   | ✅ Full   | ✅ Full    | Best support |
| PNG    | ⚠️ Limited | ❌ No      | Uses tEXt chunks instead |
| GIF    | ❌ No      | ❌ No      | Not supported |
| PDF    | ❌ No      | ❌ No      | Use different method |

For **all formats**, the JSON sidecar file is **always created**, ensuring metadata is preserved regardless of image format limitations.

## EXIF Tag Reference

### Standard EXIF Tags Used

| EXIF Tag | Tag ID | Metadata Field | Description |
|----------|--------|----------------|-------------|
| ImageDescription | 270 | title, summary | Document title/summary |
| Artist | 315 | sender, author, creator | Creator/author |
| DateTime | 306 | date, original_date | Creation date/time |
| Copyright | 33432 | copyright | Copyright notice |
| Software | 305 | (auto) | Processing software |
| UserComment | 37510 | summary, context | Long description |
| MakerNote | 37500 | (structured) | JSON metadata |

## Configuration

Environment variables:
```yaml
# Not used by EXIF handler (uses image file paths)
# But can set default output locations
ENRICHED_OUTPUT_DIR: /data/enriched
```

## Best Practices

### 1. **Always Create Copies**
✅ Use `create_enriched_copy` to preserve originals
❌ Don't overwrite original files

### 2. **Use JSON Sidecar for Complete Metadata**
- EXIF has size limits (~2-4 KB per field)
- JSON has no limits
- JSON is more portable

### 3. **Embed Key Fields in EXIF**
Prioritize for EXIF embedding:
- Title/Description
- Creator/Author
- Date
- Copyright
- Brief summary

### 4. **Directory Organization**
```
/data/
├── originals/           # Original scans (read-only)
├── enriched/            # Enriched copies (EXIF + JSON)
└── archive/             # Long-term storage
```

### 5. **Batch Processing**
For large collections, use batch functions:
```python
handler.batch_create_copies(batch, output_dir="/data/enriched")
```

## Error Handling

All tools return `success` status:

```python
result = await mcp_client.invoke_tool("create_enriched_copy", {...})

if result['success']:
    print(f"✓ Created: {result['enriched_image']}")
    # Both EXIF and JSON are ready
else:
    print(f"✗ Error: {result['error']}")
    # Handle error (retry, skip, alert)
```

Common errors:
- **File not found**: Check image path
- **Permission denied**: Check directory permissions
- **EXIF write failed**: Falls back to plain copy + JSON (still successful)
- **Invalid format**: Use JSON sidecar only

## Testing

Run the test suite:

```bash
cd packages/agents/context-agent
python3 test_exif_handler.py
```

Expected output:
```
✓ PASS: read_exif
✓ PASS: write_exif
✓ PASS: create_enriched_copy
✓ PASS: batch_processing
✓ PASS: full_pipeline

Total: 5/5 tests passed
🎉 All tests passed!
```

## Performance

### Benchmarks (approximate)

| Operation | Time | Notes |
|-----------|------|-------|
| Read EXIF | ~10ms | Very fast |
| Write EXIF | ~100ms | Image re-encoding |
| Create enriched copy | ~150ms | Copy + EXIF + JSON |
| Batch (100 images) | ~15s | Parallel processing |

### Optimization Tips

1. **Batch processing**: Process multiple images together
2. **Quality settings**: Adjust JPEG quality if size matters
3. **Parallel execution**: Use asyncio for multiple files
4. **Skip small files**: Don't enrich thumbnails

## Advanced Usage

### Custom EXIF Fields

```python
# Add custom fields via metadata dictionary
metadata = {
    "title": "Historical Document",
    "author": "S.N. Goenka",
    "custom_field": "This goes in MakerNote as JSON"
}
```

### Read EXIF from Existing Files

```python
# Check what's already embedded
result = await mcp_client.invoke_tool(
    "read_image_exif",
    {"image_path": "/data/letters/scanned_letter.jpg"}
)

if result['success']:
    exif = result['exif']
    print(f"Scan date: {exif.get('DateTime')}")
    print(f"Scanner: {exif.get('Software')}")
```

### Migrate Metadata to EXIF

```python
# Read JSON metadata
json_result = await mcp_client.invoke_tool(
    "read_metadata",
    {"metadata_file_path": "/data/letters/letter001_metadata.json"}
)

# Embed into image
if json_result['success']:
    await mcp_client.invoke_tool(
        "write_image_exif",
        {
            "image_path": "/data/letters/letter001.jpg",
            "metadata": json_result['metadata'],
            "output_path": "/data/letters/letter001_with_exif.jpg"
        }
    )
```

## Troubleshooting

### EXIF not embedding
- Check file format (JPEG/TIFF only)
- Verify piexif is installed
- Check file permissions

### Large metadata truncated
- EXIF has size limits
- Use JSON sidecar for complete data
- Only key fields go in EXIF

### Copy failed
- Check disk space
- Verify output directory exists
- Check file permissions

## Future Enhancements

Planned features:
1. XMP metadata support
2. IPTC keyword embedding
3. GPS coordinate embedding
4. Thumbnail generation
5. Watermarking support
6. Multi-page TIFF handling

## Related Documentation

- [Metadata Writer Documentation](./METADATA_WRITER_DOCUMENTATION.md)
- [AMI Parser Documentation](./AMI_METADATA_PARSER_DOCUMENTATION.md)
- [Quick Start Guide](./METADATA_WRITER_QUICK_START.md)

## Support

Check tool availability:
```python
from main import ContextAgent
agent = ContextAgent()
tools = [t['name'] for t in agent.get_tool_definitions()]
print(f"EXIF tools available: {any('exif' in t for t in tools)}")
```

Should output:
```
EXIF tools available: True
```
