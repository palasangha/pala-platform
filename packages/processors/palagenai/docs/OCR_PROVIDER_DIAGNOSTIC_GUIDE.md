# OCR Provider Diagnostic Guide - Why Providers Are Disabled

**Date**: December 30, 2024
**Purpose**: Understand and diagnose why OCR providers appear as disabled in the bulk processing UI

---

## Quick Overview

The system supports **12 different OCR providers**, but some may appear as disabled in the UI dropdown. This guide explains:
- Why each provider might be disabled
- What configuration/setup is needed to enable them
- How to check the status of each provider
- How to enable specific providers

---

## The Provider Availability Flow

```
.env File / Environment Variables
    ↓
Backend Config (config.py)
    ↓
Provider Initialization (on startup)
    ↓
is_available() Check for Each Provider
    ↓
API Endpoint /api/ocr/providers
    ↓
Frontend Receives availability status
    ↓
Renders Dropdown with (Disabled) or (Enabled) status
```

---

## All 12 OCR Providers & Their Status

### 1. ✅ CHROME LENS (Usually Enabled)
**Display Name:** "Chrome Lens (Local - No API Key)"

**Why might be disabled:**
- Missing `chrome-lens-py` Python package
- Chrome Lens library not installed

**How to enable:**
```bash
# Install the required package
pip install chrome-lens-py

# Or in docker container:
docker-compose exec backend pip install chrome-lens-py

# Restart backend
docker-compose restart backend
```

**Configuration:**
```bash
CHROME_LENS_ENABLED=true  # (optional, defaults to true)
GOOGLE_LENS_MAX_IMAGE_SIZE_MB=3  # Optional: max image size
```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.chrome_lens_provider import ChromeLensProvider; p = ChromeLensProvider(); print(f'Available: {p.is_available()}')"
```

---

### 2. ⚠️ GOOGLE VISION (Needs Credentials)
**Display Name:** "Google Cloud Vision"

**Why it's disabled:**
- Missing `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Credentials JSON file not found at specified path
- Google Cloud Vision API client cannot initialize

**How to enable:**
1. **Get credentials from Google Cloud:**
   - Go to https://console.cloud.google.com
   - Create a service account
   - Generate JSON credentials file
   - Download the JSON file

2. **Place credentials in backend directory:**
   ```bash
   cp ~/Downloads/your-credentials.json backend/google-credentials.json
   ```

3. **Configure .env:**
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
   GOOGLE_VISION_ENABLED=true
   ```

4. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.google_vision_provider import GoogleVisionProvider; p = GoogleVisionProvider(); print(f'Available: {p.is_available()}')"
```

**Current Status:**
```bash
ls -la backend/google-credentials.json  # Check if file exists
echo $GOOGLE_APPLICATION_CREDENTIALS     # Check env var
```

---

### 3. ⚠️ GOOGLE LENS (Needs Credentials)
**Display Name:** "Google Lens (Advanced)"

**Why it's disabled:**
- Same as Google Vision - needs `GOOGLE_APPLICATION_CREDENTIALS`
- Google Cloud Vision API client not initialized

**How to enable:**
- Follow same steps as Google Vision above
- Uses same credentials file

**Configuration:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
GOOGLE_LENS_ENABLED=true
GOOGLE_LENS_MAX_IMAGE_SIZE_MB=3
```

---

### 4. ⚠️ SERPAPI GOOGLE LENS (Needs API Key)
**Display Name:** "Google Lens (SerpAPI - Hindi & English)"

**Why it's disabled:**
- Missing `SERPAPI_API_KEY` environment variable
- SerpAPI key not configured

**How to enable:**
1. **Get API key:**
   - Go to https://serpapi.com/dashboard
   - Get your API key

2. **Configure .env:**
   ```bash
   SERPAPI_API_KEY=your-api-key-here
   SERPAPI_GOOGLE_LENS_ENABLED=true
   ```

3. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Current Status:**
```bash
grep SERPAPI_API_KEY .env
docker-compose exec -T backend python3 -c "from app.config import Config; print(f'Key: {Config.SERPAPI_API_KEY[:10]}...')"
```

---

### 5. ✅ TESSERACT OCR (Usually Enabled)
**Display Name:** "Tesseract OCR"

**Why it's disabled:**
- `pytesseract` package not installed
- Tesseract binary not found on system
- Tesseract not in PATH

**How to enable:**
1. **Install pytesseract:**
   ```bash
   pip install pytesseract
   ```

2. **Install tesseract binary:**
   - **Ubuntu/Debian:**
     ```bash
     sudo apt-get install tesseract-ocr
     ```
   - **macOS:**
     ```bash
     brew install tesseract
     ```
   - **Windows:**
     Download from: https://github.com/UB-Mannheim/tesseract/wiki

3. **Configure .env (optional):**
   ```bash
   TESSERACT_CMD=/usr/bin/tesseract  # Path to tesseract executable
   TESSERACT_ENABLED=true
   ```

4. **Verify installation:**
   ```bash
   tesseract --version
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.tesseract_provider import TesseractProvider; p = TesseractProvider(); print(f'Available: {p.is_available()}')"
```

---

### 6. ✅ EASYOCR (Usually Enabled)
**Display Name:** "EasyOCR"

**Why it's disabled:**
- `easyocr` package not installed
- First run initialization failed (models not downloaded)

**How to enable:**
1. **Install easyocr:**
   ```bash
   pip install easyocr
   ```

2. **Configure .env (optional):**
   ```bash
   EASYOCR_ENABLED=true
   EASYOCR_GPU=true  # Set to false if no GPU available
   ```

3. **Download models on first use:**
   - First run will download required models (~500MB)
   - Can take several minutes
   - Models cached for future use

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.easyocr_provider import EasyOCRProvider; p = EasyOCRProvider(); print(f'Available: {p.is_available()}')"
```

**Current .env Settings:**
```bash
grep EASYOCR .env
```

---

### 7. ⚠️ AZURE COMPUTER VISION (Needs Credentials)
**Display Name:** "Azure Computer Vision"

**Why it's disabled:**
- Missing `AZURE_VISION_ENDPOINT` and `AZURE_VISION_KEY`
- Azure credentials not configured

**How to enable:**
1. **Get Azure credentials:**
   - Go to https://portal.azure.com
   - Create Computer Vision resource
   - Get endpoint URL and API key

2. **Configure .env:**
   ```bash
   AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_VISION_KEY=your-azure-key-here
   ```

3. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Current Status:**
```bash
grep AZURE_VISION .env
```

---

### 8. ⚠️ OLLAMA (Needs Local Server)
**Display Name:** "Ollama (Gemma3)"

**Why it's disabled:**
- Ollama server not running on configured host
- Cannot connect to `OLLAMA_HOST` address
- Ollama service is offline

**How to enable:**
1. **Install Ollama:**
   - Download from https://ollama.ai
   - Install and run

2. **Start Ollama:**
   ```bash
   ollama serve
   # OR in background:
   nohup ollama serve &
   ```

3. **Configure .env:**
   ```bash
   OLLAMA_ENABLED=true
   OLLAMA_HOST=http://172.12.0.83:11434  # Update with your Ollama server IP
   OLLAMA_MODEL=minicpm-v  # or gemma3:4b
   OLLAMA_TIMEOUT=600
   ```

4. **Verify connection:**
   ```bash
   curl http://172.12.0.83:11434/api/tags
   ```

5. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
# Check if Ollama server is running
curl -s http://172.12.0.83:11434/api/tags | head -20

# Check backend provider status
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.ollama_provider import OllamaProvider; p = OllamaProvider(); print(f'Available: {p.is_available()}')"
```

**Current Configuration:**
```bash
grep OLLAMA .env
```

---

### 9. ⚠️ VLLM (Needs Local Server - Default Disabled)
**Display Name:** "VLLM"

**Why it's disabled:**
- `VLLM_ENABLED` defaults to `false`
- vLLM server not running
- Cannot connect to `VLLM_HOST`

**How to enable:**
1. **Set enabled flag:**
   ```bash
   # Edit .env
   VLLM_ENABLED=true
   ```

2. **Configure server details:**
   ```bash
   VLLM_HOST=http://vllm:8000  # Docker service or IP
   VLLM_MODEL=llama-vision
   VLLM_API_KEY=vllm-secret-token
   VLLM_TIMEOUT=1200
   VLLM_MAX_TOKENS=8192
   ```

3. **Start vLLM server:**
   ```bash
   # In docker-compose:
   docker-compose up vllm

   # OR manually:
   python3 -m vllm.entrypoints.openai.api_server --model llama-vision
   ```

4. **Verify connection:**
   ```bash
   curl -s http://vllm:8000/v1/models | python3 -m json.tool
   ```

5. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.vllm_provider import VLLMProvider; p = VLLMProvider(); print(f'Available: {p.is_available()}')"
```

**Current Configuration:**
```bash
grep VLLM .env
```

---

### 10. ⚠️ LLAMA.CPP (Needs Local Server - Default Disabled)
**Display Name:** "llama.cpp (Local LLM)"

**Why it's disabled:**
- `LLAMACPP_ENABLED` defaults to `false`
- llama.cpp server not running
- Cannot connect to `LLAMACPP_HOST`

**How to enable:**
1. **Set enabled flag:**
   ```bash
   # Edit .env
   LLAMACPP_ENABLED=true
   ```

2. **Configure server details:**
   ```bash
   LLAMACPP_HOST=http://localhost:8000  # Or your llama.cpp server IP
   LLAMACPP_MODEL=gemma-3-12b
   ```

3. **Start llama.cpp server:**
   ```bash
   # Install llama-cpp-python:
   pip install llama-cpp-python

   # Start server:
   python3 -m llama_cpp.server --model /path/to/model.gguf --host localhost --port 8000
   ```

4. **Verify connection:**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.llamacpp_provider import LlamaCppProvider; p = LlamaCppProvider(); print(f'Available: {p.is_available()}')"
```

**Current Configuration:**
```bash
grep LLAMACPP .env
```

---

### 11. ⚠️ CLAUDE AI (Needs API Key)
**Display Name:** "Claude AI (Anthropic)"

**Why it's disabled:**
- Missing `ANTHROPIC_API_KEY` environment variable
- `anthropic` Python package not installed

**How to enable:**
1. **Get API key:**
   - Go to https://console.anthropic.com
   - Get your API key

2. **Install anthropic package:**
   ```bash
   pip install anthropic
   ```

3. **Configure .env:**
   ```bash
   CLAUDE_ENABLED=true
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxx
   CLAUDE_MODEL=claude-3-5-sonnet-20241022
   ```

4. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.claude_provider import ClaudeProvider; p = ClaudeProvider(); print(f'Available: {p.is_available()}')"
```

**Current Status:**
```bash
grep CLAUDE .env
grep ANTHROPIC_API_KEY .env
```

**Note:** Check if `anthropic` is installed:
```bash
docker-compose exec -T backend python3 -c "import anthropic; print('anthropic package is installed')" 2>&1 || echo "anthropic package NOT installed"
```

---

### 12. ⚠️ LM STUDIO (Needs Local Server - Default Disabled)
**Display Name:** "LM Studio (Local LLM)"

**Why it's disabled:**
- `LMSTUDIO_ENABLED` is `false` in .env (was just enabled)
- LM Studio server not running on configured host
- Cannot connect to `LMSTUDIO_HOST`

**How to enable:**
1. **Set enabled flag in .env:**
   ```bash
   LMSTUDIO_ENABLED=true
   ```

2. **Configure server details:**
   ```bash
   LMSTUDIO_HOST=http://localhost:1234
   LMSTUDIO_MODEL=local-model
   LMSTUDIO_API_KEY=lm-studio
   LMSTUDIO_TIMEOUT=600
   LMSTUDIO_MAX_TOKENS=4096
   ```

3. **Start LM Studio:**
   - Download from https://lmstudio.ai
   - Launch the application
   - Load a vision model (e.g., google/gemma-3-27b)

4. **Verify connection:**
   ```bash
   curl http://localhost:1234/v1/models
   ```

5. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

**Status Check:**
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.lmstudio_provider import LMStudioProvider; p = LMStudioProvider(); print(f'Available: {p.is_available()}')"
```

**Current Configuration:**
```bash
grep LMSTUDIO .env
```

---

## How to Check All Provider Statuses

### Quick Status Check (All Providers)
```bash
# Check which providers are enabled in .env
echo "=== ENABLED PROVIDERS ==="
grep -E "ENABLED=true" .env

echo -e "\n=== REQUIRES CREDENTIALS ==="
grep -E "API_KEY|CREDENTIALS|ENDPOINT" .env

echo -e "\n=== REQUIRES LOCAL SERVER ==="
grep -E "_HOST=" .env
```

### Check Backend Provider Status
```bash
# Get all providers with availability status
docker-compose exec -T backend python3 << 'EOF'
from app.services import ocr_service
providers = ocr_service.get_available_providers()
for p in providers:
    status = "✅ ENABLED" if p['available'] else "❌ DISABLED"
    print(f"{status}: {p['display_name']} ({p['name']})")
EOF
```

### Individual Provider Status
```bash
# Replace 'lmstudio' with any provider name
docker-compose exec -T backend python3 -c "
from app.services.ocr_providers.lmstudio_provider import LMStudioProvider
p = LMStudioProvider()
print(f'LM Studio: {\"ENABLED\" if p.is_available() else \"DISABLED\"}')"
```

---

## Dependency Matrix - What Each Provider Needs

| Provider | Python Package | External Service | Credentials | Enabled by Default |
|----------|----------------|------------------|-------------|-------------------|
| Chrome Lens | chrome-lens-py | None | None | ✅ Yes |
| Google Vision | google-cloud-vision | Google Cloud API | Yes (JSON file) | ✅ Yes |
| Google Lens | google-cloud-vision | Google Cloud API | Yes (JSON file) | ✅ Yes |
| SerpAPI Lens | serpapi | SerpAPI Service | Yes (API Key) | ✅ Yes |
| Tesseract | pytesseract | Tesseract Binary | None | ✅ Yes |
| EasyOCR | easyocr | None | None | ✅ Yes |
| Azure | azure-cognitiveservices-vision | Azure Service | Yes (Key + Endpoint) | ✅ Yes |
| Ollama | None | Ollama Server | None | ✅ Yes |
| vLLM | None | vLLM Server | Optional | ❌ No |
| llama.cpp | llama-cpp-python | llama.cpp Server | None | ❌ No |
| Claude | anthropic | Anthropic API | Yes (API Key) | ✅ Yes |
| LM Studio | None | LM Studio Server | Optional | ❌ No |

---

## Troubleshooting Checklist

### Provider Still Shows as Disabled After Configuration

**Step 1:** Verify environment variable is set
```bash
echo $YOUR_ENV_VAR_NAME  # Should print the value
```

**Step 2:** Verify backend has restarted
```bash
docker-compose restart backend
docker-compose logs backend | grep -i "startup\|started" | tail -5
```

**Step 3:** Check if backend can read the variable
```bash
docker-compose exec -T backend python3 -c "from app.config import Config; print(f'Variable: {Config.YOUR_VARIABLE}')"
```

**Step 4:** Check provider initialization logs
```bash
docker-compose logs backend | grep -i "provider\|disabled" | tail -20
```

**Step 5:** Test provider directly
```bash
docker-compose exec -T backend python3 -c "from app.services.ocr_providers.your_provider import YourProvider; p = YourProvider(); print(p.is_available())"
```

### Server Connection Issues

**For Ollama:**
```bash
# Check Ollama server is running
curl http://172.12.0.83:11434/api/tags

# Check firewall allows connection
telnet 172.12.0.83 11434
```

**For LM Studio:**
```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Check port is open
netstat -an | grep 1234
```

**For VLLM/llama.cpp:**
```bash
# Check server endpoint
curl http://your-host:8000/health
```

---

## Summary Table - Provider Status Guide

| Provider | Status | Why Disabled | To Enable |
|----------|--------|------------|-----------|
| Chrome Lens | Usually ✅ | Missing package | `pip install chrome-lens-py` |
| Google Vision | Needs Config | Missing credentials | Add JSON credentials file |
| Google Lens | Needs Config | Missing credentials | Add JSON credentials file |
| SerpAPI Lens | Needs Config | Missing API key | Set `SERPAPI_API_KEY` |
| Tesseract | Usually ✅ | Missing binary | Install tesseract-ocr |
| EasyOCR | Usually ✅ | Missing package | `pip install easyocr` |
| Azure | Needs Config | Missing credentials | Set `AZURE_VISION_*` vars |
| Ollama | Needs Server | Server offline | Start Ollama service |
| vLLM | Disabled | `VLLM_ENABLED=false` | Set `VLLM_ENABLED=true` + start server |
| llama.cpp | Disabled | `LLAMACPP_ENABLED=false` | Set `LLAMACPP_ENABLED=true` + start server |
| Claude | Needs Config | Missing API key | Set `ANTHROPIC_API_KEY` |
| LM Studio | Needs Server | Server offline OR disabled | Set `LMSTUDIO_ENABLED=true` + start LM Studio |

---

## File Locations & Configuration

**Environment Variables File:** `.env`
**Backend Configuration:** `backend/app/config.py`
**Providers Code:** `backend/app/services/ocr_providers/`
**API Endpoint:** `GET /api/ocr/providers`
**Frontend Rendering:** `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`

---

## Next Steps

1. **Check current status:**
   ```bash
   docker-compose exec -T backend python3 << 'EOF'
   from app.services import ocr_service
   providers = ocr_service.get_available_providers()
   for p in providers:
       status = "✅" if p['available'] else "❌"
       print(f"{status} {p['display_name']}")
   EOF
   ```

2. **Identify which providers you need**

3. **Follow the enable instructions above for each provider**

4. **Restart backend after configuration**

5. **Verify in bulk processing UI**

---

**Created:** December 30, 2024
**Status:** ✅ Complete Reference Guide
**Purpose:** Diagnose and enable OCR providers
