# Troubleshooting Guide

## System Status Check

Run these commands to verify everything is working:

```bash
# Check all containers
docker-compose ps

# Check frontend logs
docker-compose logs --tail=20 frontend

# Check backend logs
docker-compose logs --tail=20 backend

# Test API health
curl http://localhost:3030/api/health

# Test departments endpoint
curl http://localhost:3030/api/departments | jq
```

## Common Issues & Solutions

### Issue 1: Frontend Not Loading

**Symptoms**: Blank page or loading spinner never completes

**Solution**:
```bash
# Rebuild and restart frontend
docker-compose build frontend
docker-compose up -d frontend

# Check logs
docker-compose logs -f frontend
```

### Issue 2: API 404 Errors

**Symptoms**: API calls return 404

**Check nginx proxy**:
```bash
# Verify nginx config
docker exec feedback-frontend cat /etc/nginx/conf.d/nginx.conf

# Check if backend is reachable from frontend container
docker exec feedback-frontend wget -O- http://backend:3000/api/health
```

### Issue 3: JavaScript Console Errors

**Fixed Errors**:
- ✅ `serviceWorkerVersion is not defined` - Fixed in index.html
- ✅ Deprecated meta tag warning - Fixed
- ✅ Missing icon files - Removed from manifest

**Remaining Non-Critical**:
- `favicon.png 404` - Cosmetic only, doesn't affect functionality

### Issue 4: CORS Errors

**Solution**: Already configured in backend:
```javascript
// backend/src/server.js has CORS enabled
app.use(cors({ origin: '*' }));
```

### Issue 5: Database Connection

**Symptoms**: Backend errors about MongoDB

**Solution**:
```bash
# Check MongoDB is running
docker-compose ps mongodb

# Check MongoDB logs
docker-compose logs mongodb

# Test connection from backend
docker exec feedback-backend node -e "require('mongoose').connect('mongodb://feedback_admin:SecurePass2026@mongodb:27017/feedback_system?authSource=admin').then(() => console.log('Connected')).catch(e => console.error(e))"
```

## Testing the Complete System

### 1. Test Frontend Access
```bash
# Should return HTML
curl -I http://localhost:3030

# Should return 200 OK
curl -I http://localhost:3030/api/health
```

### 2. Test Department Loading
```bash
# Should return 5 departments
curl -s http://localhost:3030/api/departments | jq '.data.departments | length'
```

### 3. Test Feedback Submission
```bash
# Login as admin first
TOKEN=$(curl -s -X POST http://localhost:3030/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@globalpagoda.org","password":"Admin@2026"}' | jq -r '.data.token')

# Submit feedback
curl -X POST http://localhost:3030/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "department_code": "global_pagoda",
    "user_name": "Test User",
    "user_email": "test@example.com",
    "is_anonymous": false,
    "access_mode": "web",
    "ratings": {
      "cleanliness": 5,
      "meditation_hall": 5,
      "staff": 5,
      "facilities": 5,
      "atmosphere": 10,
      "guidance": 5,
      "recommendation": 10
    },
    "comment": "Test feedback"
  }' | jq
```

### 4. Test Admin Dashboard
```bash
# Get dashboard stats
curl -s http://localhost:3030/api/admin/dashboard \
  -H "Authorization: Bearer $TOKEN" | jq
```

## Browser Debug Steps

1. **Open Developer Tools** (F12)

2. **Check Console Tab** for JavaScript errors

3. **Check Network Tab** to see:
   - Is `main.dart.js` loading? (should be ~2.5MB)
   - Are API calls succeeding?
   - Any 404 errors?

4. **Check Sources Tab**:
   - Should see `main.dart.js`
   - Should see Flutter framework files

5. **Common Browser Issues**:
   ```
   ❌ ERR_CONNECTION_REFUSED → Backend not running
   ❌ CORS error → Check backend CORS settings
   ❌ 404 on /api/* → Nginx proxy misconfigured
   ✅ Loading spinner → Normal, app is initializing
   ```

## Performance Checks

```bash
# Check container resource usage
docker stats --no-stream

# Check if containers are healthy
docker-compose ps | grep healthy

# Check disk space
df -h ./volumes/
```

## Logs Analysis

### Frontend Nginx Logs
```bash
# Access logs
docker-compose logs frontend | grep "GET"

# Error logs
docker-compose logs frontend | grep "error"
```

### Backend API Logs
```bash
# Request logs (should show all API calls)
docker-compose logs backend | grep "GET\|POST\|PUT\|DELETE"

# Error logs
docker-compose logs backend | grep "Error\|error\|ERROR"
```

### MongoDB Logs
```bash
# Connection logs
docker-compose logs mongodb | grep "connection"

# Error logs
docker-compose logs mongodb | grep "error\|Error"
```

## Reset & Rebuild

If all else fails, complete rebuild:

```bash
# Stop everything
docker-compose down

# Remove old images (optional)
docker-compose down --rmi all

# Rebuild from scratch
docker-compose build --no-cache

# Start fresh
docker-compose up -d

# Check status
docker-compose ps
```

## Verification Checklist

- [ ] All 4 containers running (frontend, backend, mongodb, backup)
- [ ] Frontend accessible at http://localhost:3030
- [ ] Backend healthy at http://localhost:3001/api/health
- [ ] MongoDB accepting connections
- [ ] API proxy working (http://localhost:3030/api/*)
- [ ] Departments loading in browser
- [ ] Can navigate to feedback form
- [ ] Can submit feedback
- [ ] Admin login works
- [ ] Dashboard shows statistics

## Current Known Status

Based on final verification (Last Updated: January 23, 2026 17:05 IST):

✅ **ALL SYSTEMS OPERATIONAL**:
- All 4 containers running and healthy
- Nginx serving Flutter files correctly
- Backend API responding (all endpoints working)
- MongoDB connected and operational
- API proxy functional (nginx → backend)
- main.dart.js loading successfully (2.6MB)
- Departments endpoint working (5 departments)
- Health check passing consistently

✅ **ALL ERRORS FIXED**:
- serviceWorkerVersion error - FIXED (added variable declaration)
- Deprecated meta tag - FIXED (added mobile-web-app-capable)
- Missing icon references - FIXED (removed from manifest.json)
- favicon.png 404 - FIXED (created and deployed 2KB favicon)

🎉 **ZERO ERRORS REMAINING** - System is production-ready!

## Contact & Support

If issues persist:

1. Check `docker-compose logs` for all services
2. Verify `.env` file has correct values
3. Ensure ports 3030 and 3001 are not in use by other apps
4. Check firewall rules if accessing remotely
5. Review browser console for specific errors

---

**Last Updated**: January 23, 2026
**System Version**: 1.0.0
