# OCR Metadata Extraction - Example External App

This is an **example external web application** that demonstrates how to integrate with Pala Platform.

## Architecture

This app is **NOT part of Pala Platform core**. It's a standalone web application that:
- Has its own Flask backend with OCR business logic
- Has its own React frontend for uploading images
- Has its own local temp storage
- **Uses Pala Platform's Storage Agent** to persist OCR results in the unified database

## Integration with Pala Platform

```python
# Backend calls Pala Platform's storage-agent after OCR extraction
result = await mcp_client.invoke_tool(
    agent_id="storage-agent",
    tool_name="store_extraction",
    arguments={
        "source_type": "ocr",
        "source_id": file_uuid,
        "data": extracted_text,
        "data_type": "text",
        "metadata": {"image_size": {"width": 800, "height": 600}},
        "provider": "ollama",  # or tesseract, lmstudio
        "confidence": 0.92,
        "created_by": "ocr-app"
    }
)
```

## Running This Example

1. **Start Pala Platform core services first:**
   ```bash
   cd /path/to/pala-platform
   ./start-dev.sh
   ```

2. **Then start this OCR app:**
   ```bash
   cd packages/processors/OCR_metadata_extraction
   ./start.sh  # or your own startup command
   ```

3. **Upload images through the OCR frontend**
   - Images are processed by this app's OCR logic
   - Results are stored in Pala Platform's unified DB
   - Results can be queried by other apps or chatbot

## Purpose

This app demonstrates:
- ✅ How external apps integrate with Pala Platform
- ✅ Using `storage-agent` as the integration point
- ✅ Maintaining app independence while contributing to unified data store
- ✅ Optional use of `metadata-extractor` for enrichment

## Not Required

This app is **optional**. You can delete it or use it as a reference for building your own web apps that integrate with Pala Platform.

## Other Example Apps (Future)

- Transcription app (uses Whisper, stores via `storage-agent`)
- Translation app (uses translation API, stores via `storage-agent`)
- Document conversion app (converts formats, stores via `storage-agent`)

All follow the same pattern: own logic + Pala Platform storage integration.
