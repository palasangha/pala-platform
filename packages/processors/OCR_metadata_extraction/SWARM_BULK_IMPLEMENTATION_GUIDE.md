# Docker Swarm + Bulk Processing: Implementation Guide

## Quick Summary

To make Docker Swarm work with bulk processing, you need to:

1. **Route bulk jobs through NSQ** (already done via `NSQJobCoordinator`)
2. **Deploy swarm worker services** that consume from NSQ
3. **Scale services based on job size** before processing starts
4. **Aggregate results** from all workers into final reports

## Implementation Steps

### Step 1: Modify BulkProcessor to Use NSQ Instead of Local Threads

**File: `backend/app/services/bulk_processor.py`**

Currently uses `ThreadPoolExecutor` locally. Change to use NSQ:

```python
class BulkProcessor:
    def __init__(self, use_nsq: bool = True, **kwargs):
        self.use_nsq = use_nsq
        if self.use_nsq:
            from .nsq_service import NSQService
            self.nsq_service = NSQService()
    
    def process_folder(self, folder_path, provider, languages, handwriting, recursive=True, use_swarm=False):
        """Process folder - either locally or via NSQ workers"""
        
        if self.use_nsq or use_swarm:
            # Use NSQ-based distributed processing
            return self._process_via_nsq(folder_path, provider, languages, handwriting, recursive)
        else:
            # Use local ThreadPoolExecutor (existing)
            return self._process_locally(folder_path, provider, languages, handwriting, recursive)
    
    def _process_via_nsq(self, folder_path, provider, languages, handwriting, recursive):
        """Publish all files to NSQ queue for workers to process"""
        from app.services.nsq_job_coordinator import NSQJobCoordinator
        
        coordinator = NSQJobCoordinator()
        job_id = str(uuid.uuid4())
        
        # Scan folder
        image_files = coordinator.scan_folder(folder_path, recursive)
        
        # Initialize job
        BulkJob.initialize_nsq_job(self.mongo, job_id, len(image_files))
        
        # Publish all tasks to NSQ
        for idx, file_path in enumerate(image_files):
            self.nsq_service.publish_file_task(
                job_id=job_id,
                file_path=file_path,
                file_index=idx,
                total_files=len(image_files),
                provider=provider,
                languages=languages,
                handwriting=handwriting
            )
        
        # Return job info (actual processing happens in background via workers)
        return {
            'job_id': job_id,
            'total_files': len(image_files),
            'status': 'queued'
        }
```

### Step 2: Add Swarm Service Scaling to Bulk Route

**File: `backend/app/routes/bulk.py`**

```python
from app.services.swarm_service import DockerSwarmService
from app.services.swarm_bulk_processor import SwarmBulkProcessor

@bulk_bp.route('/process', methods=['POST'])
@token_required
def process_bulk(current_user_id):
    """
    Bulk process folder
    
    New parameter: use_swarm (bool) - Use Docker Swarm for processing
    """
    data = request.get_json()
    use_swarm = data.get('use_swarm', False)
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    try:
        if use_swarm:
            # Scale up swarm services before starting job
            swarm_processor = SwarmBulkProcessor()
            required_replicas = swarm_processor.estimate_required_replicas(
                folder_path=data['folder_path'],
                recursive=data.get('recursive', True)
            )
            
            logger.info(f"Bulk job {job_id}: Scaling to {required_replicas} replicas")
            
            # Scale the OCR worker service
            provider = data.get('provider', 'tesseract')
            service_name = f"ocr-worker-{provider}"
            
            success, msg = swarm_processor.scale_service(service_name, required_replicas)
            if not success:
                logger.warning(f"Failed to scale service: {msg}")
                # Continue anyway, use available replicas
        
        # Start job (will use NSQ)
        processor = BulkProcessor(use_nsq=True)
        result = processor.process_folder(
            folder_path=data['folder_path'],
            provider=data.get('provider', 'tesseract'),
            languages=data.get('languages', ['en']),
            handwriting=data.get('handwriting', False),
            recursive=data.get('recursive', True),
            use_swarm=use_swarm
        )
        
        return jsonify({
            'success': True,
            'job_id': result['job_id'],
            'total_files': result['total_files'],
            'status': result['status'],
            'use_swarm': use_swarm
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting bulk job: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### Step 3: Create SwarmBulkProcessor Service

**File: `backend/app/services/swarm_bulk_processor.py` (NEW)**

```python
"""Service for managing bulk processing via Docker Swarm"""

import logging
import os
from pathlib import Path
from app.services.swarm_service import DockerSwarmService
from app.services.nsq_job_coordinator import NSQJobCoordinator

logger = logging.getLogger(__name__)


class SwarmBulkProcessor:
    """Manages bulk processing via Docker Swarm worker services"""
    
    def __init__(self):
        self.swarm_service = DockerSwarmService()
        self.nsq_coordinator = NSQJobCoordinator()
        
        # Configuration
        self.files_per_worker = int(os.getenv('SWARM_FILES_PER_WORKER', '100'))
        self.max_replicas = int(os.getenv('SWARM_MAX_REPLICAS', '10'))
    
    def estimate_required_replicas(self, folder_path, recursive=True):
        """
        Estimate number of worker replicas needed for a job
        
        Args:
            folder_path: Path to folder with images
            recursive: Whether to scan subfolders
            
        Returns:
            int: Recommended number of replicas
        """
        try:
            # Scan folder to count files
            image_files = self.nsq_coordinator.scan_folder(folder_path, recursive)
            total_files = len(image_files)
            
            logger.info(f"Found {total_files} files in {folder_path}")
            
            # Estimate replicas (1 worker per N files)
            estimated = max(1, total_files // self.files_per_worker)
            
            # Get current swarm capacity
            success, nodes, error = self.swarm_service.list_nodes()
            if not success:
                logger.warning(f"Could not get node count: {error}")
                return estimated
            
            worker_nodes = [n for n in nodes if not n.is_manager]
            available_workers = len(worker_nodes)
            
            # Don't request more replicas than available nodes * 2 (2x oversubscription)
            max_available = max(1, available_workers * 2)
            
            recommended = min(estimated, max_available, self.max_replicas)
            
            logger.info(f"Recommending {recommended} replicas ({available_workers} worker nodes available)")
            
            return recommended
            
        except Exception as e:
            logger.error(f"Error estimating replicas: {str(e)}")
            return 1  # Default to 1 replica on error
    
    def scale_service(self, service_name, replicas, timeout=300):
        """
        Scale a swarm service to desired replica count
        
        Args:
            service_name: Name of the service (e.g., "ocr-worker-tesseract")
            replicas: Desired number of replicas
            timeout: Max seconds to wait for replicas to be ready
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            logger.info(f"Scaling service {service_name} to {replicas} replicas")
            
            # Get current state
            success, current_state, error = self.get_service_state(service_name)
            if not success:
                return False, f"Could not get service state: {error}"
            
            current_replicas = current_state.get('replicas', 1)
            
            if current_replicas == replicas:
                logger.info(f"Service already at {replicas} replicas")
                return True, f"Service already at {replicas} replicas"
            
            # Scale the service
            success, msg = self.swarm_service.scale_service(service_name, replicas)
            
            if not success:
                return False, f"Failed to scale service: {msg}"
            
            logger.info(f"Successfully scaled {service_name} to {replicas} replicas")
            
            # Return immediately - let replicas come up asynchronously
            return True, f"Scaling {service_name} to {replicas} replicas"
            
        except Exception as e:
            logger.error(f"Error scaling service: {str(e)}")
            return False, str(e)
    
    def get_service_state(self, service_name):
        """
        Get current state of a service
        
        Returns:
            Tuple[bool, dict, str]: (success, state_dict, error_message)
        """
        try:
            success, services, error = self.swarm_service.list_services()
            
            if not success:
                return False, {}, error
            
            for service in services:
                if service.name == service_name:
                    return True, {
                        'name': service.name,
                        'replicas': service.replicas,
                        'running': service.running_count,
                        'desired': service.desired_count,
                        'status': 'healthy' if service.running_count == service.desired_count else 'degraded'
                    }, ""
            
            return False, {}, f"Service {service_name} not found"
            
        except Exception as e:
            logger.error(f"Error getting service state: {str(e)}")
            return False, {}, str(e)
    
    def wait_for_replicas(self, service_name, expected_replicas, timeout=300):
        """
        Wait for service to reach desired replica count
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        import time
        
        start_time = time.time()
        check_interval = 5
        
        while time.time() - start_time < timeout:
            success, state, error = self.get_service_state(service_name)
            
            if not success:
                logger.warning(f"Could not get service state: {error}")
                time.sleep(check_interval)
                continue
            
            running = state.get('running', 0)
            
            if running >= expected_replicas:
                logger.info(f"Service {service_name} reached {expected_replicas} replicas")
                return True, f"Service ready with {running} replicas"
            
            logger.debug(f"Waiting for replicas: {running}/{expected_replicas}")
            time.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for {service_name} to reach {expected_replicas} replicas")
        return False, f"Timeout waiting for replicas (got {state.get('running', 0)}/{expected_replicas})"
    
    def scale_back_after_job(self, service_name, target_replicas=1):
        """
        Scale service back to normal after job completion
        
        Args:
            service_name: Service to scale back
            target_replicas: Number of replicas to scale back to (default: 1)
        """
        try:
            logger.info(f"Scaling {service_name} back to {target_replicas} replicas")
            success, msg = self.scale_service(service_name, target_replicas)
            if success:
                logger.info(f"Successfully scaled back: {msg}")
            else:
                logger.warning(f"Failed to scale back: {msg}")
        except Exception as e:
            logger.error(f"Error scaling back service: {str(e)}")
```

### Step 4: Update Frontend to Support Swarm Processing

**File: `frontend/src/components/BulkOCR/BulkOCRProcessor.tsx`**

Add checkbox to enable swarm processing:

```typescript
interface BulkProcessingState {
  // ... existing fields ...
  useSwarm: boolean;  // NEW
  autoScale: boolean; // NEW
}

// In the component JSX, add to Advanced Options section:

<div className="mb-4">
  <label className="flex items-center gap-2">
    <input
      type="checkbox"
      checked={state.useSwarm}
      onChange={(e) => setState({ ...state, useSwarm: e.target.checked })}
      disabled={state.isProcessing}
      className="rounded border-gray-300"
    />
    <span className="text-sm font-medium text-gray-700">
      Use Docker Swarm for distributed processing
    </span>
  </label>
  <p className="text-xs text-gray-500 mt-2">
    💡 Recommended for large batches (100+ files). Distributes processing across available worker nodes.
  </p>
</div>

{state.useSwarm && (
  <div className="mb-4">
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={state.autoScale}
        onChange={(e) => setState({ ...state, autoScale: e.target.checked })}
        disabled={state.isProcessing}
        className="rounded border-gray-300"
      />
      <span className="text-sm font-medium text-gray-700">
        Auto-scale workers based on job size
      </span>
    </label>
    <p className="text-xs text-gray-500 mt-2">
      💡 Automatically scales up workers for this job, then scales back down when complete.
    </p>
  </div>
)}

// Update handleProcessing to include new parameters:
const handleProcessing = async () => {
  // ...
  const response = await authenticatedFetch('/api/bulk/process', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      folder_path: state.folderPath,
      recursive: state.recursive,
      provider: state.provider,
      languages: state.languages,
      handwriting: state.handwriting,
      export_formats: state.exportFormats,
      use_swarm: state.useSwarm,    // NEW
      auto_scale: state.autoScale,  // NEW
    }),
  });
  // ...
}
```

### Step 5: Configure Worker Services in Docker Compose

**File: `docker-stack.yml`**

```yaml
version: '3.8'

services:
  ocr-worker-tesseract:
    image: registry.docgenai.com:5010/gvpocr-worker:latest
    environment:
      - NSQD_ADDRESS=nsqd:4150
      - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
      - MONGO_URI=mongodb://mongo:27017/gvpocr
      - PROVIDER=tesseract
      - WORKER_MODE=distributed
    deploy:
      mode: replicated
      replicas: 1  # Start with 1, will be scaled up as needed
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      placement:
        constraints:
          - node.role == worker
    networks:
      - gvpocr-network

  ocr-worker-easyocr:
    image: registry.docgenai.com:5010/gvpocr-worker:latest
    environment:
      - NSQD_ADDRESS=nsqd:4150
      - NSQLOOKUPD_ADDRESSES=nsqlookupd:4161
      - MONGO_URI=mongodb://mongo:27017/gvpocr
      - PROVIDER=easyocr
      - WORKER_MODE=distributed
    deploy:
      mode: replicated
      replicas: 1
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      placement:
        constraints:
          - node.role == worker
    networks:
      - gvpocr-network

networks:
  gvpocr-network:
    driver: overlay
```

## Environment Configuration

Add to `.env`:

```bash
# Bulk Processing Configuration
USE_NSQ_FOR_BULK=true
USE_SWARM_FOR_BULK=true

# Swarm Configuration
SWARM_FILES_PER_WORKER=100
SWARM_MAX_REPLICAS=10
SWARM_AUTO_SCALE_ENABLED=true
SWARM_WORKER_SERVICE_NAMES=ocr-worker-tesseract,ocr-worker-easyocr,ocr-worker-google_vision
```

## Database Schema Updates

Add fields to `BulkJob` model:

```python
class BulkJob:
    """MongoDB schema for bulk processing jobs"""
    
    # Existing fields
    _id: ObjectId
    user_id: str
    folder_path: str
    provider: str
    languages: List[str]
    total_files: int
    
    # New fields for swarm support
    use_swarm: bool = False
    auto_scale: bool = False
    initial_replicas: int = 1
    final_replicas: int = 1
    swarm_nodes_used: List[str] = []
    
    # Progress tracking
    published_count: int = 0
    processed_count: int = 0
    failed_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime]
    
    # Results
    results: List[dict] = []
    aggregated_results: Optional[dict]
```

## Testing

### Test 1: Basic Swarm Processing

```bash
# Start swarm mode
docker swarm init

# Deploy test stack
docker stack deploy -c docker-stack.yml gvpocr

# Trigger bulk job via API
curl -X POST http://localhost:5000/api/bulk/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/data/test-images",
    "provider": "tesseract",
    "use_swarm": true,
    "auto_scale": true
  }'

# Monitor progress
curl http://localhost:5000/api/bulk/progress/$JOB_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Test 2: Auto-Scaling

```bash
# Start with 100 files - should scale to 1 replica
# Start with 500 files - should scale to 5 replicas
# Start with 1000 files - should scale to 10 replicas (capped)

# Monitor replica count
docker service ls
docker service ps ocr-worker-tesseract
```

## Monitoring & Debugging

### Check Swarm Status

```bash
docker node ls
docker service ls
docker service ps ocr-worker-tesseract
```

### Check NSQ Queue

```bash
# Get topic stats
curl http://nsqd:4151/api/topics | jq '.data.topics[] | select(.name=="bulk_ocr_file_tasks")'
```

### Check MongoDB Job Status

```bash
mongosh
use gvpocr
db.bulk_jobs.findOne({_id: "job_id_here"})
db.bulk_jobs.findOne({_id: "job_id_here"}).results.length
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Jobs stuck in "queued" | Workers not consuming | Check NSQ consumer health |
| Slow scaling | Node startup time | Pre-warm nodes or increase startup timeout |
| Memory errors on workers | Job too large for workers | Increase memory limits or reduce batch size |
| Results not aggregating | MongoDB connection issue | Check MONGO_URI, network connectivity |

## Performance Tips

1. **Batch Size**: Use 100-200 files per worker for optimal performance
2. **Resource Allocation**: CPU > Memory (OCR is CPU-bound)
3. **Provider Selection**: Faster providers (Tesseract) for large jobs
4. **Warm-up Time**: Allow 30-60 seconds for service startup
5. **Network**: Ensure low-latency NSQ/MongoDB access

## Next Steps

1. Implement result aggregation from multiple workers
2. Add real-time progress dashboard showing worker activity
3. Implement job persistence (pause/resume)
4. Add cost estimation for swarm processing
5. Implement predictive scaling based on historical data
