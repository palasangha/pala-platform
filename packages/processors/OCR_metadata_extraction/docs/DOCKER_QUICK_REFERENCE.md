# 🚀 Docker Caching - Quick Reference

## TL;DR (Too Long; Didn't Read)

```bash
# One-time setup
export DOCKER_BUILDKIT=1

# Fast builds with cache (use this!)
./build.sh build

# That's it! Rebuilds will be 80-90% faster!
```

---

## One-Liner Builds

```bash
# Fast build with caching
DOCKER_BUILDKIT=1 docker compose down && docker compose up --build -d

# No cache (full rebuild)
DOCKER_BUILDKIT=1 docker compose build --no-cache && docker compose up -d

# Just build
DOCKER_BUILDKIT=1 docker compose build backend
```

---

## What Changed?

**Old:**
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt  # ❌ Downloads every time
```

**New:**
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt  # ✅ Caches packages
```

---

## Usage Examples

```bash
# First time (downloads all packages)
./build.sh build          # ~5-10 minutes

# Second time (uses cache)
./build.sh build          # ~30-60 seconds ✨

# Third time (everything cached)
./build.sh build          # ~5-10 seconds ⚡
```

---

## Commands

| Command | Purpose | Time |
|---------|---------|------|
| `./build.sh build` | Build with cache | 30 sec - 2 min |
| `./build.sh build-no-cache` | Full rebuild | 5-10 min |
| `./build.sh check` | Verify BuildKit | < 1 sec |
| `./build.sh cache-status` | View cache size | < 1 sec |
| `./build.sh clear-cache` | Delete cache | < 1 sec |

---

## Permanent Setup (Optional)

**File:** `~/.docker/daemon.json`
```json
{
  "features": {
    "buildkit": true
  }
}
```

Then restart Docker and use normally:
```bash
docker compose up --build -d
```

---

## Performance

- **First build:** 5-10 min (no change)
- **Rebuild:** 30 sec - 2 min (**80-90% faster!**)
- **Cache size:** ~500MB-1GB
- **Disk usage:** Minimal

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cache not used | `export DOCKER_BUILDKIT=1` |
| Still slow | `docker buildx prune` then rebuild |
| Need clean build | `./build.sh build-no-cache` |
| Verify setup | `./build.sh check` |

---

## Key Files

- `backend/Dockerfile` - Updated with cache mount
- `build.sh` - Automated build script
- `DOCKER_CACHING_GUIDE.md` - Detailed guide
- `DOCKER_SETUP_SUMMARY.md` - Full documentation

---

## That's It! 🎉

You're all set. Use `./build.sh build` and enjoy faster builds!
