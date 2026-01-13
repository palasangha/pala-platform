# Remote OCR Worker Setup Guide

This guide explains how to install and configure OCR workers on remote machines to connect to the central NSQ queue.

## Architecture Overview

- **Queue Server (This Machine)**: 172.12.0.132
  - NSQ Lookupd: Port 4161 (HTTP), 4160 (TCP)
  - NSQ Daemon: Port 4150 (TCP), 4151 (HTTP)
  - MongoDB: Port 27017
  - NSQ Admin UI: Port 4171

- **Remote Workers**: Connect to the queue server to receive and process OCR tasks

## Prerequisites on Remote Machines

### 1. System Requirements
- Python 3.8+
- Network access to the queue server (172.12.0.132)
- Sufficient disk space for temporary file processing
- (Optional) GPU for Ollama/vLLM support

### 2. Required Software
- Python packages (see requirements.txt)
- Tesseract OCR (if using Tesseract provider)
- Google Cloud credentials (if using Google Vision)

## Step 1: Network Configuration on Queue Server

On the **queue server** (172.12.0.132), ensure NSQ and MongoDB ports are accessible:

### Check Current Port Exposure
```bash
# Check if ports are listening on all interfaces
sudo netstat -tlnp | grep -E '4150|4151|4160|4161|27017'
```

### Update Docker Compose (if needed)
The docker-compose.yml already exposes the required ports. Verify with:
```bash
docker-compose ps
```

### Configure Firewall
Allow incoming connections on required ports:
```bash
# For NSQ
sudo ufw allow 4150/tcp comment "NSQ daemon TCP"
sudo ufw allow 4151/tcp comment "NSQ daemon HTTP"
sudo ufw allow 4160/tcp comment "NSQ lookupd TCP"
sudo ufw allow 4161/tcp comment "NSQ lookupd HTTP"

# For MongoDB (if workers need direct access)
sudo ufw allow from <WORKER_IP> to any port 27017 comment "MongoDB for worker"

# Or allow from entire subnet
sudo ufw allow from 172.12.0.0/24 to any port 27017
```

## Step 2: Install Worker on Remote Machine

### Clone Repository
```bash
git clone https://github.com/palasangha/OCR_metadata_extraction.git gvpocr-worker
cd gvpocr-worker/backend
```

### Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Install System Dependencies

#### Ubuntu/Debian
```bash
# Tesseract OCR
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa tesseract-ocr-fra

# PDF processing
sudo apt-get install -y poppler-utils

# OpenCV dependencies
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```

#### CentOS/RHEL
```bash
sudo yum install -y tesseract tesseract-langpack-eng
sudo yum install -y poppler-utils
```

## Step 3: Configure Worker Environment

Create a `.env` file in the worker directory:

```bash
# MongoDB Connection (to central database)
MONGO_URI=mongodb://172.12.0.132:27017/gvpocr
MONGO_USERNAME=gvpocr_admin
MONGO_PASSWORD=<your-mongo-password>

# NSQ Configuration
USE_NSQ=true
NSQD_ADDRESS=172.12.0.132:4150
NSQLOOKUPD_ADDRESSES=172.12.0.132:4161

# OCR Provider Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-credentials.json
DEFAULT_OCR_PROVIDER=google_vision

# Provider Enablement
GOOGLE_VISION_ENABLED=true
TESSERACT_ENABLED=true
OLLAMA_ENABLED=false
VLLM_ENABLED=false
EASYOCR_ENABLED=false
AZURE_ENABLED=false

# Ollama (if running locally on worker)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2-vision

# vLLM (if running locally on worker)
VLLM_HOST=http://localhost:8000
VLLM_MODEL=phi-vision
VLLM_API_KEY=vllm-secret-token
```

## Step 4: Setup Shared Files Access

Workers need access to files being processed. Choose one method:

### Option A: Network File System (NFS)
Mount the uploads directory from the queue server:

**On Queue Server:**
```bash
# Install NFS server
sudo apt-get install nfs-kernel-server

# Configure export
sudo nano /etc/exports
# Add line:
# /mnt/sda1/mango1_home/gvpocr/backend/uploads 172.12.0.0/24(ro,sync,no_subtree_check)

# Restart NFS
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server

# Allow NFS through firewall
sudo ufw allow from 172.12.0.0/24 to any port nfs
```

**On Worker Machine:**
```bash
# Install NFS client
sudo apt-get install nfs-common

# Create mount point
sudo mkdir -p /mnt/gvpocr-uploads

# Mount
sudo mount 172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /mnt/gvpocr-uploads

# Make permanent (add to /etc/fstab)
echo "172.12.0.132:/mnt/sda1/mango1_home/gvpocr/backend/uploads /mnt/gvpocr-uploads nfs defaults 0 0" | sudo tee -a /etc/fstab
```

### Option B: Shared S3/MinIO Storage
Use MinIO or S3 for file storage (modify worker code to download files from MinIO before processing).

### Option C: Local File Sync
Use rsync or similar to sync files to worker machines (not recommended for real-time processing).

## Step 5: Copy Google Credentials

If using Google Vision API:
```bash
# Copy from queue server
scp user@172.12.0.132:/path/to/google-credentials.json ./google-credentials.json

# Update .env to point to local copy
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/google-credentials.json
```

## Step 6: Start the Worker

### Test Connection First
```bash
# Test NSQ connectivity
curl http://172.12.0.132:4161/ping
# Should return "OK"

# Test MongoDB connectivity
python3 -c "from pymongo import MongoClient; client = MongoClient('mongodb://172.12.0.132:27017/'); print('MongoDB connected:', client.server_info()['version'])"
```

### Run Worker
```bash
# Activate virtual environment
source venv/bin/activate

# Generate unique worker ID (e.g., hostname or custom name)
WORKER_ID=$(hostname)-worker-1

# Start worker
python run_worker.py --worker-id $WORKER_ID --nsqlookupd 172.12.0.132:4161
```

### Run as Systemd Service (Recommended)

Create `/etc/systemd/system/gvpocr-worker.service`:

```ini
[Unit]
Description=GVPOCR Worker
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/gvpocr-worker/backend
Environment="PATH=/path/to/gvpocr-worker/backend/venv/bin"
EnvironmentFile=/path/to/gvpocr-worker/backend/.env
ExecStart=/path/to/gvpocr-worker/backend/venv/bin/python run_worker.py --worker-id %H-worker --nsqlookupd 172.12.0.132:4161
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gvpocr-worker
sudo systemctl start gvpocr-worker
sudo systemctl status gvpocr-worker
```

View logs:
```bash
sudo journalctl -u gvpocr-worker -f
```

## Step 7: Verify Worker is Connected

### On Queue Server
Check NSQ Admin UI:
```bash
# Open in browser
http://172.12.0.132:4171
```

Look for:
- Topic: `bulk_ocr_file_tasks`
- Channel: `bulk_ocr_workers`
- Connected workers should appear in the channel

### Check Topic Stats
```bash
curl http://172.12.0.132:4151/stats?format=json | python -m json.tool
```

### Monitor Worker Logs
On the worker machine:
```bash
# If running directly
tail -f logs.txt

# If running as systemd service
sudo journalctl -u gvpocr-worker -f
```

## Scaling Workers

### Multiple Workers on Same Machine
Run multiple instances with different worker IDs:
```bash
python run_worker.py --worker-id $(hostname)-worker-1 --nsqlookupd 172.12.0.132:4161 &
python run_worker.py --worker-id $(hostname)-worker-2 --nsqlookupd 172.12.0.132:4161 &
python run_worker.py --worker-id $(hostname)-worker-3 --nsqlookupd 172.12.0.132:4161 &
```

### Multiple Remote Machines
Repeat Steps 2-6 on each machine with unique worker IDs.

## Troubleshooting

### Worker Can't Connect to NSQ
```bash
# Test connectivity
telnet 172.12.0.132 4161
nc -zv 172.12.0.132 4161

# Check firewall
sudo ufw status
```

### Worker Can't Access MongoDB
```bash
# Test MongoDB connection
mongosh "mongodb://gvpocr_admin:<password>@172.12.0.132:27017/gvpocr"
```

### Worker Can't Access Files
```bash
# Check NFS mount
df -h | grep gvpocr
mount | grep gvpocr

# Test file access
ls /mnt/gvpocr-uploads
```

### OCR Processing Fails
```bash
# Check Google credentials
echo $GOOGLE_APPLICATION_CREDENTIALS
cat $GOOGLE_APPLICATION_CREDENTIALS

# Test Tesseract
tesseract --version
tesseract --list-langs
```

### View NSQ Messages in Queue
```bash
# Check pending messages
curl http://172.12.0.132:4151/stats?format=json | grep depth
```

## Performance Tuning

### Adjust Concurrent Processing
Edit `backend/app/workers/ocr_worker.py` line 202:
```python
max_in_flight=5,  # Increase for more concurrent processing per worker
```

### Worker Resource Limits
Monitor and adjust based on:
- CPU usage
- Memory usage
- Network bandwidth
- GPU availability (for Ollama/vLLM)

## Security Considerations

1. **Firewall Rules**: Only allow worker IPs, not the entire internet
2. **MongoDB Authentication**: Always use authentication in production
3. **VPN/Private Network**: Consider using VPN for worker-to-server communication
4. **SSL/TLS**: For production, configure NSQ with TLS
5. **Credentials**: Store Google credentials securely, don't commit to git

## Monitoring

### NSQ Admin Dashboard
- URL: http://172.12.0.132:4171
- Monitor: Queue depth, message rates, worker connections

### Worker Metrics
Each worker logs:
- Files processed
- Processing time
- Error count
- Worker ID

### Database Monitoring
Check job progress in MongoDB:
```bash
mongosh "mongodb://gvpocr_admin:<password>@172.12.0.132:27017/gvpocr"
db.bulk_jobs.find({status: "processing"}).count()
```

## Quick Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| NSQ Lookupd | 4160 | TCP | Discovery (workers connect here) |
| NSQ Lookupd | 4161 | HTTP | HTTP API |
| NSQ Daemon | 4150 | TCP | Message queue |
| NSQ Daemon | 4151 | HTTP | HTTP API |
| NSQ Admin | 4171 | HTTP | Admin UI |
| MongoDB | 27017 | TCP | Database |

**Queue Server IP**: 172.12.0.132

**Worker Start Command**:
```bash
python run_worker.py --worker-id <unique-id> --nsqlookupd 172.12.0.132:4161
```
