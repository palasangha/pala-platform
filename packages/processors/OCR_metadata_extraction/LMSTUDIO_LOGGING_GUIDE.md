# LM Studio OCR Provider - Logging & Monitoring Guide

## Overview

The LM Studio OCR provider includes comprehensive logging at multiple levels (DEBUG, INFO, WARNING, ERROR) to help with monitoring, debugging, and troubleshooting.

## Logging Levels

### DEBUG Level
Detailed information for diagnosing problems:
- Provider initialization parameters
- Image file opening and optimization details
- Prompt building steps
- API request preparation
- Response parsing details
- Individual page processing steps

### INFO Level
High-level operational information:
- Provider initialization and configuration
- Availability check results
- Image/PDF processing start and completion
- Processing duration and statistics
- Page count in PDFs
- Text extraction counts

### WARNING Level
Potentially problematic situations:
- Provider not available
- Non-200 status codes
- Missing model response
- No content extracted from pages
- Configuration issues

### ERROR Level
Error conditions that prevented operation:
- Connection failures
- Timeout errors
- API errors with details
- File reading errors
- PDF conversion failures
- Unexpected exceptions with stack traces

## Logging Output Examples

### Initialization
```
INFO: LM Studio provider configured: host=http://localhost:1234, model=local-model, timeout=600s, max_tokens=4096
INFO: LM Studio provider is available and ready
```

### Image Processing
```
INFO: Starting image processing: /path/to/image.jpg
DEBUG: Image path: /path/to/image.jpg, languages: ['en'], handwriting: False
DEBUG: Opening image file: /path/to/image.jpg
DEBUG: Image loaded: size=(1920, 1080), format=JPEG
DEBUG: Optimizing and encoding image
DEBUG: Image encoded to base64, size: 2457600 bytes
DEBUG: Building default OCR prompt
DEBUG: Prompt: Extract all text from this image accurately. ...
DEBUG: Preparing API request to http://localhost:1234/v1/chat/completions
DEBUG: Sending request with model=local-model, max_tokens=4096, timeout=600s
DEBUG: API response received in 15.32s (status: 200)
DEBUG: Text extracted successfully, length: 245 chars
INFO: Image processing completed successfully in 15.45s. Extracted 245 characters
```

### PDF Processing
```
INFO: Starting PDF processing: /path/to/document.pdf
DEBUG: Converting PDF to images
INFO: PDF converted to 3 page(s)
DEBUG: Processing page 1/3
DEBUG: Added page context to prompt
DEBUG: Calling LM Studio API for page 1
DEBUG: Page 1 API call completed in 12.50s (status: 200)
DEBUG: Page 1 text extracted: 342 chars
DEBUG: Processing page 2/3
DEBUG: Page 2 API call completed in 14.20s (status: 200)
DEBUG: Page 2 text extracted: 298 chars
DEBUG: Processing page 3/3
DEBUG: Page 3 API call completed in 13.80s (status: 200)
DEBUG: Page 3 text extracted: 267 chars
INFO: PDF processing completed successfully in 42.15s. Processed 3 page(s), extracted 907 total characters
```

### Error Handling
```
ERROR: LM Studio request timed out (timeout: 600s)
DEBUG: Traceback (most recent call last):
  File "lmstudio_provider.py", line 178, in process_image
    response = requests.post(...)
  requests.exceptions.Timeout: Connection timeout

ERROR: Could not connect to LM Studio server at http://localhost:1234
DEBUG: Traceback (most recent call last):
  File "lmstudio_provider.py", line 178, in process_image
    response = requests.post(...)
  requests.exceptions.ConnectionError: Connection refused
```

## Accessing Logs

### Docker Logs
```bash
# View all backend logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Filter for LM Studio logs
docker-compose logs backend | grep -i lmstudio

# Filter for errors
docker-compose logs backend | grep ERROR
```

### Direct Log File (if configured)
```bash
# Check if logs are written to file
tail -f /path/to/logs/app.log | grep lmstudio

# View only errors
tail -f /path/to/logs/app.log | grep ERROR
```

### Python Logging Configuration
```python
import logging

# Set LM Studio provider to DEBUG level
logging.getLogger('app.services.ocr_providers.lmstudio_provider').setLevel(logging.DEBUG)

# Or set all app services to DEBUG
logging.getLogger('app.services').setLevel(logging.DEBUG)
```

## Log Analysis Tips

### Check Provider Availability
```bash
docker-compose logs backend | grep "LM Studio provider"
```

### Monitor Processing Performance
```bash
docker-compose logs backend | grep "completed successfully"
# Shows total processing time and characters extracted
```

### Identify Connection Issues
```bash
docker-compose logs backend | grep "Connection error\|Could not connect\|Timeout"
```

### Review API Errors
```bash
docker-compose logs backend | grep "API error\|status:"
```

### Track PDF Processing
```bash
docker-compose logs backend | grep "PDF\|page"
```

## Logging Configuration

### Default Configuration
The logger is automatically configured through Flask's logging system:
```python
logger = logging.getLogger(__name__)
```

The module name becomes: `app.services.ocr_providers.lmstudio_provider`

### Custom Log Level

Set in environment or application code:

```bash
# Via environment variable (if your app supports it)
export LMSTUDIO_LOG_LEVEL=DEBUG

# In Python code
import logging
logging.getLogger('app.services.ocr_providers.lmstudio_provider').setLevel(logging.DEBUG)
```

## Monitoring Metrics

### From Logs, You Can Extract

**Performance Metrics:**
- Total processing time (in seconds)
- API response time
- Image optimization time
- PDF conversion time
- Characters extracted per second

**Error Metrics:**
- Timeout failures
- Connection failures
- API errors
- Extraction failures

**Usage Metrics:**
- Images processed
- PDFs processed
- Total pages processed
- Languages detected
- Handwriting detection usage

## Example Log Analysis Script

```python
import re
from datetime import datetime

def analyze_lmstudio_logs(log_file_path):
    """Analyze LM Studio provider logs"""

    with open(log_file_path, 'r') as f:
        lines = f.readlines()

    stats = {
        'total_images': 0,
        'successful_images': 0,
        'failed_images': 0,
        'total_pdfs': 0,
        'total_pages': 0,
        'total_time': 0,
        'total_chars': 0,
        'errors': []
    }

    for line in lines:
        # Count successful processing
        if 'completed successfully' in line:
            match = re.search(r'(\d+\.?\d*?)s.*?(\d+) characters', line)
            if match:
                stats['total_time'] += float(match.group(1))
                stats['total_chars'] += int(match.group(2))

                if 'PDF' in line:
                    stats['total_pdfs'] += 1
                    page_match = re.search(r'Processed (\d+) page', line)
                    if page_match:
                        stats['total_pages'] += int(page_match.group(1))
                else:
                    stats['successful_images'] += 1

        # Count errors
        if 'ERROR' in line:
            stats['errors'].append(line.strip())
            stats['failed_images'] += 1

    # Calculate statistics
    total_operations = stats['successful_images'] + stats['total_pdfs']
    avg_time = stats['total_time'] / total_operations if total_operations > 0 else 0
    chars_per_sec = stats['total_chars'] / stats['total_time'] if stats['total_time'] > 0 else 0

    # Print report
    print("=" * 60)
    print("LM STUDIO PROVIDER LOG ANALYSIS REPORT")
    print("=" * 60)
    print(f"\nOperations Summary:")
    print(f"  Total Images Processed: {stats['successful_images']}")
    print(f"  Total PDFs Processed: {stats['total_pdfs']}")
    print(f"  Total Pages: {stats['total_pages']}")
    print(f"  Failed Operations: {stats['failed_images']}")
    print(f"\nPerformance Metrics:")
    print(f"  Total Processing Time: {stats['total_time']:.2f}s")
    print(f"  Average Time per Operation: {avg_time:.2f}s")
    print(f"  Total Characters Extracted: {stats['total_chars']}")
    print(f"  Extraction Rate: {chars_per_sec:.0f} chars/sec")
    print(f"\nErrors ({len(stats['errors'])}):")
    for error in stats['errors'][-10:]:  # Last 10 errors
        print(f"  - {error}")
    print("=" * 60)

# Usage
analyze_lmstudio_logs('/path/to/logs/app.log')
```

## Debugging Common Issues

### Issue: Provider Not Available

**Logs to look for:**
```
ERROR: Timeout while checking LM Studio availability at http://localhost:1234
ERROR: Connection error while checking LM Studio at http://localhost:1234: [Errno 111] Connection refused
```

**What to check:**
1. Is LM Studio running?
2. Is the correct host/port configured?
3. Is the model loaded?
4. Check network connectivity

### Issue: Timeout Errors

**Logs to look for:**
```
ERROR: LM Studio request timed out (timeout: 600s)
DEBUG: API response received in 600.00s (status: timeout)
```

**What to check:**
1. Is the model loaded and responsive?
2. Are system resources available (CPU, RAM, GPU)?
3. Is the timeout value appropriate?
4. Try increasing LMSTUDIO_TIMEOUT

### Issue: Text Not Extracted

**Logs to look for:**
```
WARNING: No choices in API response
WARNING: No content extracted from page 2
```

**What to check:**
1. Is the model appropriate for the image?
2. Is the image quality good?
3. Are the language hints correct?
4. Check the actual API response in DEBUG logs

### Issue: Connection Refused

**Logs to look for:**
```
ERROR: Connection error while checking LM Studio at http://localhost:1234: Connection refused
ERROR: Could not connect to LM Studio server at http://localhost:1234
```

**What to check:**
1. Is LM Studio started?
2. Is the port correct (default: 1234)?
3. Is LM Studio accessible at the configured host?
4. Check firewall settings

## Log Rotation (Best Practices)

If logging to file, implement log rotation:

```python
import logging
from logging.handlers import RotatingFileHandler

# Create rotating file handler
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)

# Add to logger
logger = logging.getLogger('app.services.ocr_providers.lmstudio_provider')
logger.addHandler(handler)
```

## Production Logging Configuration

### Recommended Settings
```bash
# Set to INFO level in production (less verbose)
LMSTUDIO_LOG_LEVEL=INFO

# Or in Python
import logging
logging.getLogger('app.services.ocr_providers.lmstudio_provider').setLevel(logging.INFO)
```

### Development Logging Configuration
```bash
# Set to DEBUG level in development
LMSTUDIO_LOG_LEVEL=DEBUG
```

## Logging Best Practices

1. **Use appropriate log levels:**
   - DEBUG: Detailed technical information
   - INFO: High-level operational events
   - WARNING: Potential issues
   - ERROR: Errors that affected operation

2. **Include context:**
   - Always log at least start/end of major operations
   - Log parameters for important function calls
   - Include timing information

3. **Sensitive data:**
   - Never log full API keys
   - Be careful with file contents
   - Mask sensitive user data

4. **Performance:**
   - Don't log in tight loops
   - Use appropriate log levels to reduce output
   - Consider asynchronous logging for high volume

## Monitoring Alerts

### Suggested Alert Conditions

**Critical:**
```
Multiple "Connection error" or "Could not connect" in short time
→ LM Studio server is down
```

**Warning:**
```
"timed out" appears frequently
→ Model is slow or system resources low
```

**Info:**
```
Track "completed successfully" to monitor throughput
→ Processing rate and performance trending
```

## Integration with External Monitoring

### Send Logs to Monitoring Service
```python
import logging
import json

class MonitoringHandler(logging.Handler):
    """Send logs to monitoring service"""

    def emit(self, record):
        log_entry = {
            'timestamp': record.created,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.name
        }

        # Send to monitoring service
        # send_to_monitoring(log_entry)
        pass

# Add to logger
logging.getLogger('app.services.ocr_providers.lmstudio_provider').addHandler(
    MonitoringHandler()
)
```

## Summary

The LM Studio provider includes comprehensive logging that helps with:

✓ **Debugging** - Detailed DEBUG logs for troubleshooting
✓ **Monitoring** - INFO logs for operational tracking
✓ **Alerting** - ERROR logs for critical issues
✓ **Performance Analysis** - Timing information in logs
✓ **Usage Tracking** - Statistics from log analysis

Use the logging output to:
1. Verify provider availability
2. Monitor processing performance
3. Identify configuration issues
4. Debug extraction failures
5. Analyze resource usage patterns

---

**Last Updated**: December 30, 2024
**Version**: 1.0
