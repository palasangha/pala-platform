# OCR Providers Setup Guide

This guide explains how to set up the different OCR providers for the Pala Platform.

## Overview

The OCR-Agent supports three OCR backends:

| Provider | Speed | Quality | Setup | Required |
|----------|-------|---------|-------|----------|
| **Tesseract** | Fast | Good | Pre-installed | ✅ Yes (fallback) |
| **Ollama** | Medium | Excellent | Manual setup | ❌ Optional |
| **LM Studio** | Medium | Excellent | Manual setup | ❌ Optional |

- **Tesseract**: CPU-based, built-in, works offline, good for documents
- **Ollama**: Local AI models, excellent for handwritten text and complex images
- **LM Studio**: Desktop GUI for running local vision models, more user-friendly

## Quick Start

```bash
# 1. Check what's installed and guide setup
./setup-ocr-providers.sh

# 2. Start the development stack (includes OCR-Agent)
./start-dev.sh

# 3. Go to http://localhost:3001 and test OCR in Document Processing tab
```

## Detailed Setup

### 1. Tesseract OCR (Already Included)

Tesseract is included via the Python `pytesseract` package and is the default fallback provider.

#### Verify Installation

```bash
# Check if tesseract is installed
tesseract --version
```

#### Install if Missing

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

**Verification:**
```bash
# Should return version info
tesseract --version
```

---

### 2. Ollama Setup (Optional - Recommended for Best Quality)

Ollama runs local vision models. It's excellent for OCR on handwritten text and complex images.

#### Installation

1. **Download Ollama** from https://ollama.ai

2. **Install** following platform-specific instructions

3. **Start Ollama Server** (in a separate terminal):
   ```bash
   ollama serve
   ```
   - Server listens on `http://localhost:11434`
   - Keep this terminal open while using OCR

4. **Pull a Vision Model** (in another terminal):
   ```bash
   # Option 1: Lightweight (recommended)
   ollama pull minicpm-v
   
   # Option 2: Alternative compact model
   ollama pull bakllava
   ```

5. **Verify** the model is installed:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   - Should return JSON with your model listed

#### Usage

When you select "Ollama" in the Dashboard:
- OCR-Agent will automatically use the installed vision model
- First request may take longer (model loading)
- Subsequent requests are faster

#### Troubleshooting

**Problem: Ollama service not responding**
```bash
# Check if running
lsof -i :11434

# Restart
pkill ollama
ollama serve
```

**Problem: Vision model not found**
```bash
# List installed models
ollama list

# Pull again
ollama pull minicpm-v
```

**Problem: Port 11434 in use**
```bash
# Find process using port
lsof -i :11434

# Kill it
kill -9 <PID>

# Restart Ollama
ollama serve
```

---

### 3. LM Studio Setup (Optional - User-Friendly)

LM Studio is a desktop application with a built-in local server for vision models.

#### Installation

1. **Download LM Studio** from https://lmstudio.ai

2. **Install** following the installer

3. **Launch LM Studio** (GUI application)

4. **Select a Vision Model**:
   - Go to the "Local Server" tab (or similar)
   - Search for vision models: "llava", "bakllava", "minicpm"
   - Download a model (first time only, ~5-10 GB)

5. **Start Local Server**:
   - Click "Start Server" button
   - Default endpoint: `http://localhost:1234`
   - Server runs in background until you stop it

6. **Verify** the server is running:
   ```bash
   curl http://localhost:1234/v1/models
   ```
   - Should return JSON with available models

#### Usage

When you select "LM Studio" in the Dashboard:
- OCR-Agent will automatically use the running local server
- Make sure LM Studio server is running before testing

#### Troubleshooting

**Problem: LM Studio server not responding**
- Verify LM Studio window shows "Server running"
- Check that you clicked "Start Server" button
- Try restarting LM Studio

**Problem: Port 1234 in use**
```bash
# Find process
lsof -i :1234

# Kill it
kill -9 <PID>

# Restart LM Studio
```

**Problem: No models available**
- Download a model in LM Studio: Search → Select → Download
- Wait for download to complete
- Then start server

---

## Testing the Setup

### Test Single-File OCR

1. Start development stack:
   ```bash
   ./start-dev.sh
   ```

2. Open Dashboard: http://localhost:3001

3. Go to **Document Processing** tab

4. In the **Upload step**:
   - Select OCR provider (dropdown)
   - Upload an image (JPG, PNG, PDF)
   - Click "Upload & Run OCR with {provider}"

5. **Results**:
   - Check OCR step for extracted text
   - Verify provider name is displayed
   - Check `logs/ocr-agent.log` for details

### Test Batch Processing

1. Create a folder with multiple images:
   ```bash
   mkdir -p /tmp/test-images
   # Add JPG/PNG files to this folder
   ```

2. Go to **Batch OCR** tab (new tab in Document Processing workflow)

3. Enter folder path and select provider

4. Click "Process Folder"

5. Watch real-time progress as files are processed

---

## Performance Notes

### Speed Comparison

- **Tesseract**: ~50-100ms per image (fast)
- **Ollama**: ~200-500ms per image (medium)
- **LM Studio**: ~200-500ms per image (medium)

First request with Ollama/LM Studio may be slower due to model initialization.

### Quality Comparison

- **Tesseract**: Good for printed documents, average on handwriting
- **Ollama**: Excellent for handwriting, complex layouts, images with text
- **LM Studio**: Same as Ollama (uses same models), more user-friendly setup

### Recommendations

- **Documents only**: Use Tesseract (no setup needed)
- **Mixed content**: Use Ollama or LM Studio (better quality)
- **Handwritten text**: Prefer Ollama or LM Studio with minicpm-v model
- **Large batch**: Use Tesseract for speed, or Ollama/LM Studio for quality

---

## Monitoring

### Check OCR Agent Status

```bash
# View real-time logs
tail -f logs/ocr-agent.log

# View recent errors
tail -20 logs/ocr-agent.log
```

### Check Provider Health

```bash
# Tesseract (installed check)
tesseract --version

# Ollama
curl http://localhost:11434/api/tags

# LM Studio
curl http://localhost:1234/v1/models
```

### Jobs and Results

OCR jobs are stored in:
```
packages/agents/ocr-agent/data/jobs/
```

Each job has:
- Job ID (unique identifier)
- Status (pending, processing, completed, failed)
- Per-file results with extracted text
- Provider used
- Timestamps

---

## Fallback Behavior

If the MCP OCR-Agent is not available:
- Dashboard falls back to browser-based Tesseract.js
- Only works for single files (no batch processing)
- No provider selection available
- Warning displayed in UI

To restore MCP OCR-Agent:
```bash
# Make sure start-dev.sh is running
./start-dev.sh

# Check OCR-Agent is running
curl ws://localhost:3000/tools | grep ocr
```

---

## FAQ

**Q: Do I need all three providers?**  
A: No. Tesseract works offline without any setup. Ollama and LM Studio are optional for better quality.

**Q: Can I use Tesseract alone?**  
A: Yes. It's the default fallback. Tesseract provides good quality for most documents.

**Q: Why is my OCR slow?**  
A: First request loads the model into memory. Subsequent requests are faster. Use Tesseract if speed is critical.

**Q: Can I run Ollama and LM Studio together?**  
A: Yes, but they'll use different ports (11434 and 1234). Dashboard lets you select which one to use.

**Q: What if I update the providers after start-dev.sh is running?**  
A: Restart the OCR-Agent. The MCP server will auto-discover updated provider availability.

**Q: How do I remove a provider?**  
A: Just uninstall it. The OCR-Agent will gracefully fall back to other available providers.

---

## Getting Help

If you encounter issues:

1. **Check logs**:
   ```bash
   tail -f logs/ocr-agent.log
   tail -f logs/mcp-server.log
   ```

2. **Run setup script**:
   ```bash
   ./setup-ocr-providers.sh
   ```

3. **Verify provider is running**:
   - Tesseract: `tesseract --version`
   - Ollama: `curl http://localhost:11434/api/tags`
   - LM Studio: `curl http://localhost:1234/v1/models`

4. **Check MCP connection**:
   - Dashboard should show connected agents
   - Look for "OCR-Agent" in agent list
