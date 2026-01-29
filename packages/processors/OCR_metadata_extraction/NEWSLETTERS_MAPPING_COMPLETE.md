# Newsletters SMB Share Mapping - Configuration Complete

## Summary

The newsletters folder from the SMB share has been mapped to the backend, but with limitations due to GVFS/Docker compatibility.

## SMB Share Details

- **SMB Path**: `smb://172.12.0.49/dhamma_for_all/JPEG_Collection/06%20News%20Letters_NL`
- **Backend Path Prefix**: `newsletters/`
- **GVFS Mount Point**: `/run/user/1004/gvfs/smb-share:server=172.12.0.49,share=dhamma_for_all/JPEG_Collection/06 News Letters_NL`

## Configuration Applied

### 1. Environment Variables (`.env`)
```bash
NEWSLETTERS_PATH=/run/user/1004/gvfs/smb-share:server=172.12.0.49,share=dhamma_for_all/JPEG_Collection/06 News Letters_NL
```

### 2. Backend Code (`backend/app/routes/files.py`)
- Added path resolution for `newsletters/` prefix
- Maps `newsletters/subfolder/file.jpg` → `/run/user/1004/gvfs/smb-share:server=172.12.0.49,share=dhamma_for_all/JPEG_Collection/06 News Letters_NL/subfolder/file.jpg`
- Added security checks to allow GVFS paths

### 3. Docker Configuration
- Mounted `/run/user/1004/gvfs:/run/user/1004/gvfs:ro` (volume mount)
- Set `NEWSLETTERS_PATH` environment variable

## Current Limitation: Docker + GVFS Incompatibility

**Issue**: GVFS (GNOME Virtual File System) mounts are FUSE-based user-space mounts that are tied to the user's session. Docker containers cannot access these mounts even when bind-mounted because:

1. FUSE mounts require the same user context
2. Docker containers run in isolated namespaces
3. The GVFS daemon runs in the user session, not system-wide

### Verification
```bash
# On host - works ✓
ls "/run/user/1004/gvfs/smb-share:server=172.12.0.49,share=dhamma_for_all/JPEG_Collection/06 News Letters_NL"

# In Docker container - fails ✗
docker exec gvpocr-backend ls /run/user/1004/gvfs/
# ls: cannot access '/run/user/1004/gvfs/': No such file or directory
```

## Solutions

### Option 1: System-Wide CIFS Mount (Recommended)
Mount the SMB share system-wide so Docker can access it:

```bash
# Install cifs-utils if not installed
sudo apt-get install cifs-utils

# Create mount point
sudo mkdir -p /mnt/smb/newsletters

# Mount the share
sudo mount -t cifs "//172.12.0.49/dhamma_for_all/JPEG_Collection/06 News Letters_NL" \
  /mnt/smb/newsletters \
  -o guest,uid=1004,gid=1004,ro,vers=3.0

# Make it permanent in /etc/fstab
echo "//172.12.0.49/dhamma_for_all/JPEG_Collection/06 News Letters_NL /mnt/smb/newsletters cifs guest,uid=1004,gid=1004,ro,vers=3.0,_netdev 0 0" | sudo tee -a /etc/fstab
```

Then update `.env`:
```bash
NEWSLETTERS_PATH=/mnt/smb/newsletters
```

And update `docker-compose.yml` volume:
```yaml
volumes:
  - /mnt/smb/newsletters:/app/newsletters:ro
```

### Option 2: Use File Server HTTP Endpoint
The `file-server` container already serves files via HTTP at port 8010. You can access newsletters through:

```bash
http://localhost:8010/newsletters/01%20DHAMMA%20GIRI%20HINDI_VH/...
```

### Option 3: Run Backend on Host (Not in Docker)
If you run the backend directly on the host (not in Docker), it will have access to the GVFS mount and the current configuration will work.

## Testing

### Test File Access (when properly mounted):
```bash
# Via backend API
curl -X POST http://localhost:5000/api/files/download \
  -H "Content-Type: application/json" \
  -d '{"file_path": "newsletters/01 DHAMMA GIRI HINDI_VH/RSNLVHZZ002_NL_HI_IN_MH_IGP_1971/page1.jpg"}'
```

## Newsletter Folders Available

```
newsletters/
├── 01 DHAMMA GIRI HINDI_VH/
├── 02 DHAMMA GIRI ENGLISH_VE/
├── 03 DHAMMA GIRI MARATHI_VM/
├── 04 INTERNATIONAL ENGLISH_IE/
├── 05 JAIPUR HINDI_JH/
├── 06 HYDERABAD TELUGU_HT/
├── 07 CHENNAI TAMIL_CT/
├── 08 AHMEDABAD GUJATHI_AG/
├── 09 VARIOUS CENTERS NEWS LETTERS_VV/
├── 10_HAVYAKA_SANDESH/
├── 11_PRABUDDHA_MANAS/
├── Buddhist Vihara_BV/
├── HAMIRPUR_PATRIKA/
├── Inside_IS/
├── JPG SCAN 2019 VRID2PALANEW PROCESSING/
├── Notes/
├── RSNPVPZZ00_AARAM_SE/
├── RSNPVPZZ00_GYAN_DARSHAN/
├── RSNPVPZZ00_NAAGSEN/
├── SUNDAY_TIMES/
├── TOW_NEWSLETTER/
└── The Interaction_IA/
```

## Files Modified

1. `.env` - Added `NEWSLETTERS_PATH` variable
2. `docker-compose.yml` - Added `NEWSLETTERS_PATH` env var and GVFS volume mount
3. `backend/app/routes/files.py` - Added `newsletters/` path prefix support

## Next Steps

**To complete the setup**, you need to:

1. Choose one of the solutions above (Option 1 recommended)
2. For Option 1, run the mount commands with sudo password
3. Restart the backend container
4. Test file access through the API

## Current Status

✓ Backend code configured to handle `newsletters/` prefix
✓ Environment variables set
✓ Docker volume mount attempted
✗ GVFS mount not accessible from Docker (expected limitation)
⚠ Requires system-wide CIFS mount to work with Docker

---

**Date**: 2026-01-28
**SMB Server**: 172.12.0.49
**Share**: dhamma_for_all/JPEG_Collection/06 News Letters_NL
