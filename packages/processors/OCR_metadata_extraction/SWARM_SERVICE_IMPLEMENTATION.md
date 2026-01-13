# Docker Swarm Management Service & UI Implementation

## Overview

Complete Docker Swarm management system with Python backend service, REST API, and Vue.js frontend UI for controlling OCR workers.

## Components

### 1. Backend Service (`app/services/swarm_service.py`)

#### Features
- **Swarm Management**: Initialize, join, leave swarm
- **Node Management**: List, inspect, update availability, remove nodes
- **Service Management**: Deploy, scale, update, remove services
- **Task Management**: Monitor tasks, view logs
- **Health Monitoring**: Comprehensive health status
- **Statistics**: Cluster metrics and performance data

#### Data Classes
```python
SwarmNode         # Node information
SwarmService      # Service information
SwarmTask         # Task information
SwarmInfo         # Swarm cluster information
```

#### Key Methods

**Swarm Management:**
- `get_swarm_info()` - Get swarm cluster info
- `init_swarm(advertise_addr)` - Initialize swarm
- `leave_swarm(force)` - Leave swarm
- `get_join_token(role)` - Get worker/manager join token

**Node Management:**
- `list_nodes()` - List all nodes
- `inspect_node(node_id)` - Get node details
- `update_node_availability(node_id, availability)` - Drain/restore node
- `remove_node(node_id, force)` - Remove node

**Service Management:**
- `list_services(filters)` - List services
- `scale_service(service_name, replicas)` - Scale service
- `update_service_image(service_name, image)` - Update image
- `remove_service(service_name)` - Remove service
- `deploy_stack(stack_file, stack_name)` - Deploy stack

**Task Management:**
- `list_service_tasks(service_name)` - List service tasks
- `get_service_logs(service_name, tail)` - Get logs

**Health & Diagnostics:**
- `get_health_status()` - Comprehensive health check
- `get_statistics()` - Cluster statistics

### 2. REST API Routes (`app/routes/swarm.py`)

#### Endpoints

**Swarm Information**
```
GET    /api/swarm/info              Get swarm cluster info
POST   /api/swarm/init              Initialize swarm
POST   /api/swarm/leave             Leave swarm
GET    /api/swarm/join-token/<role> Get join token
```

**Node Management**
```
GET    /api/swarm/nodes                    List nodes
GET    /api/swarm/nodes/<node_id>          Inspect node
PUT    /api/swarm/nodes/<node_id>/availability  Update availability
DELETE /api/swarm/nodes/<node_id>          Remove node
```

**Service Management**
```
GET    /api/swarm/services                      List services
POST   /api/swarm/services/<name>/scale         Scale service
PUT    /api/swarm/services/<name>/image         Update image
DELETE /api/swarm/services/<name>               Remove service
```

**Task Management**
```
GET    /api/swarm/services/<name>/tasks    List tasks
GET    /api/swarm/services/<name>/logs     Get logs
```

**Health & Diagnostics**
```
GET    /api/swarm/health             Comprehensive health status
GET    /api/swarm/statistics         Cluster statistics
```

**Stack Deployment**
```
POST   /api/swarm/deploy-stack       Deploy stack
```

### 3. Frontend UI (`frontend/src/components/SwarmManagement.vue`)

#### Features
- **Dashboard**: Real-time metrics and status
- **Services Management**: View, scale, monitor, remove services
- **Nodes Management**: View nodes, drain for maintenance, restore, remove
- **Health Monitoring**: Comprehensive health status with details
- **Statistics**: Cluster and task statistics
- **Logs Viewer**: Real-time service logs
- **Auto-Refresh**: Every 30 seconds

#### Views

**Services Tab**
- List all services with replica counts
- Scale service replicas
- View service logs
- Remove services

**Nodes Tab**
- List all nodes with status
- Drain nodes for maintenance
- Restore drained nodes
- Remove nodes from swarm

**Health Tab**
- Overall swarm health
- Node health metrics
- Service health metrics
- Detailed node status

**Statistics Tab**
- Cluster statistics (nodes, managers, workers)
- Service statistics (total, replicas, running)
- Task statistics (running, failed, pending)

## Error Handling

All methods return tuples with:
```python
(success: bool, data: any, error_message: str)
```

Example:
```python
success, nodes, error = swarm_service.list_nodes()
if not success:
    print(f"Error: {error}")
else:
    print(f"Found {len(nodes)} nodes")
```

## API Response Format

### Success Response
```json
{
  "success": true,
  "data": {...},
  "count": 5
}
```

### Error Response
```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

## Test Cases

### Unit Tests (`tests/test_swarm_service.py`)

**Data Class Tests**
- `test_swarm_node_to_dict()` - SwarmNode serialization
- `test_swarm_service_to_dict()` - SwarmService serialization
- `test_swarm_task_to_dict()` - SwarmTask serialization
- `test_swarm_info_to_dict()` - SwarmInfo serialization

**Service Method Tests**
- `test_list_nodes_success()` - Node listing
- `test_scale_service_success()` - Service scaling
- `test_update_node_availability()` - Node management
- `test_get_health_status()` - Health monitoring
- `test_get_statistics()` - Statistics gathering

**Error Handling Tests**
- `test_docker_exception_handling_list_nodes()` - Exception in list_nodes
- `test_docker_exception_handling_scale_service()` - Exception in scale_service
- `test_update_node_availability_invalid()` - Invalid availability parameter
- `test_scale_service_invalid_replicas()` - Negative replicas

**Integration Tests**
- `test_full_workflow_scale_service()` - List -> Scale -> List workflow
- `test_node_lifecycle()` - List -> Inspect -> Update -> Remove workflow

**API Tests**
- `test_get_swarm_info_endpoint()` - GET /api/swarm/info
- `test_list_nodes_endpoint()` - GET /api/swarm/nodes
- `test_scale_service_endpoint()` - POST /api/swarm/services/*/scale
- `test_get_health_status_endpoint()` - GET /api/swarm/health

## Running Tests

### Run all tests
```bash
cd backend
python -m pytest tests/test_swarm_service.py -v
```

### Run specific test class
```bash
python -m pytest tests/test_swarm_service.py::TestDataClasses -v
```

### Run with coverage
```bash
python -m pytest tests/test_swarm_service.py --cov=app.services.swarm_service
```

## Usage Examples

### Python Backend

```python
from app.services.swarm_service import get_swarm_service

swarm = get_swarm_service()

# List nodes
success, nodes, error = swarm.list_nodes()
for node in nodes:
    print(f"{node.hostname}: {node.status}")

# Scale service
success, msg = swarm.scale_service('ocr-worker', 5)
if success:
    print(f"Scaled successfully: {msg}")

# Get health status
success, health, error = swarm.get_health_status()
if success:
    print(f"Overall health: {health['overall_health']}")
```

### REST API

```bash
# Get swarm info
curl http://localhost:5000/api/swarm/info

# List services
curl http://localhost:5000/api/swarm/services

# Scale service to 5 replicas
curl -X POST http://localhost:5000/api/swarm/services/ocr-worker/scale \
  -H "Content-Type: application/json" \
  -d '{"replicas": 5}'

# Get health status
curl http://localhost:5000/api/swarm/health

# Get service logs
curl 'http://localhost:5000/api/swarm/services/ocr-worker/logs?tail=100'

# Drain node
curl -X PUT http://localhost:5000/api/swarm/nodes/node-id/availability \
  -H "Content-Type: application/json" \
  -d '{"availability": "drain"}'
```

### Vue.js Frontend

```vue
<template>
  <SwarmManagement />
</template>

<script>
import SwarmManagement from '@/components/SwarmManagement.vue'

export default {
  components: { SwarmManagement }
}
</script>
```

## Features

### Real-time Monitoring
- Auto-refresh every 30 seconds
- Live health metrics
- Task status tracking
- Resource usage statistics

### Service Management
- Scale services up/down
- Update container images
- Deploy new stacks
- Remove services
- View service logs

### Node Management
- List all nodes
- Drain nodes for maintenance
- Restore drained nodes
- Remove nodes from swarm
- View node details

### Health Monitoring
- Overall swarm health
- Node health status
- Service availability
- Task success rate
- Error detection

### Statistics
- Cluster metrics
- Service metrics
- Task metrics
- Timestamp for tracking

## Error Handling

All operations include comprehensive error handling:

```python
# Check Docker client availability
if not self._check_client():
    return False, "Docker client not available"

# Validate input parameters
if replicas < 0:
    return False, "Number of replicas must be non-negative"

# Handle Docker exceptions
try:
    ...
except Exception as e:
    logger.error(f"Error: {str(e)}")
    return False, error_message
```

## Integration with Backend

To integrate with your Flask app:

```python
# In app/__init__.py
from app.routes.swarm import register_swarm_routes

def create_app():
    app = Flask(__name__)
    ...
    register_swarm_routes(app)
    return app
```

## Frontend Integration

To add to your Vue app:

1. Import component
```javascript
import SwarmManagement from '@/components/SwarmManagement.vue'
```

2. Add route
```javascript
{
  path: '/swarm',
  name: 'SwarmManagement',
  component: SwarmManagement
}
```

3. Add navigation link
```html
<router-link to="/swarm">Docker Swarm Management</router-link>
```

## Production Checklist

- [ ] Install docker-py: `pip install docker`
- [ ] Verify Docker daemon access
- [ ] Test all API endpoints
- [ ] Run unit tests: `pytest tests/test_swarm_service.py`
- [ ] Configure CORS for frontend
- [ ] Set up logging
- [ ] Test error scenarios
- [ ] Monitor performance
- [ ] Regular backups of configuration

## Dependencies

### Python
```
docker>=4.0
flask>=1.0
```

### Frontend
```
vue>=2.6
bootstrap>=4.0 (for styling)
```

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Prometheus metrics export
- [ ] Advanced filtering and search
- [ ] Service templates
- [ ] Automated scaling policies
- [ ] Event history and audit logs
- [ ] RBAC integration
- [ ] Multi-cluster management

## Troubleshooting

### Docker socket permission denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
sudo systemctl restart docker
```

### Service not found
```bash
# Verify service name
docker service ls

# Use exact service name from 'docker service ls'
curl http://localhost:5000/api/swarm/services/<exact-name>/logs
```

### Connection refused
```bash
# Check Docker daemon
docker ps

# Check API endpoint
curl http://localhost:5000/api/swarm/info
```

## Support

For issues or questions:
1. Check logs: `docker logs <container>`
2. Verify connectivity: `docker ps`
3. Test endpoints: `curl http://localhost:5000/api/swarm/info`
4. Review test cases for examples

---

**Implementation Date**: 2025-12-20  
**Status**: Production Ready  
**Version**: 1.0.0
