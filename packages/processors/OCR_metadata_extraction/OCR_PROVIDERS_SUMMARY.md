# OCR Providers Complete Summary

**Created**: December 30, 2024
**Purpose**: Quick reference for all 12 OCR providers and why they might be disabled

---

## 📋 System Overview

Your system has **12 different OCR providers** available:

```
┌─────────────────────────────────────────────────────────────┐
│          OCR PROVIDER ECOSYSTEM (12 Total)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LOCAL PROVIDERS (No External API):                        │
│  ✅ Chrome Lens        ✅ Tesseract    ✅ EasyOCR         │
│  ⚠️  Ollama Server      ⚠️  VLLM Server  ⚠️  llama.cpp     │
│  ⚠️  LM Studio Server                                      │
│                                                             │
│  CLOUD PROVIDERS (Need API Keys/Credentials):              │
│  ✅ Google Vision      ✅ Google Lens                      │
│  ✅ SerpAPI Google Lens ✅ Claude AI (Anthropic)           │
│  ✅ Azure Computer Vision                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start - Enable a Provider

### Fastest Providers to Enable
1. **Chrome Lens** - Just install: `pip install chrome-lens-py`
2. **Tesseract** - Install binary: `sudo apt-get install tesseract-ocr`
3. **EasyOCR** - Just install: `pip install easyocr`

### Providers That Need Credentials
1. **Google Vision** - Need JSON credentials file
2. **Claude** - Need ANTHROPIC_API_KEY
3. **Azure** - Need AZURE_VISION_ENDPOINT + AZURE_VISION_KEY
4. **SerpAPI** - Need SERPAPI_API_KEY

### Providers That Need Servers Running
1. **Ollama** - Run Ollama application on your system
2. **LM Studio** - Run LM Studio application on your system
3. **VLLM** - Start vLLM server
4. **llama.cpp** - Start llama.cpp server

---

## 🔍 Understanding Why Providers are Disabled

Each provider has 3 potential failure points:

```
Environment Variable
        ↓
    [Not Set] → DISABLED
        ↓ (Set)
Dependencies/Package
        ↓
    [Missing] → DISABLED
        ↓ (Installed)
Server/Service Check
        ↓
    [Offline] → DISABLED
        ↓ (Online)
✅ ENABLED
```

---

## 📖 Complete Provider Reference

### **Group 1: Usually Enabled by Default**

#### 1️⃣ Chrome Lens
- **Status**: ✅ Usually works
- **Type**: Local
- **Requires**: `chrome-lens-py` package
- **Cost**: Free
- **Speed**: Fast
- **Accuracy**: Good
- **Why disabled**: Missing `chrome-lens-py` package

#### 2️⃣ Tesseract OCR
- **Status**: ✅ Usually works
- **Type**: Local
- **Requires**: `pytesseract` package + tesseract binary
- **Cost**: Free
- **Speed**: Fast
- **Accuracy**: Good for typed text
- **Why disabled**: Missing pytesseract or tesseract binary

#### 3️⃣ EasyOCR
- **Status**: ✅ Usually works
- **Type**: Local
- **Requires**: `easyocr` package
- **Cost**: Free
- **Speed**: Moderate (models downloaded on first use)
- **Accuracy**: Very good (supports 80+ languages)
- **Why disabled**: Missing easyocr package

#### 4️⃣ Ollama
- **Status**: ⚠️ Needs server
- **Type**: Local server
- **Requires**: Ollama application running
- **Default**: Enabled (`OLLAMA_ENABLED=true`)
- **Cost**: Free
- **Speed**: Depends on system
- **Accuracy**: Excellent
- **Why disabled**: Ollama server not running at `http://172.12.0.83:11434`

---

### **Group 2: Needs Configuration to Enable**

#### 5️⃣ Google Vision
- **Status**: ⚠️ Needs credentials
- **Type**: Cloud API
- **Requires**: `google-cloud-vision` package + JSON credentials file
- **Default**: Enabled (`GOOGLE_VISION_ENABLED=true`)
- **Cost**: Pay-per-use
- **Speed**: Fast
- **Accuracy**: Excellent
- **Why disabled**: Missing `GOOGLE_APPLICATION_CREDENTIALS`
- **How to fix**:
  ```bash
  # 1. Get credentials from Google Cloud Console
  # 2. Place in backend/google-credentials.json
  # 3. Set GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json in .env
  # 4. Restart: docker-compose restart backend
  ```

#### 6️⃣ Google Lens
- **Status**: ⚠️ Needs credentials
- **Type**: Cloud API
- **Requires**: Same as Google Vision (shared API)
- **Default**: Enabled
- **Cost**: Pay-per-use
- **Speed**: Fast
- **Accuracy**: Excellent (document metadata extraction)
- **Why disabled**: Missing `GOOGLE_APPLICATION_CREDENTIALS`

#### 7️⃣ SerpAPI Google Lens
- **Status**: ⚠️ Needs API key
- **Type**: Cloud API
- **Requires**: SerpAPI account + API key
- **Default**: Enabled
- **Cost**: Pay-per-use
- **Speed**: Fast
- **Accuracy**: Good (optimized for Hindi & English)
- **Why disabled**: Missing `SERPAPI_API_KEY`
- **How to fix**:
  ```bash
  # 1. Get key from https://serpapi.com
  # 2. Set SERPAPI_API_KEY=your-key in .env
  # 3. Restart: docker-compose restart backend
  ```

#### 8️⃣ Azure Computer Vision
- **Status**: ⚠️ Needs credentials
- **Type**: Cloud API
- **Requires**: Azure account + credentials
- **Default**: Enabled
- **Cost**: Pay-per-use
- **Speed**: Fast
- **Accuracy**: Excellent
- **Why disabled**: Missing `AZURE_VISION_ENDPOINT` or `AZURE_VISION_KEY`
- **How to fix**:
  ```bash
  # 1. Create Computer Vision resource in Azure Portal
  # 2. Get endpoint and key
  # 3. Set in .env:
  #    AZURE_VISION_ENDPOINT=https://xxx.cognitiveservices.azure.com/
  #    AZURE_VISION_KEY=your-key
  # 4. Restart: docker-compose restart backend
  ```

#### 9️⃣ Claude AI (Anthropic)
- **Status**: ⚠️ Needs API key
- **Type**: Cloud API
- **Requires**: `anthropic` package + API key
- **Default**: Enabled (`CLAUDE_ENABLED=true`)
- **Cost**: Pay-per-use
- **Speed**: Fast
- **Accuracy**: Excellent (multimodal)
- **Why disabled**: Missing `ANTHROPIC_API_KEY` OR missing `anthropic` package
- **How to fix**:
  ```bash
  # 1. Get key from https://console.anthropic.com
  # 2. Install package: pip install anthropic
  # 3. Set ANTHROPIC_API_KEY=sk-ant-api03-xxx in .env
  # 4. Restart: docker-compose restart backend
  ```

---

### **Group 3: Disabled by Default (Experimental/Optional)**

#### 🔟 VLLM
- **Status**: ❌ Default disabled
- **Type**: Local server (inference)
- **Requires**: vLLM server + `VLLM_ENABLED=true`
- **Default**: Disabled (`VLLM_ENABLED=false`)
- **Cost**: Free
- **Speed**: Fast
- **Accuracy**: Excellent
- **Why disabled**: Experimental feature, off by default
- **How to enable**:
  ```bash
  # 1. Set VLLM_ENABLED=true in .env
  # 2. Start vLLM server
  # 3. Set VLLM_HOST, VLLM_MODEL in .env
  # 4. Restart: docker-compose restart backend
  ```

#### 1️⃣1️⃣ llama.cpp (Local LLM)
- **Status**: ❌ Default disabled
- **Type**: Local server
- **Requires**: llama.cpp server + `LLAMACPP_ENABLED=true`
- **Default**: Disabled
- **Cost**: Free
- **Speed**: Depends on system
- **Accuracy**: Excellent
- **Why disabled**: Experimental feature, off by default
- **How to enable**:
  ```bash
  # 1. Set LLAMACPP_ENABLED=true in .env
  # 2. Start llama.cpp server
  # 3. Set LLAMACPP_HOST, LLAMACPP_MODEL in .env
  # 4. Restart: docker-compose restart backend
  ```

#### 1️⃣2️⃣ LM Studio (Local LLM)
- **Status**: ❌ Default disabled (Now enabled!)
- **Type**: Local server (OpenAI-compatible API)
- **Requires**: LM Studio app running + `LMSTUDIO_ENABLED=true`
- **Default**: Disabled → Now `LMSTUDIO_ENABLED=true` in .env
- **Cost**: Free
- **Speed**: Depends on system
- **Accuracy**: Excellent (vision models)
- **Why disabled**: Server offline OR `LMSTUDIO_ENABLED=false`
- **Current Status**: ✅ ENABLED in .env (set to true)
- **How to enable**:
  ```bash
  # 1. Start LM Studio application on your machine
  # 2. Verify running: curl http://localhost:1234/v1/models
  # 3. Check .env has: LMSTUDIO_ENABLED=true
  # 4. Restart: docker-compose restart backend
  ```

---

## 🎯 Diagnostic Checklist

To understand why a specific provider is disabled:

### **Step 1: Check Environment Variable**
```bash
# Is the provider enabled?
grep "PROVIDER_ENABLED\|PROVIDER_API_KEY\|PROVIDER_HOST" .env

# What's the current value?
echo $PROVIDER_ENABLED
echo $PROVIDER_API_KEY
echo $PROVIDER_HOST
```

### **Step 2: Check Configuration**
```bash
# Is the backend reading it?
docker-compose exec -T backend python3 -c "
from app.config import Config
print(f'PROVIDER_ENABLED: {Config.PROVIDER_ENABLED}')
"
```

### **Step 3: Check Provider Status**
```bash
# Is the provider available?
docker-compose exec -T backend python3 -c "
from app.services.ocr_providers.provider_name import ProviderName
p = ProviderName()
print(f'Available: {p.is_available()}')
"
```

### **Step 4: Check Backend Response**
```bash
# What does the API return?
curl -s http://localhost:5000/api/ocr/providers \
  -H "Authorization: Bearer TOKEN" | python3 -m json.tool
```

---

## 💾 Environment Variables Reference

### **File**: `.env` (in project root)

```bash
# Local Providers
CHROME_LENS_ENABLED=true
GOOGLE_LENS_MAX_IMAGE_SIZE_MB=3
TESSERACT_ENABLED=true
TESSERACT_CMD=/usr/bin/tesseract
EASYOCR_ENABLED=true
EASYOCR_GPU=true

# Server-based Providers
OLLAMA_ENABLED=true
OLLAMA_HOST=http://172.12.0.83:11434
OLLAMA_MODEL=minicpm-v
OLLAMA_TIMEOUT=600

VLLM_ENABLED=false  # Set to true to enable
VLLM_HOST=http://vllm:8000
VLLM_MODEL=llama-vision
VLLM_API_KEY=vllm-secret-token

LLAMACPP_ENABLED=false  # Set to true to enable
LLAMACPP_HOST=http://localhost:8000
LLAMACPP_MODEL=gemma-3-12b

LMSTUDIO_ENABLED=true  # Now enabled!
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=local-model
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_TIMEOUT=600
LMSTUDIO_MAX_TOKENS=4096

# Cloud Providers (Credentials-based)
GOOGLE_APPLICATION_CREDENTIALS=google-credentials.json
GOOGLE_VISION_ENABLED=true
GOOGLE_LENS_ENABLED=true

SERPAPI_API_KEY=your-api-key
SERPAPI_GOOGLE_LENS_ENABLED=true

AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_VISION_KEY=your-azure-key

CLAUDE_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-api03-xxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

---

## 🧪 Testing Provider Status

### **Quick Status Check (Bash)**
```bash
# See which providers are configured
echo "=== CHECKING CONFIGURATION ==="
grep -E "ENABLED|API_KEY|CREDENTIALS|HOST" .env | head -20

# Check backend logs
echo -e "\n=== CHECKING BACKEND LOGS ==="
docker-compose logs backend | grep -i "provider\|disabled" | tail -10
```

### **Full Diagnostic (Python)**
```bash
# Inside backend container
docker-compose exec -T backend python3 << 'EOF'
from app.services import ocr_service

providers = ocr_service.get_available_providers()
print("OCR PROVIDER STATUS:\n")
for p in providers:
    status = "✅" if p['available'] else "❌"
    print(f"{status} {p['display_name']:<50} ({p['name']})")
EOF
```

---

## 📁 Related Documentation

- **OCR_PROVIDER_DIAGNOSTIC_GUIDE.md** - Detailed guide for each provider
- **check_ocr_provider_status.py** - Python script to check all providers
- **LMSTUDIO_BULK_PROCESSING_FIX.md** - How LM Studio was enabled
- **LMSTUDIO_DOCKER_SETUP_COMPLETE.md** - Docker configuration details

---

## ✅ Final Status Summary

| Provider | Status | Type | Cost | Notes |
|----------|--------|------|------|-------|
| Chrome Lens | ✅ | Local | Free | Needs package |
| Google Vision | ⚠️ | Cloud | Paid | Needs credentials |
| Google Lens | ⚠️ | Cloud | Paid | Needs credentials |
| SerpAPI Lens | ⚠️ | Cloud | Paid | Needs API key |
| Tesseract | ✅ | Local | Free | Needs binary |
| EasyOCR | ✅ | Local | Free | Needs package |
| Azure Vision | ⚠️ | Cloud | Paid | Needs credentials |
| Ollama | ⚠️ | Server | Free | Needs server |
| vLLM | ❌ | Server | Free | Disabled by default |
| llama.cpp | ❌ | Server | Free | Disabled by default |
| Claude | ⚠️ | Cloud | Paid | Needs API key |
| **LM Studio** | **✅** | **Server** | **Free** | **Just enabled!** |

---

## 🚀 Next Actions

1. **Identify which providers you need**
2. **Read OCR_PROVIDER_DIAGNOSTIC_GUIDE.md for detailed setup**
3. **Follow the enable instructions for your chosen providers**
4. **Run check_ocr_provider_status.py to verify status**
5. **Test in bulk processing UI**

---

**Document Version**: 1.0
**Last Updated**: December 30, 2024
**Status**: Complete Reference
