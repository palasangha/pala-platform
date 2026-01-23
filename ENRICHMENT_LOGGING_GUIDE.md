# Enrichment Services Comprehensive Logging Guide

## Overview

This guide explains the complete logging infrastructure for enrichment services, including how to monitor, analyze, and troubleshoot the system.

## Table of Contents

1. [Logging Architecture](#logging-architecture)
2. [Service Log Locations](#service-log-locations)
3. [Quick Log Monitoring](#quick-log-monitoring)
4. [Advanced Monitoring](#advanced-monitoring)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Log Aggregation (ELK Stack)](#log-aggregation-elk-stack)
7. [Environment Variables](#environment-variables)

---

## Logging Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                  Enrichment Services                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  Coordinator     │  │  Workers (×2)    │  │  APIs     │ │
│  │  Port: 8001      │  │  (NSQ Consumer)  │  │  5001,    │ │
│  │                  │  │                  │  │  5002     │ │
│  └────────┬─────────┘  └────────┬─────────┘  └─────┬─────┘ │
└───────────┼──────────────────────┼──────────────────┼────────┘
            │                      │                  │
            └──────────────────────┴──────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
            ┌───────▼────────┐          ┌────────▼──────┐
            │  Console Logs  │          │   File Logs   │
            │  (Real-time)   │          │  (/app/logs)  │
            └────────────────┘          └────────┬──────┘
                                                  │
                    ┌─────────────────────────────┘
                    │
        ┌───────────▼──────────────┐
        │   Filebeat (shipper)     │
        │   Docker log collector   │
        └───────────┬──────────────┘
                    │
        ┌───────────▼──────────────┐
        │   Elasticsearch (index)  │
        └───────────┬──────────────┘
                    │
        ┌───────────▼──────────────┐
        │   Kibana (visualization) │
        │   (http://localhost:5601)│
        └──────────────────────────┘
```

### Log Levels

- **DEBUG**: Detailed information, typically of interest only when diagnosing problems
- **INFO**: Confirmation that things are working as expected (default)
- **WARNING**: An indication that something unexpected happened or potentially problematic
- **ERROR**: A serious problem, a function has not performed some function
- **CRITICAL**: A serious error, the program itself may be unable to continue

---

## Service Log Locations

### Docker Logs

Each service logs to both console and files:

```
Service                  Container Name              Port
─────────────────────────────────────────────────────────
enrichment-coordinator   gvpocr-enrichment-coordinator  8001
enrichment-worker        ocr_metadata_extraction-enrichment-worker (×2)
review-api               gvpocr-review-api          5001
cost-api                 gvpocr-cost-api            5002
```

### Log File Locations

All services write to a shared volume: `/app/logs/`

```
/app/logs/enrichment-coordinator.log    # Coordinator logs
/app/logs/enrichment-worker.log         # Worker logs
/app/logs/review-api.log                # Review API logs
/app/logs/cost-api.log                  # Cost API logs
```

**Host Path**: `/var/lib/docker/volumes/ocr_metadata_extraction_enrichment_logs/_data/`

---

## Quick Log Monitoring

### Using the Monitoring Script

The `monitor_enrichment_logs.sh` script provides an easy way to monitor logs:

#### Basic Usage

```bash
# Show logs summary
./monitor_enrichment_logs.sh

# Monitor specific service
./monitor_enrichment_logs.sh --service coordinator
./monitor_enrichment_logs.sh --service worker
./monitor_enrichment_logs.sh --service review-api
./monitor_enrichment_logs.sh --service cost-api

# Show only errors
./monitor_enrichment_logs.sh --errors-only

# Follow logs in real-time
./monitor_enrichment_logs.sh --follow

# Monitor specific service in real-time
./monitor_enrichment_logs.sh --service coordinator --follow

# Show last 100 lines
./monitor_enrichment_logs.sh --tail 100

# Monitor worker errors in real-time
./monitor_enrichment_logs.sh --service worker --errors-only --follow
```

#### Script Options

```
-s, --service SERVICE    Filter logs for specific service
-l, --level LEVEL        Log level to display (DEBUG|INFO|WARNING|ERROR|CRITICAL)
-e, --errors-only        Show only ERROR and CRITICAL logs
-f, --follow             Follow log files (tail -f)
-t, --tail LINES         Number of lines to show initially (default: 50)
-h, --help              Show help message
```

### Using Docker Logs

```bash
# View container logs
docker logs gvpocr-enrichment-coordinator
docker logs gvpocr-review-api
docker logs gvpocr-cost-api

# Follow logs in real-time
docker logs -f gvpocr-enrichment-coordinator

# Show last 50 lines
docker logs --tail 50 gvpocr-enrichment-coordinator

# Show logs since specific time
docker logs --since 2026-01-19T13:00:00 gvpocr-enrichment-coordinator
```

### Using Standard Unix Tools

```bash
# View logs
cat /app/logs/enrichment-coordinator.log

# Follow logs
tail -f /app/logs/enrichment-coordinator.log

# Search for errors
grep ERROR /app/logs/enrichment-coordinator.log
grep -i "error\|critical" /app/logs/*.log

# Show last 30 lines
tail -30 /app/logs/enrichment-coordinator.log

# Count errors per service
for f in /app/logs/*.log; do
    errors=$(grep -ci "ERROR" "$f" 2>/dev/null || echo "0")
    echo "$(basename $f): $errors errors"
done
```

---

## Advanced Monitoring

### Log Format

All logs include the following information:

```
2026-01-19 13:20:43,123 - enrichment_service.coordinator - INFO - [coordinator.py:145] - initialize() - MongoDB connected
│                          │                                │      │                    │             │
└─ Timestamp              └─ Module name                   └─ Level
                                                              │
                                                         Context info
```

### Log Filtering

#### Find errors in all services

```bash
grep -i "ERROR" /app/logs/*.log
```

#### Find errors in coordinator

```bash
grep ERROR /app/logs/enrichment-coordinator.log
```

#### Find specific operations

```bash
# Find all MongoDB connections
grep "MongoDB" /app/logs/enrichment-coordinator.log

# Find all NSQ operations
grep "NSQ" /app/logs/*.log

# Find all agent operations
grep "Agent\|MCP" /app/logs/*.log
```

#### Timeline analysis

```bash
# Show logs in chronological order
sort -k1,2 /app/logs/enrichment-coordinator.log

# Show logs between two timestamps
awk '/2026-01-19 13:15:00/,/2026-01-19 13:30:00/ {print}' /app/logs/*.log
```

### Log Statistics

```bash
# Count log lines per service
wc -l /app/logs/*.log

# Count logs by level per service
for f in /app/logs/*.log; do
    echo "=== $(basename $f) ==="
    echo "INFO: $(grep -c 'INFO' "$f" 2>/dev/null || echo 0)"
    echo "DEBUG: $(grep -c 'DEBUG' "$f" 2>/dev/null || echo 0)"
    echo "WARNING: $(grep -c 'WARNING' "$f" 2>/dev/null || echo 0)"
    echo "ERROR: $(grep -c 'ERROR' "$f" 2>/dev/null || echo 0)"
    echo "CRITICAL: $(grep -c 'CRITICAL' "$f" 2>/dev/null || echo 0)"
    echo ""
done

# Find services with most errors
grep -h ERROR /app/logs/*.log | cut -d' ' -f3 | sort | uniq -c
```

---

## Troubleshooting Guide

### Issue: enrichment-coordinator keeps restarting

**Symptoms**:
- Container shows "Restarting (0) X seconds ago"
- Healthcheck failing

**Investigation**:
```bash
# Check logs
./monitor_enrichment_logs.sh --service coordinator

# Check for connection errors
grep -i "connection\|failed\|error" /app/logs/enrichment-coordinator.log

# Check Docker health
docker inspect gvpocr-enrichment-coordinator | grep -A 10 "Health"

# Check MongoDB connectivity
docker exec gvpocr-enrichment-coordinator python -c "
from pymongo import MongoClient
try:
    client = MongoClient('mongodb://mongodb:27017/gvpocr', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('MongoDB: OK')
except Exception as e:
    print(f'MongoDB Error: {e}')
"
```

**Solutions**:
1. Check MongoDB is running: `docker ps | grep mongodb`
2. Check NSQ is running: `docker ps | grep nsq`
3. Verify environment variables: `docker inspect gvpocr-enrichment-coordinator`
4. Restart service: `docker restart gvpocr-enrichment-coordinator`

### Issue: Worker not processing enrichment tasks

**Symptoms**:
- No worker logs
- Tasks remain in NSQ queue

**Investigation**:
```bash
# Check worker is running
docker ps | grep enrichment-worker

# Check worker logs for errors
./monitor_enrichment_logs.sh --service worker --errors-only

# Check NSQ queue depth
docker exec gvpocr-nsqadmin curl http://localhost:4151/api/topics/enrichment

# Check MCP connectivity
grep "MCP" /app/logs/enrichment-worker.log

# Check for schema validation errors
grep "schema\|validation" /app/logs/enrichment-worker.log
```

**Solutions**:
1. Check MCP server running: `docker ps | grep mcp-server`
2. Check NSQ connectivity: `telnet nsqd 4150`
3. View MCP logs: `docker logs gvpocr-mcp-server`
4. Restart workers: `docker-compose up -d enrichment-worker`

### Issue: API (review-api/cost-api) returning 500 errors

**Symptoms**:
- HTTP 500 responses
- Error logs in API container

**Investigation**:
```bash
# Check which API has errors
./monitor_enrichment_logs.sh --errors-only

# Get specific error
grep "ERROR\|Traceback" /app/logs/review-api.log
grep "ERROR\|Traceback" /app/logs/cost-api.log

# Check MongoDB
docker exec gvpocr-review-api python -c "
from pymongo import MongoClient
try:
    client = MongoClient('mongodb://mongodb:27017/gvpocr')
    client.admin.command('ping')
    print('MongoDB OK')
except Exception as e:
    print(f'Error: {e}')
"
```

**Solutions**:
1. Check MongoDB connection: `docker logs gvpocr-mongodb`
2. Restart API: `docker-compose restart review-api cost-api`
3. Check required environment variables
4. Review API implementation

### Issue: Missing logs in log files

**Symptoms**:
- Logs visible in Docker but not in files
- Log files are empty

**Investigation**:
```bash
# Check volume mount
docker inspect gvpocr-enrichment-coordinator | grep -A 5 "Mounts"

# Verify log directory exists
ls -la /app/logs/

# Check permissions
stat /app/logs/

# Check Docker volume
docker volume inspect ocr_metadata_extraction_enrichment_logs
```

**Solutions**:
1. Recreate logs volume: `docker volume rm ocr_metadata_extraction_enrichment_logs`
2. Restart services: `docker-compose up -d`
3. Check disk space: `df -h`

---

## Log Aggregation (ELK Stack)

### Setup ELK Stack

```bash
# Start ELK services
docker-compose -f docker-compose.yml -f docker-compose.logging.yml up -d elasticsearch kibana logstash filebeat

# Wait for services to start
sleep 30

# Verify
curl http://localhost:9200/_cluster/health  # Elasticsearch
curl http://localhost:5601                  # Kibana
```

### Access Kibana

Open browser: http://localhost:5601

**Default Steps**:
1. Go to Stack Management → Indices
2. Create index pattern: `enrichment-logs-*`
3. Go to Discover to view logs
4. Create visualizations for monitoring

### Kibana Queries

#### Find all errors
```
level: ERROR OR level: CRITICAL
```

#### Errors in last hour
```
level: ERROR AND @timestamp: [now-1h TO now]
```

#### Specific service logs
```
logger: *coordinator*
logger: *worker*
logger: *review_api*
logger: *cost_api*
```

#### Failed operations
```
message: "ERROR" AND message: "failed"
```

---

## Environment Variables

### Logging Configuration

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Set log directory
LOG_DIR=/app/logs

# Service-specific log levels
COORDINATOR_LOG_LEVEL=INFO
WORKER_LOG_LEVEL=INFO
REVIEW_API_LOG_LEVEL=INFO
COST_API_LOG_LEVEL=INFO

# ELK Stack
ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

### Docker Compose Example

```yaml
environment:
  - LOG_LEVEL=INFO
  - LOG_DIR=/app/logs
  - COORDINATOR_LOG_LEVEL=DEBUG  # More verbose for debugging
```

---

## Log Retention Policies

### File Rotation

Logs are automatically rotated when they reach 10 MB:

```
enrichment-coordinator.log         # Current log
enrichment-coordinator.log.1       # Backup 1
enrichment-coordinator.log.2       # Backup 2
...
enrichment-coordinator.log.10      # Backup 10 (oldest, then deleted)
```

### Cleanup Logs

```bash
# Clean logs older than 7 days
find /app/logs -name "*.log*" -mtime +7 -delete

# Archive logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz /app/logs/

# Clear all logs (WARNING: Deletes all logs)
rm -f /app/logs/*.log*
```

---

## Performance Monitoring

### Key Metrics from Logs

```bash
# Operations per minute
grep -c "operation" /app/logs/enrichment-coordinator.log | xargs -I {} echo "scale=2; {} / $(grep -o '[0-9]*:[0-9]*:[0-9]*' /app/logs/enrichment-coordinator.log | head -1 | wc -l)" | bc

# Average response time (from logs)
grep "completed in" /app/logs/*.log | awk '{print $NF}' | sed 's/ms//' | awk '{sum+=$1; count++} END {print sum/count " ms"}'

# Error rate
errors=$(grep -c ERROR /app/logs/*.log 2>/dev/null | awk -F: '{sum+=$2} END {print sum}')
total=$(wc -l /app/logs/*.log 2>/dev/null | tail -1 | awk '{print $1}')
echo "Error rate: $(echo "scale=2; $errors * 100 / $total" | bc)%"
```

---

## Best Practices

1. **Regular Monitoring**: Check logs daily for errors
2. **Log Retention**: Implement cleanup policies to manage disk space
3. **Centralization**: Use ELK stack for better analysis
4. **Alerting**: Set up alerts for ERROR and CRITICAL logs
5. **Documentation**: Keep notes on common issues and resolutions
6. **Archiving**: Archive old logs for compliance/auditing

---

## Summary

The enrichment services logging infrastructure provides:

✅ **Real-time Console Logging** - Immediate visibility in Docker
✅ **File-based Logging** - Persistent log storage with rotation
✅ **Centralized Monitoring** - ELK stack for aggregation
✅ **Easy Access** - Simple monitoring scripts and tools
✅ **Structured Data** - JSON formatting for automation
✅ **Service Isolation** - Per-service log files and levels

For questions or issues, check the logs first using the monitoring script!

---

*Last Updated: 2026-01-19*
