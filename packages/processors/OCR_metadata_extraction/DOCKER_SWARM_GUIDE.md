# Docker Swarm Worker Management Guide

## Overview

This guide explains how to manage OCR workers using Docker Swarm for distributed, scalable processing.

## What is Docker Swarm?

Docker Swarm is Docker's native orchestration platform that allows you to:
- **Scale workers** up and down easily
- **Distribute tasks** across multiple machines
- **Load balance** automatically
- **Recover from failures** with automatic restart
- **Monitor and manage** all workers from one place

## Architecture

```
Main Server (Manager Node) - 172.12.0.132
├── MongoDB (27017)
├── NSQ (4150, 4161)
├── Ollama (11434)
├── LlamaCPP (8007)
└── Swarm Manager
    └── OCR Worker Service (3+ replicas)
        ├── Worker 1 (on manager or worker node)
        ├── Worker 2 (on worker node 1)
        └── Worker 3 (on worker node 2)

Worker Nodes (Worker Nodes) - 172.12.0.96, etc.
├── SSHFS Mounts
└── OCR Worker (managed by swarm)
```

## Getting Started

### 1. Initialize Docker Swarm

The main server is already initialized as a manager node:

```bash
docker swarm init --advertise-addr 172.12.0.132
```

### 2. Add Worker Nodes to Swarm

To add a remote worker (e.g., 172.12.0.96) to the swarm:

```bash
# Get the join token
docker swarm join-token worker

# On the remote worker machine, run:
docker swarm join --token SWMTKN-1-1x6pzb8usoxc2pwc0ziwijy9fnaawavkblmznc7m74h765jk3r-8b4gjreqaaulxcsm0m5tgbzii 172.12.0.132:2377
```

### 3. Deploy Workers

```bash
cd /mnt/sda1/mango1_home/gvpocr
chmod +x swarm-manage.sh
./swarm-manage.sh deploy
```

This deploys the OCR worker service with 3 replicas across the swarm.

## Management Commands

### Check Status

```bash
./swarm-manage.sh status
```

Output:
```
Swarm Info:
 Swarm: active
 NodeID: v2gvb0g72g4bm337qykrtoavq
 Is Manager: true

Nodes:
ID                            HOSTNAME    STATUS  MANAGERSTAT  AVAILABI
v2gvb0g72g4bm337qykrtoavq     main-srv    Ready   Leader       Active
a8f4k9j2m3l5n7p0r1s2t3u4     worker-1    Ready               Active
b9g5l0k3n4m6o8q1s2t3u4v5     worker-2    Ready               Active

Services:
ID         NAME              MODE        REPLICAS  IMAGE
k7m2j4l1n  gvpocr_ocr-worker replicated  3/3       registry.docgenai.com:5010/gvpocr-worker-updated:latest

Tasks:
TASKID          NAME               NODE        STATUS   DESIRED
a1b2c3d4e5f6    gvpocr_ocr-worker.1  main-srv  Running  Running
f6g7h8i9j0k1    gvpocr_ocr-worker.2  worker-1  Running  Running
k2l3m4n5o6p7    gvpocr_ocr-worker.3  worker-2  Running  Running
```

### Scale Workers

Increase or decrease the number of worker replicas:

```bash
# Scale to 5 workers
./swarm-manage.sh scale 5

# Scale to 10 workers
./swarm-manage.sh scale 10

# Scale down to 2 workers
./swarm-manage.sh scale 2
```

### View Logs

Monitor worker logs in real-time:

```bash
# View logs from all workers
./swarm-manage.sh logs

# Or specify a task ID
./swarm-manage.sh logs <task_id>
```

### Resource Monitoring

Check resource usage of running workers:

```bash
./swarm-manage.sh stats
```

Output:
```
CONTAINER      MEMUSAGE        CPUPERC    NETIO
worker.1       1.2GB / 4GB     25%        12MB / 5MB
worker.2       1.5GB / 4GB     18%        15MB / 8MB
worker.3       1.1GB / 4GB     22%        10MB / 4MB
```

### Health Check

Verify all workers are healthy:

```bash
./swarm-manage.sh health
```

### Restart Service

Force restart all workers:

```bash
./swarm-manage.sh restart
```

### Update Service

Update service configuration (image, environment, etc.):

```bash
# Update to new image version
./swarm-manage.sh update --image registry.docgenai.com:5010/gvpocr-worker-updated:v2

# Update environment variable
./swarm-manage.sh update -e LLAMACPP_MODEL=phi-3

# Update resource limits
./swarm-manage.sh update --limit-memory 8GB
```

## Node Management

### List Nodes

```bash
docker node ls
```

### Add Worker Node

```bash
./swarm-manage.sh add-node
```

Follow the instructions to join a new worker to the swarm.

### Drain Node (for Maintenance)

Temporarily stop assigning tasks to a node while existing tasks finish:

```bash
./swarm-manage.sh drain <node_id>
```

This is useful when:
- Performing maintenance on a worker machine
- Updating system packages
- Restarting the Docker daemon
- Cleaning up disk space

### Restore Node

Bring a drained node back online:

```bash
./swarm-manage.sh restore <node_id>
```

### Remove Node

Remove a node from the swarm:

```bash
./swarm-manage.sh remove-node <node_id>
```

## Configuration

### Stack File: docker-stack.yml

The stack configuration defines:
- **Service**: OCR worker service
- **Replicas**: Number of worker instances (3 by default)
- **Resources**: CPU and memory limits
- **Placement**: Where to run workers (worker nodes only)
- **Restart Policy**: Automatic restart on failure
- **Health Check**: Periodic status verification
- **Environment**: Configuration variables
- **Volumes**: Shared SSHFS mounts

### Resource Limits

Current limits in docker-stack.yml:
```yaml
resources:
  limits:
    cpus: '2'           # Max 2 CPU cores per worker
    memory: 4G          # Max 4GB RAM per worker
  reservations:
    cpus: '1'           # Reserve 1 CPU core
    memory: 2G          # Reserve 2GB RAM
```

Modify these based on your hardware:

```bash
./swarm-manage.sh update --limit-cpus 4 --limit-memory 8GB
```

### Placement Constraints

Current setting: Run workers only on worker nodes (not manager):
```yaml
placement:
  constraints:
    - node.role == worker
```

To also allow manager node:
```yaml
placement:
  constraints: []
```

## Scaling Strategies

### Manual Scaling

```bash
# Start with 3 workers
./swarm-manage.sh deploy

# Peak hours: scale to 10 workers
./swarm-manage.sh scale 10

# Off-peak: scale down to 2 workers
./swarm-manage.sh scale 2
```

### Based on Load

Monitor NSQ queue depth and scale accordingly:

```bash
#!/bin/bash
# Example: auto-scale based on queue depth

QUEUE_DEPTH=$(curl -s http://172.12.0.132:4171/api/topics | jq '.topics[] | select(.name=="bulk_ocr_file_tasks") | .depth')

if [ "$QUEUE_DEPTH" -gt 1000 ]; then
    echo "High load detected: $QUEUE_DEPTH tasks in queue"
    ./swarm-manage.sh scale 10
elif [ "$QUEUE_DEPTH" -lt 100 ]; then
    echo "Low load: $QUEUE_DEPTH tasks in queue"
    ./swarm-manage.sh scale 3
fi
```

## Troubleshooting

### Worker not starting

```bash
# Check logs
./swarm-manage.sh logs

# Check service status
docker service ps gvpocr_ocr-worker --no-trunc
```

### Worker keeps restarting

Check restart policy and logs for errors:

```bash
docker service inspect gvpocr_ocr-worker | grep -A 10 "RestartPolicy"
./swarm-manage.sh logs
```

### Task placement issues

Check node availability:

```bash
docker node ls

# If node is unavailable, restore it:
./swarm-manage.sh restore <node_id>
```

### Network connectivity issues

Verify overlay network:

```bash
docker network ls | grep gvpocr
docker network inspect gvpocr_gvpocr-network
```

## Production Checklist

Before deploying to production:

- [ ] Initialize Docker Swarm on main server
- [ ] Add all worker nodes to swarm
- [ ] Verify SSHFS mounts on all nodes
- [ ] Test network connectivity between nodes
- [ ] Deploy stack with initial replicas
- [ ] Monitor logs and resource usage
- [ ] Set up health checks and alerts
- [ ] Document node IPs and roles
- [ ] Create backup of swarm configuration
- [ ] Test scaling up and down
- [ ] Test node drain and restore
- [ ] Verify automatic restart on failure

## Monitoring and Alerting

### Health Check Endpoint

Workers expose a health check on port 5000:

```bash
curl -f http://worker-ip:5000/health
```

### Prometheus Metrics (Optional)

Add Prometheus scraping to monitor workers:

```yaml
- job_name: 'ocr-workers'
  static_configs:
    - targets: ['localhost:5000']
```

### NSQ Monitoring

Monitor queue depth and consumer lag:

```bash
# View topics and depth
curl -s http://172.12.0.132:4171/api/topics | jq

# View consumer status
curl -s http://172.12.0.132:4161/api/consumers/bulk_ocr_file_tasks | jq
```

## Backup and Recovery

### Backup Swarm Configuration

```bash
# Backup Swarm keys (manager nodes only)
sudo tar -czf swarm-backup.tar.gz /var/lib/docker/swarm/

# Backup stack configuration
cp docker-stack.yml docker-stack.backup.yml
```

### Restore Swarm

If manager fails:

```bash
# On new manager node with backed up config:
sudo tar -xzf swarm-backup.tar.gz -C /

# Restart Docker
sudo systemctl restart docker

# Verify swarm status
docker swarm info
```

## Advanced Topics

### Custom Labels

Add labels to nodes for selective task placement:

```bash
# Label a node
docker node update --label-add type=gpu node-id

# Update stack to use labeled nodes
placement:
  constraints:
    - node.labels.type == gpu
```

### Global Service

Run one worker on every node:

```yaml
deploy:
  mode: global  # Instead of replicated
```

### Rolling Updates

Update service with rolling restart:

```bash
# Update image (rolling restart)
./swarm-manage.sh update --image new-image:v2

# Control update parallelism
docker service update --update-parallelism 1 \
  --update-delay 30s gvpocr_ocr-worker
```

### Service Discovery

Workers are discoverable within the swarm network:

```bash
# From another container in the network:
curl http://gvpocr_ocr-worker:5000/health
```

## Quick Commands

```bash
# Deploy
./swarm-manage.sh deploy

# Check status
./swarm-manage.sh status

# Scale to 5 workers
./swarm-manage.sh scale 5

# View logs
./swarm-manage.sh logs

# Check health
./swarm-manage.sh health

# Restart
./swarm-manage.sh restart

# Remove
./swarm-manage.sh remove

# Get help
./swarm-manage.sh help
```

## Support

For issues or questions:

1. Check logs: `./swarm-manage.sh logs`
2. Check status: `./swarm-manage.sh status`
3. Check health: `./swarm-manage.sh health`
4. Review stack file: `cat docker-stack.yml`
5. Check Docker daemon: `docker info`

---

For more information on Docker Swarm:
- https://docs.docker.com/engine/swarm/
- https://docs.docker.com/engine/swarm/swarm-tutorial/
- https://docs.docker.com/engine/reference/commandline/service/
