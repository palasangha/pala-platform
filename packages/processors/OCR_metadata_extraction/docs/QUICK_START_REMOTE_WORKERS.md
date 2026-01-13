# Quick Start: Remote OCR Workers

## On the Queue Server (172.12.0.132)

### 1. Configure Server for Remote Workers
```bash
sudo ./scripts/configure_queue_server.sh
```

This will:
- Configure firewall rules for NSQ ports
- Optionally setup NFS for shared file access
- Verify NSQ services are running

### 2. Verify Services are Running
```bash
docker-compose ps
```

Check these services are up:
- `gvpocr-nsqlookupd` (NSQ discovery)
- `gvpocr-nsqd` (NSQ message queue)
- `gvpocr-mongodb` (Database)
- `gvpocr-nsqadmin` (Admin UI at http://172.12.0.132:4171)

## On Remote Worker Machines

### 1. Clone Repository
```bash
git clone https://github.com/palasangha/OCR_metadata_extraction.git gvpocr-worker
cd gvpocr-worker
```

### 2. Run Setup Script
```bash
./scripts/setup_remote_worker.sh
```

This will:
- Test network connectivity to queue server
- Install Python dependencies
- Check system dependencies
- Create `.env` configuration file

### 3. Edit Configuration
```bash
nano backend/.env
```

Update these values:
- `MONGO_PASSWORD` - MongoDB password from queue server
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google credentials file

### 4. Copy Google Credentials (if using Google Vision)
```bash
scp user@172.12.0.132:/path/to/google-credentials.json ./backend/google-credentials.json
```

### 5. Start Worker

**Option A: Run Directly**
```bash
cd backend
source venv/bin/activate
python run_worker.py --worker-id $(hostname)-worker-1 --nsqlookupd 172.12.0.132:4161
```

**Option B: Install as Service (Recommended)**
```bash
sudo ./scripts/install_worker_service.sh
sudo systemctl start gvpocr-worker
sudo systemctl status gvpocr-worker
```

### 6. Monitor Worker
```bash
# View logs (if running as service)
sudo journalctl -u gvpocr-worker -f

# Or check NSQ Admin UI
# Open: http://172.12.0.132:4171
```

## Scaling to Multiple Workers

### Multiple Workers on Same Machine
```bash
# Terminal 1
python run_worker.py --worker-id $(hostname)-worker-1 --nsqlookupd 172.12.0.132:4161

# Terminal 2
python run_worker.py --worker-id $(hostname)-worker-2 --nsqlookupd 172.12.0.132:4161

# Terminal 3
python run_worker.py --worker-id $(hostname)-worker-3 --nsqlookupd 172.12.0.132:4161
```

### Multiple Remote Machines
Repeat steps 1-5 on each machine.

## Verification

### Check Worker is Connected
1. Open NSQ Admin UI: http://172.12.0.132:4171
2. Click on **Topics** → `bulk_ocr_file_tasks`
3. Look for channel `bulk_ocr_workers`
4. You should see your worker listed

### Test Processing
1. Submit a bulk OCR job through the web interface
2. Watch the worker logs for processing activity
3. Check NSQ Admin UI for message flow

## Troubleshooting

### Can't Connect to NSQ
```bash
# Test connectivity
telnet 172.12.0.132 4161
curl http://172.12.0.132:4161/ping

# Should return "OK"
```

### Can't Access MongoDB
```bash
# Test from worker machine
mongosh "mongodb://gvpocr_admin:<password>@172.12.0.132:27017/gvpocr"
```

### Worker Not Processing
1. Check worker logs for errors
2. Verify `.env` configuration is correct
3. Ensure Google credentials are accessible
4. Check NSQ queue has messages: http://172.12.0.132:4171

## Quick Commands

| Task | Command |
|------|---------|
| Start worker | `sudo systemctl start gvpocr-worker` |
| Stop worker | `sudo systemctl stop gvpocr-worker` |
| View logs | `sudo journalctl -u gvpocr-worker -f` |
| Restart worker | `sudo systemctl restart gvpocr-worker` |
| Check status | `sudo systemctl status gvpocr-worker` |
| NSQ Admin UI | http://172.12.0.132:4171 |

## Important Ports

| Port | Service | Purpose |
|------|---------|---------|
| 4161 | NSQ Lookupd HTTP | Worker discovery (workers connect here) |
| 4150 | NSQ Daemon TCP | Message queue |
| 27017 | MongoDB | Database |
| 4171 | NSQ Admin | Monitoring UI |

## File Access Methods

Workers need access to files being processed. Choose one:

### Option 1: NFS Mount (Recommended)
On worker:
```bash
sudo mkdir -p /mnt/gvpocr-uploads
sudo mount 172.12.0.132:/path/to/uploads /mnt/gvpocr-uploads
```

### Option 2: Direct File Paths
If worker and queue server share a file system (same machine or network storage).

### Option 3: S3/MinIO
Configure MinIO for file storage (requires code modification).
