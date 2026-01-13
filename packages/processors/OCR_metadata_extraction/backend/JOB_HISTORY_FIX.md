# Job History Display Issue - 401 Unauthorized

## Problem

The job history is not displaying because the `/api/bulk/history` endpoint is returning **401 Unauthorized** errors continuously.

```
GET /api/bulk/history?page=1&limit=10 HTTP/1.1" 401
```

## Root Cause

The bulk history endpoint requires authentication:

```python
@bulk_bp.route('/history', methods=['GET'])
@token_required  # <-- Requires valid JWT token
def get_job_history(current_user_id):
    ...
```

The frontend is making requests without a valid JWT token, or the token has expired.

## Solution Options

### Option 1: Check Frontend Authentication (Recommended)

1. **Verify user is logged in**:
   - Check if user has a valid session
   - Verify JWT token is stored (localStorage/sessionStorage)
   - Check token expiration

2. **Refresh the token if expired**:
   - JWT tokens expire after 1 hour (see [app/config.py](app/config.py#L27))
   - Frontend should refresh the token before expiration
   - Or redirect to login if token is expired

3. **Include token in requests**:
   ```javascript
   const token = localStorage.getItem('access_token');

   fetch('/api/bulk/history?page=1&limit=10', {
     headers: {
       'Authorization': `Bearer ${token}`
     }
   })
   ```

### Option 2: Make Endpoint Public (Not Recommended)

If you want to allow unauthenticated access to job history:

**⚠️ Security Warning**: This exposes all users' job history to anyone.

Remove `@token_required` decorator:

```python
@bulk_bp.route('/history', methods=['GET'])
# @token_required  # <-- Comment this out
def get_job_history(current_user_id=None):  # Make current_user_id optional
    # Modify logic to handle no user_id
    if current_user_id:
        jobs = BulkJob.find_by_user(mongo, current_user_id, skip=skip, limit=limit)
    else:
        # Return all jobs or handle appropriately
        jobs = BulkJob.find_all(mongo, skip=skip, limit=limit)
```

### Option 3: Use Session-Based Auth (Alternative)

If JWT is problematic, switch to session-based authentication for this endpoint.

## Diagnostic Steps

### 1. Check if User is Logged In

```bash
# Check browser console
localStorage.getItem('access_token')
# or
sessionStorage.getItem('access_token')
```

### 2. Decode JWT Token (if exists)

```javascript
// In browser console
const token = localStorage.getItem('access_token');
if (token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  console.log('Token expires at:', new Date(payload.exp * 1000));
  console.log('Current time:', new Date());
  console.log('Is expired:', Date.now() > payload.exp * 1000);
}
```

### 3. Test Endpoint with curl

```bash
# Without token (will get 401)
curl http://localhost:5000/api/bulk/history?page=1&limit=10

# With token (should work)
TOKEN="your_jwt_token_here"
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/bulk/history?page=1&limit=10
```

### 4. Check Backend Token Validation

Look at the `@token_required` decorator in [app/utils/decorators.py](app/utils/decorators.py):

```python
# Check if this is validating tokens correctly
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            # Decode and validate token
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated
```

## Report.zip File Storage

### Location

Reports are stored in output folders within the upload directory:

```python
# From bulk.py line 314-315
output_folder = os.path.join(Config.UPLOAD_FOLDER, f'bulk_{timestamp}')
zip_path = os.path.join(output_folder, 'reports.zip')
```

**Default path**: `/app/uploads/bulk_{timestamp}/reports.zip`

### Structure

```
/app/uploads/
├── bulk_20251127_050000/
│   ├── reports.zip          # <-- All reports in one ZIP
│   ├── results.json         # Full results
│   ├── ocr_report.json      # JSON report
│   ├── ocr_report.csv       # CSV report
│   └── ocr_report.txt       # Text report
├── bulk_20251127_060000/
│   └── reports.zip
└── ...
```

### Contents of reports.zip

```
reports.zip
├── ocr_report.json    # All OCR results in JSON format
├── ocr_report.csv     # All results in CSV format
└── ocr_report.txt     # All results in plain text format
```

### Download Endpoint

```python
@bulk_bp.route('/download/<job_id>', methods=['GET'])
@token_required
def download_reports(current_user_id, job_id):
    """Download reports.zip for a specific job"""
    # Returns: /app/uploads/bulk_{job_id}/reports.zip
```

### Docker Volume Mapping

Check `docker-compose.yml` for volume mapping:

```yaml
backend:
  volumes:
    - ./backend/uploads:/app/uploads  # Local uploads folder
```

**Host location**: `/mnt/sda1/mango1_home/gvpocr/backend/uploads/bulk_*/reports.zip`

### Accessing Report Files

#### From Host Machine

```bash
# List all report folders
ls -lh /mnt/sda1/mango1_home/gvpocr/backend/uploads/

# Find all report.zip files
find /mnt/sda1/mango1_home/gvpocr/backend/uploads -name "reports.zip"

# Extract a specific report
cd /mnt/sda1/mango1_home/gvpocr/backend/uploads/bulk_TIMESTAMP/
unzip reports.zip
```

#### From Container

```bash
# List uploads in container
docker-compose exec backend ls -lh /app/uploads/

# Find report files
docker-compose exec backend find /app/uploads -name "reports.zip"

# Copy report to host
docker cp gvpocr-backend:/app/uploads/bulk_TIMESTAMP/reports.zip ./
```

#### Via API (Requires Auth)

```bash
# Get job ID from history
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5000/api/bulk/history?page=1&limit=10

# Download reports for specific job
curl -H "Authorization: Bearer $TOKEN" \
     -o reports.zip \
     http://localhost:5000/api/bulk/download/{job_id}
```

## Quick Fix Recommendations

### For Job History Display

1. **Check Frontend Code**:
   - Verify authentication state management
   - Ensure token is included in API requests
   - Add token refresh logic before requests

2. **Add Error Handling**:
   ```javascript
   // In frontend API call
   fetch('/api/bulk/history?page=1&limit=10', {
     headers: {
       'Authorization': `Bearer ${getToken()}`
     }
   })
   .then(response => {
     if (response.status === 401) {
       // Token expired - redirect to login
       window.location.href = '/login';
     }
     return response.json();
   })
   .catch(error => {
     console.error('Failed to fetch job history:', error);
     // Show user-friendly error message
   });
   ```

3. **Add Token Refresh**:
   ```javascript
   // Refresh token before expiration
   const refreshTokenIfNeeded = async () => {
     const token = getToken();
     if (!token) return null;

     const payload = JSON.parse(atob(token.split('.')[1]));
     const expiresIn = payload.exp * 1000 - Date.now();

     // Refresh if expiring in less than 5 minutes
     if (expiresIn < 5 * 60 * 1000) {
       return await refreshToken();
     }
     return token;
   };
   ```

### For Report Access

Reports are accessible both:
1. **Via API** (requires auth): `/api/bulk/download/{job_id}`
2. **Directly on filesystem**: `/mnt/sda1/mango1_home/gvpocr/backend/uploads/bulk_*/reports.zip`

## Monitoring

Check logs for authentication issues:

```bash
# Watch for authentication errors
docker-compose logs backend -f | grep -i "401\|unauthorized\|token"

# Check recent history requests
docker-compose logs backend | grep "/api/bulk/history" | tail -20
```

## Related Files

- [app/routes/bulk.py](app/routes/bulk.py) - Bulk processing routes
- [app/utils/decorators.py](app/utils/decorators.py) - Authentication decorators
- [app/config.py](app/config.py) - JWT configuration
- [app/models/bulk_job.py](app/models/bulk_job.py) - Job history model

## Summary

**Issue**: Job history shows 401 errors because authentication token is missing/expired.

**Fix**: Ensure frontend includes valid JWT token in Authorization header for all `/api/bulk/history` requests.

**Reports Location**: `/mnt/sda1/mango1_home/gvpocr/backend/uploads/bulk_*/reports.zip`
