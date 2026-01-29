# Metadata Tools - Quick Reference Card

## 🚀 TL;DR - Just Use This

```python
# Create enriched copy with EXIF + JSON metadata
result = await mcp_client.invoke_tool(
    "create_enriched_copy",
    {
        "image_path": "/data/letters/original.jpg",
        "metadata": enriched_metadata,
        "output_dir": "/data/enriched"
    }
)

# Creates:
# - /data/enriched/original_enriched.jpg (with EXIF)
# - /data/enriched/original_enriched_metadata.json
```

---

## 📋 All 10 MCP Tools

### Enrichment Tools (Original 4)
| Tool | Purpose |
|------|---------|
| `research_historical_context` | Generate historical context |
| `assess_significance` | Assess importance |
| `generate_biographies` | Create bios |
| `parse_ami_filename` | Parse AMI names |

### JSON Metadata Tools (New 3)
| Tool | Purpose | Example |
|------|---------|---------|
| `write_metadata` | Create JSON file | `file.jpg` → `file_metadata.json` |
| `update_metadata` | Update JSON | Merge new fields |
| `read_metadata` | Read JSON | Get metadata |

### EXIF Tools (New 3)
| Tool | Purpose | Best For |
|------|---------|----------|
| `read_image_exif` | Read EXIF | Check existing metadata |
| `write_image_exif` | Write EXIF | Embed in image |
| **`create_enriched_copy`** ⭐ | **Copy + EXIF + JSON** | **Everything!** |

---

## 🎯 Common Tasks

### Task 1: Enrich a Single Image
```python
await mcp_client.invoke_tool("create_enriched_copy", {
    "image_path": "/data/letters/letter001.jpg",
    "metadata": {
        "sender": "S.N. Goenka",
        "date": "1990-05-15",
        "summary": "Meditation guidance..."
    }
})
```

### Task 2: Process a Batch
```python
from tools.exif_metadata_handler import ExifMetadataHandler

handler = ExifMetadataHandler()
batch = [{"image_path": path, "metadata": meta} for path, meta in files]
result = handler.batch_create_copies(batch, "/data/enriched")
```

### Task 3: Full Pipeline (AMI + Enrich + EXIF)
```python
# 1. Parse filename
parsed = await mcp_client.invoke_tool("parse_ami_filename", {"filename": ami_name})

# 2. Enrich
enriched = await orchestrator.enrich_document(doc_id, ocr_data)

# 3. Create enriched copy
await mcp_client.invoke_tool("create_enriched_copy", {
    "image_path": file_path,
    "metadata": {**parsed, **enriched}
})
```

---

## 📦 What Gets Created

### Option 1: JSON Only
```
letter001.jpg
letter001_metadata.json          # JSON only
```

### Option 2: Enriched Copy ⭐ **Recommended**
```
letter001.jpg                          # Original (untouched)
letter001_enriched.jpg                 # Copy with EXIF
letter001_enriched_metadata.json       # Complete JSON
```

---

## 🧪 Testing

```bash
# Test metadata writer (JSON)
python3 test_metadata_writer.py

# Test EXIF handler
python3 test_exif_handler.py

# Verify tools registered
python3 -c "from main import ContextAgent; \
  print(f'{len(ContextAgent().get_tool_definitions())} tools')"
```

Expected: **10 tools**, **All tests pass** ✅

---

## 🔍 Metadata Formats

### JSON (Complete)
```json
{
  "document_type": "Letter",
  "sender": "S.N. Goenka",
  "date": "1990-05-15",
  "subjects": ["Buddhism", "Vipassana"],
  "summary": "Full text...",
  "historical_context": "Long context...",
  "biographies": {...},
  "_metadata_written_at": "2026-01-29T10:00:00"
}
```

### EXIF (Key Fields)
```
ImageDescription: "Summary..."
Artist: "S.N. Goenka"
DateTime: "1990:05:15 10:30:00"
Software: "Heritage Platform"
UserComment: "Full summary..."
```

---

## ⚙️ Configuration

```yaml
# Environment variables (optional)
METADATA_BASE_PATH: /data
ENRICHED_OUTPUT_DIR: /data/enriched
```

---

## 📊 Format Support

| Format | EXIF | JSON | Notes |
|--------|------|------|-------|
| JPEG   | ✅   | ✅   | Best support |
| TIFF   | ✅   | ✅   | Full support |
| PNG    | ❌   | ✅   | JSON only |
| GIF    | ❌   | ✅   | JSON only |

**JSON sidecar always created** for all formats!

---

## 💡 Best Practices

1. ✅ Use `create_enriched_copy` for everything
2. ✅ Keep originals in `/data/originals` (read-only)
3. ✅ Store enriched in `/data/enriched`
4. ✅ Use batch processing for large collections
5. ✅ JSON has complete metadata, EXIF has key fields

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| EXIF not embedding | Check format (JPEG/TIFF only), verify piexif installed |
| Permission denied | `chmod -R 755 /data/enriched/` |
| Metadata truncated | Normal - use JSON for complete data |
| File not found | Check paths, ensure directories exist |

---

## 📚 Full Documentation

- **Metadata Writer**: `METADATA_WRITER_DOCUMENTATION.md`
- **EXIF Handler**: `EXIF_METADATA_DOCUMENTATION.md`
- **Quick Start**: `METADATA_WRITER_QUICK_START.md`
- **Complete Summary**: `METADATA_TOOLS_COMPLETE_SUMMARY.md`

---

## ✨ The One-Liner You Need

```python
# This does everything: creates enriched image copy with EXIF + JSON sidecar
result = await mcp_client.invoke_tool("create_enriched_copy", {
    "image_path": original_path,
    "metadata": enriched_metadata,
    "output_dir": "/data/enriched"
})
```

**That's it!** 🎉

---

## 📞 Quick Check

```python
# Verify tools available
from main import ContextAgent
agent = ContextAgent()
tools = agent.get_tool_definitions()
print(f"Total tools: {len(tools)}")  # Should be 10

metadata_tools = [t['name'] for t in tools if 'metadata' in t['name'] or 'exif' in t['name']]
print(f"Metadata tools: {metadata_tools}")
# Should show: write_metadata, update_metadata, read_metadata,
#              read_image_exif, write_image_exif, create_enriched_copy
```

---

**Ready to enrich your heritage documents!** 🏛️✨
