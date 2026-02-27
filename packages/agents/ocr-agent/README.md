# OCR Agent

Stateless agent for extracting text from images and scanned documents using OCR (Optical Character Recognition).

## Features

- **Multiple OCR Providers**: Tesseract (with extensible interface for Cloud Vision, Azure OCR, etc.)
- **Language Support**: Multi-language OCR (English, French, German, etc.)
- **Confidence Scores**: Per-word and overall confidence metrics
- **Bounding Boxes**: Word-level position information
- **MCP Integration**: Connects to MCP server for orchestration

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Tesseract OCR engine (system dependency)
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# For additional languages
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-fra tesseract-ocr-deu  # Ubuntu
```

## Usage

```bash
# Start the OCR agent
python main.py

# Or with custom MCP server URL
MCP_SERVER_URL=ws://localhost:3000 python main.py
```

## Tool: extract_text

Extract text from an image or scanned document.

**Parameters:**
- `image_path` (required): Path to the image file
- `language` (optional): Language code (default: 'eng')
  - Examples: 'eng', 'fra', 'deu', 'spa', 'ita'
- `provider` (optional): OCR provider (default: 'tesseract')
- `psm` (optional): Page segmentation mode (default: 3)
  - 0 = Orientation and script detection (OSD) only
  - 1 = Automatic page segmentation with OSD
  - 3 = Fully automatic page segmentation (default)
  - 6 = Assume a single uniform block of text
  - 11 = Sparse text. Find as much text as possible in no particular order

**Returns:**
```json
{
  "text": "Extracted text content...",
  "confidence": 0.95,
  "word_confidence": [
    {
      "word": "Letter",
      "confidence": 0.98,
      "bbox": {
        "left": 10,
        "top": 10,
        "width": 50,
        "height": 20
      }
    }
  ],
  "language": "eng",
  "metadata": {
    "provider": "tesseract",
    "image_path": "/path/to/image.jpg",
    "timestamp": "2026-02-26T10:30:00Z",
    "image_size": {
      "width": 800,
      "height": 1200
    }
  }
}
```

## Architecture

```
ocr-agent/
├── main.py                 # Agent entry point, MCP integration
├── providers/
│   ├── base_provider.py    # Abstract OCR provider interface
│   └── tesseract_provider.py  # Tesseract implementation
├── requirements.txt
└── README.md
```

## Adding New OCR Providers

1. Create a new provider class inheriting from `BaseOCRProvider`
2. Implement the `extract_text` method
3. Update `main.py` to support the new provider

Example:
```python
from providers.base_provider import BaseOCRProvider

class CloudVisionProvider(BaseOCRProvider):
    async def extract_text(self, image_path: str, language: str = "eng", **kwargs):
        # Implement Cloud Vision API integration
        pass
```

## Testing

```bash
# Test with a sample image
python -c "
import asyncio
from providers.tesseract_provider import TesseractOCRProvider

async def test():
    provider = TesseractOCRProvider()
    result = await provider.extract_text('sample.jpg', language='eng')
    print(result['text'])

asyncio.run(test())
"
```

## Configuration

Environment variables:
- `MCP_SERVER_URL`: WebSocket URL of MCP server (default: ws://localhost:3000)
- `TESSERACT_CMD`: Path to tesseract binary (optional, auto-detected)

## Dependencies

- `websockets`: WebSocket client for MCP communication
- `pytesseract`: Python wrapper for Tesseract OCR
- `Pillow`: Image processing library
- `tesseract`: System OCR engine (brew/apt install)
