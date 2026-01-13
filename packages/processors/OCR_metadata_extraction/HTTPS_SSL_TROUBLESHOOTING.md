# HTTPS/SSL Troubleshooting Guide

## Error: net::ERR_NETWORK_CHANGED with Archipelago Uploads

This error typically indicates SSL/HTTPS-related issues when uploading to Archipelago.

## Root Causes

### 1. **SSL Certificate Verification Failure**
The Python `requests` library fails to verify Archipelago's SSL certificate.

**Solution:**
```python
# Add to ami_service.py
self.session = requests.Session()
self.session.verify = False  # Disable SSL verification (dev only!)
# OR use proper certificate path
# self.session.verify = '/path/to/ca-bundle.crt'
```

### 2. **Mixed HTTP/HTTPS Content**
Frontend running on HTTPS, backend API on HTTP.

**Solution:**
- Ensure both frontend and backend use same protocol (both HTTPS or both HTTP)
- Check `ARCHIPELAGO_BASE_URL` - must match frontend protocol

### 3. **Self-Signed Certificates**
Archipelago using self-signed cert without proper trust.

**Solution:**
```bash
# Export certificate from Archipelago server
openssl s_client -connect archipelago.example.com:443 -showcerts < /dev/null | openssl x509 -outform PEM > archipelago.crt

# Use in Python
import certifi
import requests

# Create session with certificate
session = requests.Session()
session.verify = '/path/to/archipelago.crt'
```

### 4. **CORS/Network Proxy Issues**
Network proxy (corporate/VPN) intercepting HTTPS.

**Solution:**
- Check proxy settings
- May need to disable cert verification in dev

## Debugging Steps

### Step 1: Check Browser Console
```javascript
// Look for:
// - Failed to fetch errors
// - Mixed content warnings
// - Certificate errors
```

### Step 2: Check Backend Logs
```bash
# Look for:
# - SSLError
# - Certificate verification failed
# - Connection refused

tail -f logs/app.log | grep -i "ssl\|certificate\|connection"
```

### Step 3: Test Archipelago Connection
```bash
# From backend server
curl -k https://your-archipelago.com/  # -k ignores cert verification

# Or with certificate
curl --cacert /path/to/cert.crt https://your-archipelago.com/
```

### Step 4: Check Environment Variables
```bash
# Required
ARCHIPELAGO_BASE_URL=https://your-archipelago.com
ARCHIPELAGO_USERNAME=admin
ARCHIPELAGO_PASSWORD=password

# Optional (for dev)
ARCHIPELAGO_VERIFY_SSL=false  # NOT recommended for production!
```

## Solutions by Scenario

### Scenario A: Development with Self-Signed Cert
```python
# In ami_service.py __init__
import os

# Get SSL verification setting from environment
verify_ssl = os.getenv('ARCHIPELAGO_VERIFY_SSL', 'true').lower() == 'true'
self.session = requests.Session()
self.session.verify = verify_ssl  # False for self-signed in dev

logger.info(f"Archipelago SSL verification: {verify_ssl}")
```

### Scenario B: Production with CA Certificate
```python
# In ami_service.py __init__
import certifi

# Use system CA bundle
self.session = requests.Session()
self.session.verify = certifi.where()  # Uses system's trusted CAs
```

### Scenario C: Custom Certificate Authority
```bash
# Set environment variable
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
export CURL_CA_BUNDLE=/path/to/ca-bundle.crt
```

## Code Changes Required

### 1. Update ami_service.py
```python
def __init__(self):
    self.base_url = Config.ARCHIPELAGO_BASE_URL
    self.username = Config.ARCHIPELAGO_USERNAME
    self.password = Config.ARCHIPELAGO_PASSWORD
    self.enabled = Config.ARCHIPELAGO_ENABLED
    self.session = None
    self.csrf_token = None
    
    # Configure SSL verification
    import os
    verify_ssl = os.getenv('ARCHIPELAGO_VERIFY_SSL', 'true').lower() == 'true'
    self.verify_ssl = verify_ssl
    
    if not verify_ssl:
        logger.warning("⚠️ SSL verification disabled - only for development!")
        # Suppress warnings about unverified HTTPS
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _login(self):
    """Login to Archipelago and get CSRF token"""
    try:
        self.session = requests.Session()
        self.session.verify = self.verify_ssl  # Use configured setting
        
        login_url = f"{self.base_url}/user/login?_format=json"
        logger.info(f"Logging in to Archipelago at {login_url} (verify_ssl={self.verify_ssl})")
        
        response = self.session.post(
            login_url,
            json={'name': self.username, 'pass': self.password},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        # ... rest of login code
```

### 2. Update .env Configuration
```bash
# Required
ARCHIPELAGO_BASE_URL=https://your-archipelago-instance.com
ARCHIPELAGO_USERNAME=admin
ARCHIPELAGO_PASSWORD=your_password
ARCHIPELAGO_ENABLED=true

# Optional - for development with self-signed certs
ARCHIPELAGO_VERIFY_SSL=false

# Optional - path to custom CA bundle
# REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

## Testing the Fix

### Test 1: Backend Connection
```bash
# SSH into backend server
python3 -c "
import requests
import os

# Test with SSL verification disabled
session = requests.Session()
session.verify = False

url = os.getenv('ARCHIPELAGO_BASE_URL') + '/user/login?_format=json'
response = session.post(url, 
    json={'name': os.getenv('ARCHIPELAGO_USERNAME'), 'pass': os.getenv('ARCHIPELAGO_PASSWORD')},
    headers={'Content-Type': 'application/json'}
)
print(f'Status: {response.status_code}')
print(f'Response: {response.text[:200]}')
"
```

### Test 2: Frontend Polling
```javascript
// Open browser console (F12) and check:
// 1. Look for [Archipelago] logs
// 2. Should see status: 200 responses
// 3. Check Network tab for API calls
// 4. No SSL certificate errors

// Manual test:
fetch('/api/bulk/status/your-job-id')
  .then(r => {
    console.log('Status:', r.status);
    console.log('OK:', r.ok);
    return r.json();
  })
  .then(d => console.log('Data:', d))
  .catch(e => console.error('Error:', e));
```

### Test 3: Full Upload Flow
```bash
1. Start bulk OCR job (100+ files)
2. Wait for completion
3. Click "Upload to Archipelago"
4. Open browser console (F12)
5. Should see [Archipelago] logs showing:
   - Initial POST request (202 Accepted)
   - Polling requests every 5 seconds
   - Status 200 responses
   - Eventually archipelago_result with ami_set_id
6. No net::ERR_NETWORK_CHANGED errors
```

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `SSLError: certificate verify failed` | Self-signed cert | Set `ARCHIPELAGO_VERIFY_SSL=false` in dev |
| `ConnectionError: ... reset by peer` | Network/proxy issue | Check firewall, proxy settings |
| `Timeout waiting for response` | Archipelago slow | Increase timeout in ami_service.py |
| `Failed to fetch (browser)` | CORS/SSL | Check browser console, backend logs |
| `401 Unauthorized` | Wrong credentials | Verify `ARCHIPELAGO_USERNAME/PASSWORD` |

## Production Best Practices

1. **Always verify SSL in production**
   ```bash
   ARCHIPELAGO_VERIFY_SSL=true  # Never disable in production!
   ```

2. **Use proper CA certificates**
   ```bash
   REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
   ```

3. **Monitor SSL certificate expiration**
   ```bash
   # Check cert expiration
   openssl s_client -connect archipelago.example.com:443 -showcerts | \
    grep -A 10 "Issuer:"
   ```

4. **Use HTTPS for frontend and backend**
   - Frontend: HTTPS
   - Backend API: HTTPS
   - Archipelago: HTTPS

## See Also

- [ARCHIPELAGO_TIMEOUT_QUICK_FIX.md](./ARCHIPELAGO_TIMEOUT_QUICK_FIX.md)
- [ARCHIPELAGO_API_TIMEOUT_FIX.md](./ARCHIPELAGO_API_TIMEOUT_FIX.md)
- [ARCHIPELAGO_POLLING_FIX.md](./ARCHIPELAGO_POLLING_FIX.md)
