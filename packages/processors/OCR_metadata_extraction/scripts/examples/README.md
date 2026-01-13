# Example Scripts

This directory contains example code and integration templates for reference and learning.

## Python Examples

### Integration Examples

#### LangChain Integration
- **LANGCHAIN_INTEGRATION_EXAMPLES.py** - Demonstrates LangChain integration patterns including:
  - Prompt templates
  - Chain composition
  - LLM provider integration
  - Document processing

#### PDF Metadata Extraction
- **extract_pdf_metadata.py** - Full-featured PDF metadata extraction
- **extract_pdf_metadata_standalone.py** - Minimal standalone version
- **example_pdf_metadata.py** - Simple usage examples

### Provider Integration

#### LMStudio
- **example_lmstudio_usage.py** - How to use LMStudio OCR provider locally
- **lmstudio_docker_bridge.py** - Bridge LMStudio with Docker containers

#### AMI/Archipelago
- **ami_upload_bhushanji.py** - Example of uploading files to Archipelago

### Utilities & Diagnostics

- **check_ocr_provider_status.py** - Check which OCR providers are available
- **list_endpoints.py** - List all API endpoints
- **fetch_do.py** - Example DigitalOcean integration
- **fix_node_18.py** - Handle Node 18 compatibility
- **fix_node_233_metadata.py** - Handle Node 2.33 metadata
- **diagnose_deployments.py** - Troubleshoot deployment issues

## Running Examples

### Basic Execution
```bash
# Run an example script
python example_name.py

# Run with Python 3.8+
python3 example_name.py
```

### With Environment Setup
```bash
# Set environment variables first
export CLAUDE_API_KEY="your-key-here"
export LMSTUDIO_HOST="http://localhost:1234"

# Then run
python example_name.py
```

### Using Docker
```bash
# Run example in Docker
docker run -v $(pwd):/app -w /app python:3.9 python example_name.py
```

## Example Categories

### 📚 Learning Examples
- `LANGCHAIN_INTEGRATION_EXAMPLES.py` - Learn LangChain patterns
- `example_lmstudio_usage.py` - Simple LMStudio usage
- `example_pdf_metadata.py` - PDF processing basics

### 🔗 Integration Examples
- `LANGCHAIN_INTEGRATION_EXAMPLES.py` - LLM integration
- `lmstudio_docker_bridge.py` - Docker bridge patterns
- `ami_upload_bhushanji.py` - File upload patterns

### 🛠️ Utility Examples
- `check_ocr_provider_status.py` - Status checking
- `list_endpoints.py` - API discovery
- `diagnose_deployments.py` - Diagnostics and troubleshooting

### 📝 Production Examples
- `extract_pdf_metadata.py` - Production-ready extraction
- `extract_pdf_metadata_standalone.py` - Minimal dependencies version

## Common Usage Patterns

### Pattern 1: PDF Metadata Extraction
```bash
python extract_pdf_metadata.py input.pdf output.json
```

### Pattern 2: Check OCR Providers
```bash
python check_ocr_provider_status.py
```

### Pattern 3: LMStudio Integration
```bash
export LMSTUDIO_HOST="http://localhost:1234"
python example_lmstudio_usage.py
```

### Pattern 4: Diagnose Issues
```bash
python diagnose_deployments.py --verbose
```

## Dependencies

Most examples require:
- Python 3.8+
- Core dependencies from `requirements.txt`
- Optional: Additional providers (OpenAI, Anthropic, etc.)

### Installing Dependencies
```bash
cd ../..  # Go to project root
pip install -r requirements.txt

# For specific providers
pip install -r requirements-azure.txt      # Azure Vision
pip install -r requirements-tesseract.txt # Tesseract
```

## Modifying Examples

To adapt examples for your use case:

1. Copy the example file
2. Modify as needed
3. Test with `python your_modified_example.py`
4. Consider contributing improvements back

### Example Modification Template
```python
#!/usr/bin/env python3
"""
Based on example_name.py
Modified for: [your use case]
"""

# Your imports
from example_original import some_function

# Your modifications
def my_custom_function():
    # Your code here
    pass

if __name__ == "__main__":
    my_custom_function()
```

## Troubleshooting Examples

### Import Errors
```bash
# Ensure all dependencies are installed
pip install -r ../../requirements.txt
```

### API Key Errors
```bash
# Set required environment variables
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_CLIENT_ID="your-id"
```

### Connection Errors
```bash
# For local services, verify they're running
python check_ocr_provider_status.py

# For remote services, check network connectivity
python diagnose_deployments.py
```

## Example Contributions

Want to add a new example?

1. Write clear, well-commented code
2. Add docstrings explaining the example
3. Test thoroughly
4. Add to this README
5. Submit a pull request

## Related Documentation

For more information, see:
- `../../docs/LANGCHAIN_START_HERE.md` - LangChain guide
- `../../docs/LMSTUDIO_SETUP.md` - LMStudio setup
- `../../docs/INTEGRATION_E2E_TESTS.md` - Integration tests
- `../../docs/INDEX.md` - Full documentation index

---

**Last Updated:** January 13, 2026
