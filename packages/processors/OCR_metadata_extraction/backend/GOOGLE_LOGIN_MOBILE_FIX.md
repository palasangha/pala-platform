# Google Login Issue on Mobile - Troubleshooting Guide

## Problem

Google OAuth login fails when accessing GVPOCR from mobile devices.

## Root Causes

### 1. **Missing/Invalid Google OAuth Credentials**

The `.env` file contains placeholder values:
```env
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
```

### 2. **Redirect URI Mismatch**

Current configuration:
```env
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

This only works for desktop/localhost access. Mobile devices cannot access `localhost`.

### 3. **CORS Configuration**

Current CORS setting:
```env
CORS_ORIGINS=http://localhost:5173
```

This blocks requests from mobile IP addresses.

---

## Solution

### Step 1: Set Up Google OAuth Credentials

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create or Select a Project**
   - Click on project dropdown → "New Project"
   - Name it "GVPOCR" or similar

3. **Enable Google+ API**
   - Navigation menu → "APIs & Services" → "Library"
   - Search for "Google+ API"
   - Click "Enable"

4. **Create OAuth 2.0 Credentials**
   - Navigation menu → "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: **Web application**
   - Name: "GVPOCR Web Client"

5. **Configure Authorized Origins and Redirect URIs**

   **For Mobile Access (Required):**

   Get your server's actual IP address:
   ```bash
   hostname -I
   ```

   Current server IPs: `172.12.0.132`, `10.10.0.179`

   **Authorized JavaScript origins:**
   ```
   http://localhost:3000
   http://localhost:5173
   http://172.12.0.132:3000
   http://172.12.0.132:5173
   http://10.10.0.179:3000
   http://10.10.0.179:5173
   ```

   **Authorized redirect URIs:**
   ```
   http://localhost:5000/api/auth/google/callback
   http://172.12.0.132:5000/api/auth/google/callback
   http://10.10.0.179:5000/api/auth/google/callback
   ```

6. **Copy Credentials**
   - After creating, you'll see:
     - Client ID: `xxxxx.apps.googleusercontent.com`
     - Client Secret: `GOCSPX-xxxxx`

---

### Step 2: Update Environment Variables

Edit `/mnt/sda1/mango1_home/gvpocr/backend/.env`:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-actual-client-secret

# For mobile access, use server IP instead of localhost
# Use the IP accessible from your mobile network (e.g., 10.10.0.179)
GOOGLE_REDIRECT_URI=http://10.10.0.179:5000/api/auth/google/callback

# CORS - Allow mobile access
CORS_ORIGINS=http://localhost:5173,http://172.12.0.132:3000,http://10.10.0.179:3000
```

**Important:** Replace `your-actual-client-id` and `your-actual-client-secret` with the credentials from Google Cloud Console.

---

### Step 3: Update Frontend Configuration

If your frontend has hardcoded API URLs, update them to use the server IP:

**For mobile access:**
```javascript
// Use dynamic API URL based on access method
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:5000/api'
  : `http://${window.location.hostname}:5000/api`;
```

---

### Step 4: Restart Services

```bash
cd /mnt/sda1/mango1_home/gvpocr
docker-compose restart backend frontend
```

---

## Testing

### Test from Desktop

1. Open browser: `http://localhost:3000`
2. Click "Sign in with Google"
3. Should redirect to Google login
4. After login, redirects back with tokens

### Test from Mobile

1. **Ensure mobile is on same network as server**
2. Find server IP accessible from mobile:
   ```bash
   # On server, check IPs
   ip addr show | grep "inet "
   ```
   Common IPs for local network: `192.168.x.x` or `10.x.x.x`

3. Open mobile browser: `http://10.10.0.179:3000` (use your actual IP)
4. Click "Sign in with Google"
5. Should work now!

---

## Common Issues and Fixes

### Issue 1: "redirect_uri_mismatch" Error

**Error Message:**
```
Error 400: redirect_uri_mismatch
The redirect URI in the request does not match the authorized redirect URIs
```

**Fix:**
- Check the redirect URI in Google Cloud Console matches exactly
- Case-sensitive, must include `http://` or `https://`
- Cannot use IP addresses in production (use domain names)

### Issue 2: "Access blocked: This app's request is invalid"

**Cause:** OAuth consent screen not configured

**Fix:**
1. Google Cloud Console → "APIs & Services" → "OAuth consent screen"
2. Choose "External" (for testing) or "Internal" (if using Google Workspace)
3. Fill in required fields:
   - App name: "GVPOCR"
   - User support email: your email
   - Developer contact: your email
4. Save and continue
5. Add scopes (if needed): `email`, `profile`, `openid`
6. Add test users if using "External" mode

### Issue 3: Mobile Can't Connect

**Possible Causes:**
1. Mobile not on same network as server
2. Firewall blocking port 3000 or 5000
3. Using wrong IP address

**Fix:**
```bash
# Check firewall (Ubuntu/Debian)
sudo ufw status

# Allow ports if blocked
sudo ufw allow 3000
sudo ufw allow 5000
```

### Issue 4: CORS Error on Mobile

**Error in browser console:**
```
Access to fetch at 'http://10.10.0.179:5000/api/auth/google' from origin
'http://10.10.0.179:3000' has been blocked by CORS policy
```

**Fix:**
Update `CORS_ORIGINS` in `.env`:
```env
CORS_ORIGINS=http://localhost:5173,http://10.10.0.179:3000
```

Restart backend:
```bash
docker-compose restart backend
```

---

## Security Considerations

### For Development

Current setup uses HTTP, which is fine for:
- Local network testing
- Development environment
- Internal networks

### For Production

**Use HTTPS with valid SSL certificate:**

1. **Get a domain name**
   - Example: `gvpocr.yourdomain.com`

2. **Get SSL certificate**
   - Use Let's Encrypt (free): https://letsencrypt.org/
   - Or use Cloudflare (free tier includes SSL)

3. **Update redirect URIs**
   ```
   https://gvpocr.yourdomain.com/api/auth/google/callback
   ```

4. **Update environment variables**
   ```env
   GOOGLE_REDIRECT_URI=https://gvpocr.yourdomain.com/api/auth/google/callback
   CORS_ORIGINS=https://gvpocr.yourdomain.com
   ```

5. **Configure reverse proxy (nginx/traefik)**
   ```nginx
   server {
       listen 443 ssl;
       server_name gvpocr.yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:3000;
       }

       location /api {
           proxy_pass http://localhost:5000;
       }
   }
   ```

---

## Verification Checklist

Before testing mobile login, verify:

- [ ] Google OAuth credentials created in Cloud Console
- [ ] Redirect URI added to Google Cloud Console
- [ ] `.env` file updated with real credentials
- [ ] `GOOGLE_REDIRECT_URI` uses server IP (not localhost)
- [ ] `CORS_ORIGINS` includes server IP
- [ ] Backend restarted after `.env` changes
- [ ] Mobile device on same network as server
- [ ] Can access frontend from mobile browser
- [ ] Firewall allows ports 3000 and 5000

---

## Current Configuration

### Backend Configuration

**File:** [app/config.py](app/config.py#L30-L33)
```python
# Google OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI',
    'http://localhost:5000/api/auth/google/callback')
```

### Auth Routes

**File:** [app/routes/auth.py](app/routes/auth.py)

**Login Flow:**
1. Frontend calls `GET /api/auth/google`
2. Backend returns Google authorization URL
3. User redirects to Google login
4. Google redirects back to `GOOGLE_REDIRECT_URI` with code
5. Backend exchanges code for token
6. Backend gets user info from Google
7. Backend creates/updates user in database
8. Backend creates JWT tokens
9. Backend redirects to frontend with tokens

**Endpoints:**
- `GET /api/auth/google` - Get Google auth URL
- `GET /api/auth/google/callback` - Handle Google callback
- `POST /api/auth/refresh` - Refresh access token

---

## Network Discovery

### Find Server IP for Mobile Access

**From server:**
```bash
# Get all IP addresses
hostname -I

# Or more detailed
ip addr show | grep "inet " | grep -v "127.0.0.1"
```

**From mobile:**
1. Connect to same WiFi as server
2. Check WiFi settings for network range (e.g., 192.168.1.x)
3. Try server IPs in that range

**Test connectivity from mobile:**
```bash
# On server, start simple HTTP server
python3 -m http.server 8000

# On mobile browser
http://YOUR_SERVER_IP:8000
```

---

## Logs and Debugging

### Enable Verbose Logging

**Backend logs:**
```bash
# Follow backend logs in real-time
docker-compose logs -f backend | grep -i "google\|oauth\|auth"
```

### Common Log Messages

**Successful login:**
```
172.x.x.x - - [27/Nov/2025 06:00:00] "GET /api/auth/google HTTP/1.1" 200 -
172.x.x.x - - [27/Nov/2025 06:00:05] "GET /api/auth/google/callback?code=... HTTP/1.1" 302 -
```

**Failed login (missing credentials):**
```
Error: GOOGLE_CLIENT_ID not configured
```

**Redirect URI mismatch:**
```
Error: redirect_uri_mismatch
```

---

## Quick Fix Commands

```bash
# 1. Check current environment variables
cd /mnt/sda1/mango1_home/gvpocr/backend
grep "GOOGLE" .env

# 2. Edit .env file
nano .env
# Update GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI

# 3. Restart services
cd /mnt/sda1/mango1_home/gvpocr
docker-compose restart backend frontend

# 4. Test from desktop
curl http://localhost:5000/api/auth/google

# 5. Check logs
docker-compose logs -f backend
```

---

## Alternative: Using ngrok for Mobile Testing

If you can't configure network access, use ngrok:

```bash
# Install ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Expose frontend
ngrok http 3000

# You'll get a URL like: https://abc123.ngrok.io
```

**Update .env:**
```env
GOOGLE_REDIRECT_URI=https://abc123.ngrok.io/api/auth/google/callback
CORS_ORIGINS=https://abc123.ngrok.io
```

**Update Google Cloud Console:**
- Add redirect URI: `https://abc123.ngrok.io/api/auth/google/callback`

**Access from mobile:**
- Open: `https://abc123.ngrok.io`

---

## Summary

The Google login failure on mobile is due to:

1. ❌ **Placeholder OAuth credentials** - Need real Google Cloud credentials
2. ❌ **localhost redirect URI** - Mobile can't access localhost
3. ❌ **CORS restrictions** - Frontend origin not allowed

**To fix:**
1. ✅ Create Google OAuth credentials in Cloud Console
2. ✅ Add server IP-based redirect URIs
3. ✅ Update `.env` with real credentials and server IP
4. ✅ Update CORS to allow mobile access
5. ✅ Restart backend and frontend
6. ✅ Test from mobile using server IP

After these steps, Google login will work from both desktop and mobile devices on the same network.
