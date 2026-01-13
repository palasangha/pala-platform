# 🚀 Docker BuildKit Caching Guide

## Overview

Your Docker setup now uses **BuildKit caching** to avoid re-downloading pip packages on every build. This can reduce build time from **5-15 minutes** down to **30 seconds** for subsequent builds!

---

## ✨ What Changed

### Before (Old Dockerfile)
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```
❌ Problem: `--no-cache-dir` removes the pip cache, forcing re-download every build

### After (New Dockerfile)
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```
✅ Benefits:
- Pip cache persists between builds
- BuildKit manages the cache automatically
- Only new/changed packages are downloaded

---

## 🎯 How to Use

### 1. Enable BuildKit (One-time setup)

**On Linux/Mac:**
```bash
export DOCKER_BUILDKIT=1
```

**On Windows (PowerShell):**
```powershell
$env:DOCKER_BUILDKIT=1
```

**Permanently (Linux/Mac):**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
source ~/.bashrc
```

**Permanently (Docker Config):**
Create or edit `~/.docker/daemon.json`:
```json
{
  "features": {
    "buildkit": true
  }
}
```

### 2. Build with Caching

```bash
# First build (downloads all packages)
docker compose up --build -d

# Second build (uses cache - much faster!)
docker compose down
docker compose up --build -d

# Subsequent builds (even faster!)
docker compose down
docker compose up --build -d
```

### 3. Force Full Rebuild (Clear Cache)

If you need a fresh build without cache:

```bash
# Option 1: Build without cache
docker compose build --no-cache

# Option 2: Prune everything and rebuild
docker system prune -a
docker compose up --build -d
```

---

## 📊 Performance Comparison

| Scenario | Old (no-cache-dir) | New (BuildKit) |
|----------|---|---|
| **First build** | 5-10 min | 5-10 min |
| **Rebuild (same requirements)** | 5-10 min | 30-60 sec |
| **Add one package** | 5-10 min | 1-2 min |
| **No changes** | 5-10 min | 5-10 sec |

---

## 🔧 Verify BuildKit is Working

```bash
# Check if BuildKit is enabled
docker buildx version

# Build and watch the output
DOCKER_BUILDKIT=1 docker compose build --progress=plain backend

# You should see:
# => [backend 4/7] RUN --mount=type=cache...
```

---

## 📁 Cache Location

BuildKit stores cache in:
- **Linux**: `/var/lib/docker/buildx`
- **Docker Desktop (Mac/Windows)**: Managed by Docker Desktop VM

The cache is **persistent** across builds unless you:
- Run `docker system prune`
- Clear BuildKit cache with `docker buildx prune`

---

## 💡 Tips & Tricks

### 1. Check Cache Status
```bash
# See all BuildKit caches
docker buildx du

# Prune unused caches
docker buildx prune
```

### 2. Environment Variable Method

As an alternative to setting env var, add to your build command:
```bash
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

### 3. Multi-Stage Builds (Optional)

For even faster builds with multiple services, use BuildKit's multi-stage cache:

```dockerfile
# Stage 1: Dependencies
FROM python:3.11-slim AS dependencies
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Stage 2: Application
FROM python:3.11-slim
WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
EXPOSE 5000
CMD ["python", "run.py"]
```

This approach:
- Separates dependency layer from application code
- Each layer caches independently
- Makes rebuilds even faster

---

## ✅ Quick Start Checklist

- [ ] Enable BuildKit: `export DOCKER_BUILDKIT=1`
- [ ] Verify Dockerfile uses `RUN --mount=type=cache`
- [ ] Build once: `docker compose up --build -d`
- [ ] Make a change and rebuild: `docker compose down && docker compose up --build -d`
- [ ] Notice the speed improvement! 🎉

---

## 🐛 Troubleshooting

### Issue: BuildKit not being used

**Solution:**
```bash
# Verify BuildKit is enabled
docker buildx version

# If not available, enable it:
docker buildx create --use
docker buildx inspect --bootstrap
```

### Issue: Cache not being used (still downloads packages)

**Solution:**
```bash
# Make sure BuildKit is enabled
export DOCKER_BUILDKIT=1

# Rebuild with progress to see cache usage
docker compose build --progress=plain backend

# Look for:
# CACHED [backend 4/7] COPY requirements.txt
# => [backend 5/7] RUN --mount=type=cache pip install -r requirements.txt
```

### Issue: Need to clear cache but keep image

**Solution:**
```bash
# Clear only BuildKit cache
docker buildx prune

# Keep images, just clear build cache
docker buildx prune --all
```

---

## 📚 Additional Resources

- [Docker BuildKit Documentation](https://docs.docker.com/build/buildkit/)
- [Docker Caching Best Practices](https://docs.docker.com/build/cache/)
- [RUN mount options](https://docs.docker.com/engine/reference/builder/#run---mount)

---

## 🎯 Current Setup Summary

✅ **Already Configured:**
- Copy `requirements.txt` before application code
- Use BuildKit cache mount for pip packages
- Proper `.dockerignore` to reduce build context

✅ **Ready to Use:**
```bash
# Just enable BuildKit and build
export DOCKER_BUILDKIT=1
docker compose up --build -d
```

That's it! Your builds will be **much faster** now! 🚀
