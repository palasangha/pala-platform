# Docker Testing Setup for LangChain - Complete Summary

## ✅ Status: Ready for Docker Testing

Docker is installed and ready! You now have multiple options to test your LangChain integration with a web UI.

## 🚀 Quickest Way to Start (2 minutes)

```bash
cd /mnt/sda1/mango1_home/gvpocr

# 1. Start services
./DOCKER_QUICKSTART.sh start

# 2. Pull models (2-3 minutes)
./DOCKER_QUICKSTART.sh models

# 3. Open browser
# Visit: http://localhost:8080 (Open WebUI)
```

## 📋 What You Get

### Docker Containers

1. **Ollama** (Port 11434)
   - LLM backend
   - API endpoint: http://localhost:11434/api

2. **Open WebUI** (Port 8080) ⭐ **Best for Testing**
   - Chat interface
   - Model management
   - Easy testing
   - Access: http://localhost:8080

3. **LangFlow** (Port 7860)
   - Visual LangChain builder
   - Chain composition
   - Testing interface
   - Access: http://localhost:7860

## 🎯 Docker Quickstart Script Commands

```bash
# Start all services
./DOCKER_QUICKSTART.sh start

# Pull models
./DOCKER_QUICKSTART.sh models

# View status
./DOCKER_QUICKSTART.sh status

# View logs
./DOCKER_QUICKSTART.sh logs

# Test services
./DOCKER_QUICKSTART.sh test

# Stop services
./DOCKER_QUICKSTART.sh stop

# Clean up (remove volumes)
./DOCKER_QUICKSTART.sh clean
```

## 🔧 Docker Compose Alternative

If you prefer using docker-compose directly:

```bash
# Start
docker-compose -f docker-compose.langchain.yml up -d

# Pull models
docker exec -it langchain-ollama ollama pull mistral
docker exec -it langchain-ollama ollama pull nomic-embed-text

# View logs
docker-compose -f docker-compose.langchain.yml logs -f

# Stop
docker-compose -f docker-compose.langchain.yml down
```

## 🌐 Access the Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Open WebUI** | http://localhost:8080 | 💬 Chat with models |
| **LangFlow** | http://localhost:7860 | 🔗 Build chains visually |
| **Ollama API** | http://localhost:11434/api | 🖥️ Direct API access |
| **Your Flask App** | http://localhost:5000 | 🚀 Your application |

## 🧪 Testing Workflow

### 1. Start Everything
```bash
./DOCKER_QUICKSTART.sh start
```

### 2. Wait for Services (1-2 min)
```bash
./DOCKER_QUICKSTART.sh status
```

Should show all containers with status "Up"

### 3. Pull Models
```bash
./DOCKER_QUICKSTART.sh models
```

Takes 3-5 minutes depending on internet speed

### 4. Test via Web UI
- Visit http://localhost:8080
- Login (default: admin/admin)
- Select "mistral" model
- Try prompts

### 5. Test Your LangChain API
```bash
# Health check
curl http://localhost:5000/api/langchain/health

# Invoke
curl -X POST http://localhost:5000/api/langchain/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?"}'

# Embeddings
curl -X POST http://localhost:5000/api/langchain/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["hello", "world"]}'
```

## 📊 Monitor Services

```bash
# View logs
./DOCKER_QUICKSTART.sh logs

# View running containers
docker ps

# Check container stats
docker stats

# View specific logs
docker logs langchain-ollama
docker logs langchain-webui
docker logs langchain-langflow
```

## 🛠️ Troubleshooting

### Ollama Models Not Showing
```bash
# Check if models are installed
docker exec langchain-ollama ollama list

# Pull manually if needed
docker exec -it langchain-ollama ollama pull mistral
```

### WebUI Won't Load
```bash
# Restart container
docker restart langchain-webui

# Check logs
docker logs langchain-webui

# Rebuild
docker-compose -f docker-compose.langchain.yml down
docker-compose -f docker-compose.langchain.yml up -d
```

### Port Already in Use
```bash
# Find what's using port 8080
lsof -i :8080

# Kill process (if safe)
kill -9 <PID>

# Or change ports in docker-compose.langchain.yml
```

### Slow Performance
- Check available RAM: `free -h`
- Check CPU: `top -b -n 1`
- Monitor with: `docker stats`
- Reduce model size or use GPU if available

## 🔗 Integration with Your Flask App

### Inside Docker Network
```python
from app.services.langchain_service import get_langchain_service

# Use Docker internal hostname
service = get_langchain_service(
    ollama_host='http://ollama:11434'  # From within Docker
)
```

### From Host Machine
```python
# Use localhost
service = get_langchain_service(
    ollama_host='http://localhost:11434'  # From host
)
```

## 📁 Files Created

### Docker Setup
- ✅ `docker-compose.langchain.yml` - Docker Compose configuration
- ✅ `DOCKER_QUICKSTART.sh` - Quick start script
- ✅ `DOCKER_LANGCHAIN_TESTING.md` - Detailed testing guide
- ✅ `DOCKER_TESTING_SUMMARY.md` - This file

### LangChain Integration (Previously Created)
- ✅ `backend/app/services/langchain_service.py` - Service
- ✅ `backend/app/routes/langchain_routes.py` - API endpoints
- ✅ `LANGCHAIN_START_HERE.md` - Quick start
- ✅ `LANGCHAIN_OLLAMA_SETUP.md` - Full docs

## ✨ Benefits of Docker Testing

| Aspect | Benefit |
|--------|---------|
| **Isolation** | Don't affect host system |
| **Reproducibility** | Same environment every time |
| **Easy Cleanup** | Just stop containers |
| **Scalability** | Easy to add more services |
| **Testing** | Test with exact prod config |
| **Web UI** | Easy visual testing |
| **No Port Conflicts** | All isolated |

## 🚀 Recommended Testing Sequence

### Phase 1: Docker Setup (5 minutes)
1. ✅ Docker is installed
2. Start containers: `./DOCKER_QUICKSTART.sh start`
3. Verify: `./DOCKER_QUICKSTART.sh status`

### Phase 2: Model Setup (5-10 minutes)
1. Pull models: `./DOCKER_QUICKSTART.sh models`
2. Verify: Check in Open WebUI

### Phase 3: Web UI Testing (5 minutes)
1. Visit http://localhost:8080
2. Chat with Mistral
3. Test different prompts
4. Verify responses

### Phase 4: API Testing (5 minutes)
1. Test health endpoint
2. Test invoke endpoint
3. Test batch endpoint
4. Test embeddings
5. Test chat

### Phase 5: Integration Testing (10 minutes)
1. Update Flask app if needed
2. Test with your data
3. Verify integration
4. Check logs

## 📊 System Requirements

### Minimum (for testing)
- 2GB RAM available
- 10GB disk space
- Docker 20.10+

### Recommended
- 4GB RAM available
- 20GB disk space
- Docker 29.1+ (you have this ✅)

### Optimal
- 8GB+ RAM
- GPU (NVIDIA, AMD)
- SSD storage

## 🔐 Security Notes

### For Development
- Default credentials fine (admin/admin)
- Localhost only
- No external exposure

### For Production
- Change default passwords
- Use reverse proxy (nginx)
- Enable SSL/TLS
- Set up authentication
- Isolate networks

## 💡 Pro Tips

1. **Keep containers running** during development
   ```bash
   docker-compose -f docker-compose.langchain.yml up -d
   ```

2. **Monitor performance**
   ```bash
   docker stats --no-stream
   ```

3. **Backup volumes**
   ```bash
   docker run --rm -v ollama_data:/data -v $(pwd):/backup \
     alpine tar czf /backup/ollama_backup.tar.gz /data
   ```

4. **View API documentation**
   - Ollama: http://localhost:11434
   - Open WebUI: http://localhost:8080/docs (if available)

5. **Test endpoint directly**
   ```bash
   curl -X POST http://localhost:11434/api/generate \
     -H "Content-Type: application/json" \
     -d '{"model":"mistral","prompt":"hello","stream":false}'
   ```

## 📞 Quick Reference

### Common Commands

```bash
# Start everything
cd /mnt/sda1/mango1_home/gvpocr && ./DOCKER_QUICKSTART.sh start

# Pull models
./DOCKER_QUICKSTART.sh models

# View status
./DOCKER_QUICKSTART.sh status

# View logs
./DOCKER_QUICKSTART.sh logs

# Stop everything
./DOCKER_QUICKSTART.sh stop

# Clean up
./DOCKER_QUICKSTART.sh clean

# Test services
./DOCKER_QUICKSTART.sh test
```

### URLs to Remember

```
WebUI:     http://localhost:8080
LangFlow:  http://localhost:7860
Ollama:    http://localhost:11434
Your App:  http://localhost:5000
```

## �� Next Steps

1. ✅ **Read this file** (you are here!)
2. 🚀 **Start Docker**: `./DOCKER_QUICKSTART.sh start`
3. 🔄 **Pull models**: `./DOCKER_QUICKSTART.sh models`
4. 🌐 **Open WebUI**: Visit http://localhost:8080
5. 🧪 **Test chat**: Try some prompts
6. �� **Test API**: Run curl commands
7. 📚 **Read**: DOCKER_LANGCHAIN_TESTING.md for details
8. 💻 **Integrate**: Add to your Flask routes
9. 🚀 **Deploy**: Move to production

## 📞 Support Resources

| Resource | Path |
|----------|------|
| Docker Quick Start | `./DOCKER_QUICKSTART.sh` |
| Docker Compose | `docker-compose.langchain.yml` |
| Detailed Guide | `DOCKER_LANGCHAIN_TESTING.md` |
| LangChain Setup | `LANGCHAIN_START_HERE.md` |
| API Reference | `LANGCHAIN_OLLAMA_SETUP.md` |
| Code Examples | `LANGCHAIN_INTEGRATION_EXAMPLES.py` |

## ✅ Verification Checklist

- [x] Docker installed (29.1.3 ✅)
- [x] Docker Compose ready
- [x] docker-compose.langchain.yml created
- [x] DOCKER_QUICKSTART.sh created
- [x] Testing guide written
- [ ] Services started (next step)
- [ ] Models pulled (next step)
- [ ] Web UI accessed (next step)
- [ ] API tested (next step)

---

**Ready to test?**

```bash
cd /mnt/sda1/mango1_home/gvpocr
./DOCKER_QUICKSTART.sh start
```

**Then visit:** http://localhost:8080

---

Generated: 2024-12-23
Status: ✅ Ready for Docker Testing
