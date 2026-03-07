# LM Studio Disabled in Frontend - Root Cause Analysis & Fix

**Date**: December 30, 2024
**Issue**: LM Studio appears as "(Disabled)" in bulk processing UI dropdown
**Status**: ✅ **ROOT CAUSE IDENTIFIED** | 🔧 **FIX REQUIRED**

---

## Executive Summary

LM Studio is showing as disabled in the frontend **NOT because of configuration issues** but because:

**The backend container cannot reach LM Studio server at `localhost:1234`**

When the Docker backend container tries to connect to `localhost:1234`, it's trying to connect to the backend container's own localhost, not the host machine's localhost where LM Studio is actually running.

---

## Root Cause Analysis

### The Problem Chain

```
Backend Container Starting
    ↓
LMStudioProvider.__init__() called
    ↓
Configuration: LMSTUDIO_ENABLED=true ✅ (from .env)
    ↓
Configuration: LMSTUDIO_HOST=http://localhost:1234 ✅ (from .env)
    ↓
Provider runs: self._check_availability()
    ↓
Attempts: requests.get("http://localhost:1234/v1/models", timeout=5)
    ↓
❌ CONNECTION ERROR: "Failed to establish a new connection: [Errno 111] Connection refused"
    ↓
sets: self._available = False
    ↓
Backend API returns: {"available": false}
    ↓
Frontend renders: "LM Studio (Disabled)"
```

### Error Details from Backend Logs

```
Connection error while checking LM Studio at http://localhost:1234:
HTTPConnectionPool(host='localhost', port=1234):
  Max retries exceeded with url: /v1/models
  (Caused by NewConnectionError("HTTPConnection(host='localhost', port=1234):
    Failed to establish a new connection: [Errno 111] Connection refused"))
```

**[Errno 111]** = Connection Refused = Port not listening on that address

---

## Why This Happens

### Docker Network Isolation

When the backend container is running, `localhost` refers to **the container's network namespace**, not the host machine.

```
Host Machine (your computer)
├── LM Studio running at: localhost:1234 ✅
└── Docker Network
    └── Backend Container
        └── localhost:1234 → Backend container's own localhost ❌
            (NOT the host's localhost)
```

### Configuration is Correct But Unreachable

Your `.env` file is correct:
```bash
LMSTUDIO_ENABLED=true           ✅ Provider is enabled
LMSTUDIO_HOST=http://localhost:1234  ✅ Configuration is set
LMSTUDIO_MODEL=gemma3-12b-vision     ✅ Model is configured
LMSTUDIO_API_KEY=lm-studio      ✅ API key is set
```

But from **inside the Docker container**, `localhost:1234` doesn't exist.

---

## Quick Status Check

**What's actually happening:**

```
✅ LM Studio server IS running (verified: curl http://localhost:1234/v1/models works from host)
✅ LMSTUDIO_ENABLED=true (configured in .env)
✅ LMSTUDIO_HOST is set correctly (configured in .env)
❌ Backend container CANNOT reach it (network isolation issue)
❌ Provider availability check FAILS (returns available=false)
❌ Frontend displays "(Disabled)" (because API says available=false)
```

---

## Solution Options

### Option 1: Use Docker Host Network (Easiest but Less Secure)

Make the backend container use the host's network:

```bash
# Edit docker-compose.yml
backend:
  network_mode: "host"  # Add this line
```

Then LM Studio will be reachable at `localhost:1234`.

**Pros**: Simple, LM Studio connection works immediately
**Cons**: Reduces container isolation, all ports exposed to host network

---

### Option 2: Use Docker Service Name (Recommended for Production)

If LM Studio were running in Docker, reference it by service name. But since it's on the host:

Set the address to the Docker host gateway:

```bash
# In .env
LMSTUDIO_HOST=http://host.docker.internal:1234
```

**Why this works**: Docker provides `host.docker.internal` to reach the host machine
**Pros**: More secure, standard Docker practice
**Cons**: Requires updating .env

---

### Option 3: Run LM Studio in Docker (If Applicable)

If you can containerize LM Studio, run it as a Docker service:

```yaml
# In docker-compose.yml
lmstudio:
  image: your-lmstudio-image
  ports:
    - "1234:1234"
  networks:
    - your-network

backend:
  depends_on:
    - lmstudio
  environment:
    LMSTUDIO_HOST: http://lmstudio:1234  # Service name
```

Then reference by service name in .env:

```bash
LMSTUDIO_HOST=http://lmstudio:1234
```

---

## Implementation: Option 2 (Recommended)

### Step 1: Update .env File

Edit `/mnt/sda1/mango1_home/gvpocr/.env` and change:

```bash
# OLD:
LMSTUDIO_HOST=http://localhost:1234

# NEW:
LMSTUDIO_HOST=http://host.docker.internal:1234
```

### Step 2: Restart Backend Container

```bash
docker-compose restart backend
```

Wait 5 seconds for it to start up.

### Step 3: Verify the Fix

Check if LM Studio is now available:

```bash
docker-compose exec -T backend python3 << 'EOF'
from app import create_app
from app.services.ocr_service import OCRService

app = create_app()
with app.app_context():
    service = OCRService()
    providers = service.get_available_providers()
    lmstudio = [p for p in providers if p['name'] == 'lmstudio'][0]
    print(f"LM Studio Available: {lmstudio['available']}")

    if lmstudio['available']:
        print("✅ SUCCESS! LM Studio is now available")
    else:
        print("❌ Still not available - check if LM Studio is running on host")
EOF
```

### Step 4: Check Frontend

Refresh your browser and open the bulk processing UI. LM Studio should now appear as **enabled** (not disabled).

---

## Implementation: Option 1 (Simpler but Less Secure)

If Option 2 doesn't work (older Docker versions), try:

### Step 1: Update docker-compose.yml

```yaml
services:
  backend:
    network_mode: "host"
    # ... rest of config
```

### Step 2: Restart Docker Compose

```bash
docker-compose down
docker-compose up -d
```

### Step 3: Verify

```bash
docker-compose exec -T backend curl http://localhost:1234/v1/models
```

---

## Verification Checklist

After applying the fix:

- [ ] Backend container is running: `docker-compose ps | grep backend`
- [ ] LM Studio is running on host: `curl http://localhost:1234/v1/models`
- [ ] Backend can reach it: `docker-compose exec -T backend curl http://host.docker.internal:1234/v1/models`
- [ ] Provider shows available: Check API returns `"available": true`
- [ ] Frontend shows enabled: Refresh browser, LM Studio not marked "(Disabled)"
- [ ] Can select in UI: Dropdown shows "LM Studio (Local LLM)" without disabled state

---

## Architecture Diagram

### Before Fix (Current - Not Working)

```
Host Machine
├── LM Studio: localhost:1234 ✅
│
├─→ Docker Network
    └─→ Backend Container
        ├─ Tries: http://localhost:1234 ❌
        │  (Inside container, localhost ≠ host's localhost)
        │
        └─ Result: Connection Refused
           └─ Provider marked unavailable
              └─ Frontend shows "(Disabled)"
```

### After Fix (Option 2 - Working)

```
Host Machine
├── LM Studio: localhost:1234 ✅
│   (Also accessible as: host.docker.internal:1234)
│
├─→ Docker Network
    └─→ Backend Container
        ├─ Tries: http://host.docker.internal:1234 ✅
        │  (Docker gateway alias for host)
        │
        └─ Result: Connection Successful ✅
           └─ Provider marked available
              └─ Frontend shows "LM Studio (Local LLM)"
```

---

## Technical Details

### How the Availability Check Works

`backend/app/services/ocr_providers/lmstudio_provider.py:63-95`

```python
def _check_availability(self):
    """Check if LM Studio API server is available"""
    try:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # This is where it fails - tries to connect to localhost
        response = requests.get(
            f"{self.host}/v1/models",  # self.host = "http://localhost:1234"
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            return True  # Available
        else:
            return False  # Server error

    except requests.exceptions.ConnectionError as e:
        # THIS IS WHAT WE'RE HITTING
        # "Failed to establish a new connection: [Errno 111] Connection refused"
        logger.error(f"Connection error: {e}")
        return False  # Not available
```

### Provider Initialization Flow

`backend/app/services/ocr_service.py:35`

```python
self.providers = {
    # ... other providers ...
    'lmstudio': LMStudioProvider()  # Called during service init
}
```

When `LMStudioProvider()` is created:
1. Reads `LMSTUDIO_ENABLED` from environment (✅ true)
2. Reads `LMSTUDIO_HOST` from environment (✅ localhost:1234)
3. Calls `_check_availability()` to test the connection
4. Sets `self._available = result` (❌ false due to connection error)

Later, when frontend requests providers:

```python
def get_available_providers(self):
    available = []
    for name, provider in self.providers.items():
        available.append({
            'name': name,
            'available': provider.is_available(),  # Returns False
            'display_name': self._get_display_name(name)
        })
    return available
```

The `available: false` is sent to frontend, which renders it as disabled.

---

## Why This Wasn't Obvious

1. **Configuration appears correct** - LMSTUDIO_ENABLED is true in .env ✅
2. **Environment variables loaded properly** - Backend reads them correctly ✅
3. **LM Studio IS running** - curl from host works fine ✅
4. **But network isolation prevents connection** - Docker container can't reach host ❌

It looks like a configuration problem but it's actually a **networking problem**.

---

## What NOT To Do

❌ **Don't change** `LMSTUDIO_ENABLED` - it's already true
❌ **Don't change** `LMSTUDIO_TIMEOUT` - that's not the issue
❌ **Don't restart** the backend without fixing the host reference
❌ **Don't reinstall** LM Studio - it's already working

The issue is the **connection address**, not the configuration or the service.

---

## Summary

| Aspect | Status | Note |
|--------|--------|------|
| LM Studio running | ✅ | `curl localhost:1234/v1/models` works from host |
| LMSTUDIO_ENABLED | ✅ | Set to `true` in .env |
| LMSTUDIO_HOST configured | ✅ | Set in .env |
| Backend config loads | ✅ | Environment variables read correctly |
| Backend → LM Studio connection | ❌ | **Can't reach `localhost:1234` from container** |
| Provider available flag | ❌ | Returns `false` due to connection error |
| Frontend displays | ❌ | Shows "(Disabled)" because available=false |

---

## Next Steps

1. **Choose a solution** (Option 1 or Option 2)
2. **Apply the fix** (change .env or docker-compose.yml)
3. **Restart backend** (`docker-compose restart backend`)
4. **Verify** (run the Python verification script)
5. **Test UI** (refresh browser, select LM Studio in bulk processing)

---

## Reference Documentation

- **LMStudioProvider code**: `backend/app/services/ocr_providers/lmstudio_provider.py:63`
- **Availability check**: `backend/app/services/ocr_service.py:81`
- **API endpoint**: `backend/app/routes/ocr.py:18`
- **Docker networking**: [Docker networking docs](https://docs.docker.com/engine/reference/commandline/run/#network)
- **host.docker.internal**: [Docker desktop feature](https://docs.docker.com/desktop/features/networking/)

---

**Created**: December 30, 2024
**Diagnosis**: Root cause identified - Docker network isolation
**Status**: Ready for implementation
**Recommended Solution**: Option 2 (host.docker.internal)
