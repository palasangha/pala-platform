# LM Studio Provider - Logging Quick Reference

## Quick Log Commands

```bash
# Real-time logs
docker-compose logs -f backend

# LM Studio logs only
docker-compose logs backend | grep -i lmstudio

# Last 20 lines
docker-compose logs --tail=20 backend

# Errors only
docker-compose logs backend | grep ERROR

# Warnings
docker-compose logs backend | grep WARNING

# Processing times
docker-compose logs backend | grep "completed successfully"

# Connection issues
docker-compose logs backend | grep -i "connection\|timeout\|refused"

# PDF processing
docker-compose logs backend | grep -i "pdf\|page"
```

## Log Levels at a Glance

| Level | Use Case | Examples |
|-------|----------|----------|
| **DEBUG** | Detailed troubleshooting | Image optimization, API details, response parsing |
| **INFO** | Track operations | Processing start/end, timing, character count |
| **WARNING** | Potential issues | Provider unavailable, empty responses |
| **ERROR** | Failures | Connection errors, timeouts, API failures |

## Common Log Patterns

### Successful Image Processing
```
INFO: Starting image processing: image.jpg
INFO: Image processing completed successfully in 15.45s. Extracted 245 characters
```

### Successful PDF Processing
```
INFO: Starting PDF processing: document.pdf
INFO: PDF converted to 3 page(s)
INFO: PDF processing completed successfully in 42.15s. Processed 3 page(s)
```

### Connection Error
```
ERROR: Connection error while checking LM Studio at http://localhost:1234
ERROR: Could not connect to LM Studio server
```

### Timeout Error
```
ERROR: LM Studio request timed out (timeout: 600s)
```

### Missing Content
```
WARNING: No choices in API response
WARNING: No content extracted from page 2
```

## Extract Performance Metrics

```bash
# Average processing time (in seconds)
docker-compose logs backend | grep "completed successfully" | \
  sed 's/.*in \([0-9.]*\)s.*/\1/' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "s"}'

# Total characters extracted
docker-compose logs backend | grep "Extracted" | \
  sed 's/.*Extracted \([0-9]*\) char.*/\1/' | \
  awk '{sum+=$1} END {print "Total:", sum " characters"}'

# Count successful operations
docker-compose logs backend | grep "completed successfully" | wc -l

# Count errors
docker-compose logs backend | grep ERROR | wc -l
```

## Troubleshooting Checklist

```bash
# 1. Check if provider is available
docker-compose logs backend | grep "LM Studio provider"

# 2. Check for connection errors
docker-compose logs backend | grep "Connection\|Could not connect"

# 3. Check for timeouts
docker-compose logs backend | grep "timed out"

# 4. Check configuration
docker-compose logs backend | grep "configured:"

# 5. Check last error
docker-compose logs backend | grep ERROR | tail -1

# 6. Check processing status
docker-compose logs backend | grep "Starting\|completed"
```

## Debug Mode (Verbose)

```bash
# Enable debug logs for detailed troubleshooting
# In Python code:
import logging
logging.getLogger('app.services.ocr_providers.lmstudio_provider').setLevel(logging.DEBUG)

# Then view logs with full details
docker-compose logs -f backend | grep lmstudio
```

## Key Metrics You Can Track

From logs, calculate:
- **Processing time**: 15.45s (from "completed successfully in 15.45s")
- **API response time**: 15.32s (from "received in 15.32s")
- **Characters extracted**: 245 chars (from "Extracted 245 characters")
- **Pages processed**: 3 pages (from "Processed 3 page(s)")
- **Success rate**: Count "completed successfully" / total operations

## Log Formats

**Success message:**
```
INFO: Image processing completed successfully in {time}s. Extracted {chars} characters
```

**Error message:**
```
ERROR: {error_type}: {error_details}
```

**Timing format:**
```
DEBUG: {operation} completed in {time}s (status: {status})
```

## Real-world Examples

### Monitor a Live Processing
```bash
docker-compose logs -f backend | grep -E "Starting|completed successfully"
```

### Find Slow Operations
```bash
docker-compose logs backend | grep "completed successfully" | awk '{print $NF}' | sort -rn | head
```

### Identify Problematic Models
```bash
docker-compose logs backend | grep "ERROR\|WARNING" | \
  grep -v "Connection refused" | head -20
```

### Track PDF Processing
```bash
docker-compose logs backend | grep "PDF\|page" | tail -30
```

## File Locations

- **Provider code**: `backend/app/services/ocr_providers/lmstudio_provider.py`
- **Logging docs**: `LMSTUDIO_LOGGING_GUIDE.md`
- **Setup docs**: `LMSTUDIO_SETUP.md`
- **Logs output**: Docker logs (see commands above)

## Default Configuration

```
URL:        http://localhost:1234
Timeout:    600 seconds
Max tokens: 4096
Model:      local-model
```

## Quick Diagnostic Steps

1. **Is LM Studio running?**
   ```bash
   curl http://localhost:1234/v1/models
   ```

2. **View LM Studio logs**
   ```bash
   docker-compose logs -f backend | grep lmstudio
   ```

3. **Check for errors**
   ```bash
   docker-compose logs backend | grep ERROR
   ```

4. **Test image processing**
   ```bash
   python example_lmstudio_usage.py
   ```

5. **Check configuration**
   ```bash
   docker-compose logs backend | grep "configured:"
   ```

## Summary

✓ Comprehensive logging at 4 levels (DEBUG, INFO, WARNING, ERROR)
✓ Performance timing included
✓ Easy to filter and analyze
✓ Ready for production monitoring
✓ Integration with Docker logging
✓ Can track metrics and trends

For detailed logging documentation, see: **LMSTUDIO_LOGGING_GUIDE.md**
