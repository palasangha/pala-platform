# Archipelago Commons Setup Guide

Quick setup guide to enable Archipelago Commons integration in GVPOCR.

## Prerequisites

1. An Archipelago Commons instance running and accessible
2. Credentials for a user with permissions to create digital objects
3. Archipelago's JSON:API enabled

## Step-by-Step Setup

### 1. Configure Environment Variables

Edit the `.env` file in the project root and update the Archipelago section:

```bash
# ============================================================
# Archipelago Commons Configuration
# ============================================================
# Set to true to enable Archipelago integration
ARCHIPELAGO_ENABLED=true

# Base URL of your Archipelago Commons instance
ARCHIPELAGO_BASE_URL=http://your-archipelago-server:8001

# Archipelago authentication credentials
# Create a user in Archipelago with permissions to create digital objects
ARCHIPELAGO_USERNAME=your_archipelago_username
ARCHIPELAGO_PASSWORD=your_archipelago_password
```

### 2. Update Values

Replace the following:
- `your-archipelago-server:8001` - Your Archipelago server hostname/IP and port
- `your_archipelago_username` - Archipelago username (needs digital object creation permissions)
- `your_archipelago_password` - Archipelago password

### 3. Restart Services

After updating the `.env` file, restart the Docker containers:

```bash
docker-compose down
docker-compose up -d --build
```

Or if already running:

```bash
docker-compose restart backend
```

### 4. Verify Connection

1. Log into GVPOCR
2. Navigate to Bulk Processing → Job History
3. The system automatically checks Archipelago connection
4. If configured correctly, you'll see purple upload buttons on completed jobs

Alternatively, test via API:

```bash
curl -X GET "http://localhost:5000/api/archipelago/check-connection" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Expected response:
```json
{
  "success": true,
  "enabled": true,
  "base_url": "http://your-archipelago-server:8001",
  "message": "Connected successfully"
}
```

## Archipelago User Permissions

The Archipelago user needs the following permissions:

1. **Create Digital Objects**: `create digital_object content`
2. **Create Collections**: `create digital_object_collection content`
3. **Upload Files**: `restful post file_upload`
4. **Access JSON:API**: `access jsonapi`

### Creating a User in Archipelago

1. Log into Archipelago as administrator
2. Navigate to: **People** → **Add user**
3. Create user with username/password
4. Assign role with above permissions (or create custom role)
5. Save user

## Network Configuration

### Same Network/Server

If Archipelago and GVPOCR are on the same server:

```bash
ARCHIPELAGO_BASE_URL=http://localhost:8001
```

### Different Server (Same Network)

```bash
ARCHIPELAGO_BASE_URL=http://192.168.1.100:8001
```

### Using Domain Name

```bash
ARCHIPELAGO_BASE_URL=https://archipelago.example.com
```

**Note**: Use HTTPS in production for security!

### Docker Network (If both in Docker)

If both services are in the same Docker network:

```bash
ARCHIPELAGO_BASE_URL=http://archipelago-container-name:8001
```

## Troubleshooting

### Connection Test Fails

**Check 1**: Can you access Archipelago from the backend container?

```bash
docker exec -it gvpocr-backend curl http://your-archipelago-server:8001/jsonapi
```

**Check 2**: Is Archipelago's JSON:API enabled?
- Visit: `http://your-archipelago-server:8001/jsonapi`
- Should return JSON API links

**Check 3**: Network connectivity
- Ensure backend can reach Archipelago (firewall, network rules)
- Check if Archipelago is listening on correct port

### Authentication Fails

**Check 1**: Verify credentials in Archipelago
- Log into Archipelago web interface with same credentials
- If login fails, reset password

**Check 2**: Check user permissions
- User needs digital object creation permissions
- Check role assignments

**Check 3**: Check backend logs

```bash
docker logs gvpocr-backend | grep -i archipelago
```

### Upload Button Not Visible

**Check 1**: Is integration enabled?

```bash
grep ARCHIPELAGO_ENABLED .env
```

Should show: `ARCHIPELAGO_ENABLED=true`

**Check 2**: Restart backend after config changes

```bash
docker-compose restart backend
```

**Check 3**: Check browser console
- Open Developer Tools → Console
- Look for connection check errors

### Partial Uploads

If some documents upload but others fail:

1. Check backend logs for specific errors:
```bash
docker logs gvpocr-backend --tail 100
```

2. Verify file permissions on failed files
3. Check Archipelago storage space
4. Review Archipelago logs

## Testing the Integration

### Test 1: Connection Check

```bash
curl -X GET "http://localhost:5000/api/archipelago/check-connection" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 2: Small Bulk Job

1. Process a small folder (5-10 images)
2. Go to Job History
3. Click purple upload button
4. Fill in collection details
5. Click "Push to Archipelago"
6. Verify success message with URL

### Test 3: Verify in Archipelago

1. Open the Archipelago URL from success message
2. Verify collection was created
3. Check that documents are present
4. Verify metadata is correct

## Production Deployment

For production use:

1. **Use HTTPS**:
   ```bash
   ARCHIPELAGO_BASE_URL=https://archipelago.example.com
   ```

2. **Secure Credentials**:
   - Use strong passwords
   - Consider secrets management
   - Don't commit `.env` to version control

3. **Network Security**:
   - Use VPN or private network if possible
   - Configure firewall rules
   - Enable HTTPS/TLS

4. **Monitor Logs**:
   ```bash
   docker logs -f gvpocr-backend | grep archipelago
   ```

5. **Test Thoroughly**:
   - Test with various file types
   - Test with different OCR providers
   - Test large batches

## Getting Help

If issues persist:

1. Check backend logs: `docker logs gvpocr-backend`
2. Check Archipelago logs
3. Review API responses for error details
4. Consult `ARCHIPELAGO_INTEGRATION.md` for detailed documentation
5. Check Archipelago Commons documentation: https://archipelago.nyc/

## Example Configurations

### Local Development

```bash
ARCHIPELAGO_ENABLED=true
ARCHIPELAGO_BASE_URL=http://localhost:8001
ARCHIPELAGO_USERNAME=admin
ARCHIPELAGO_PASSWORD=admin123
```

### Production (Same Network)

```bash
ARCHIPELAGO_ENABLED=true
ARCHIPELAGO_BASE_URL=https://archipelago.internal.company.com
ARCHIPELAGO_USERNAME=gvpocr_integration
ARCHIPELAGO_PASSWORD=SecureP@ssw0rd!
```

### Docker Compose Network

```bash
ARCHIPELAGO_ENABLED=true
ARCHIPELAGO_BASE_URL=http://esmero-web:80
ARCHIPELAGO_USERNAME=api_user
ARCHIPELAGO_PASSWORD=api_secure_pass
```

## Quick Checklist

- [ ] Archipelago instance is running
- [ ] JSON:API is enabled in Archipelago
- [ ] User created with proper permissions
- [ ] `.env` file updated with correct values
- [ ] `ARCHIPELAGO_ENABLED=true`
- [ ] Backend container restarted
- [ ] Connection test successful
- [ ] Purple upload button visible on completed jobs
- [ ] Test upload successful

## Next Steps

Once configured:
1. Process some documents with bulk OCR
2. Push to Archipelago from Job History
3. Verify collection in Archipelago
4. Review metadata and make adjustments if needed
5. Configure custom metadata fields if desired (see `ARCHIPELAGO_INTEGRATION.md`)

Congratulations! Your Archipelago integration is ready! 🎉
