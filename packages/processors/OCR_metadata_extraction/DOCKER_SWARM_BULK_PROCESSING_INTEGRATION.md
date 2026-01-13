# Docker Swarm Integration with Bulk Processing

## Overview

This document outlines how to integrate Docker Swarm with bulk OCR processing to enable scalable, distributed processing of large image batches across multiple nodes.

## Current Architecture

### Existing Components

1. **Bulk Processing Frontend** (`BulkOCRProcessor.tsx`)
   - User selects folder and OCR parameters
   - Submits `/api/bulk/process` request
   - Polls `/api/bulk/progress/{job_id}` for status
   - Downloads results

2. **Bulk Job Coordinator** (`bulk_processor.py`)
   - Scans folders for image files
   - Uses ThreadPoolExecutor for local parallel processing
   - Limited to single machine CPU cores

3. **NSQ Queue System** (`nsq_service.py`)
   - Message queue for distributed task processing
   - Workers consume tasks from NSQ topics
   - Already integrated with bulk processing

4. **Supervisor Service** (`supervisor_service.py`)
   - Deploys workers via SSH
   - Manages worker lifecycle (start, stop, scale)
   - Uses NSQ for job coordination

5. **Docker Swarm Service** (`swarm_service.py`)
   - Manages swarm nodes and services
   - Can scale services up/down
   - Not yet integrated with bulk processing

## Integration Strategy

### Phase 1: Swarm-Aware Bulk Job Routing

**Goal:** Route bulk jobs to swarm services instead of local processing

**Changes needed:**

1. **Modify Bulk Processor** (`bulk_processor.py`)
   ```python
   class BulkProcessor:
       def __init__(self, use_swarm: bool = False, swarm_service_name: str = None):
           self.use_swarm = use_swarm
           self.swarm_service_name = swarm_service_name
           
       def process_folder_via_swarm(self, folder_path, provider, languages, handwriting, recursive=True):
           """
           Process folder via Docker Swarm services instead of local threads
           
           1. Get list of available swarm nodes
           2. Estimate job size and required replicas
           3. Scale swarm service to meet demand
           4. Distribute tasks across swarm via NSQ
           """
   ```

2. **Modify Bulk Route** (`routes/bulk.py`)
   ```python
   @bulk_bp.route('/process', methods=['POST'])
   def process_bulk():
       # Check if swarm is available and enabled
       if should_use_swarm():
           return process_via_swarm()
       else:
           return process_locally()
   ```

### Phase 2: Smart Service Scaling

**Goal:** Automatically scale swarm services based on job size

**Implementation:**

```python
class SwarmBulkProcessor:
    def estimate_required_replicas(self, total_files, files_per_worker=100):
        """
        Estimate number of replicas needed based on job size
        
        Factors:
        - Total files to process
        - Average processing time per file
        - Available swarm nodes
        - Current node load
        """
        # Default: 1 replica per 100-200 files per worker
        base_replicas = max(1, total_files // files_per_worker)
        
        # Get available worker nodes
        available_workers = self.get_available_worker_nodes()
        
        # Cap replicas to available workers
        max_replicas = len(available_workers) * 2  # Allow 2x oversubscription
        
        return min(base_replicas, max_replicas)
    
    def scale_service_for_job(self, job_size, provider):
        """
        Temporarily scale service for a specific job, then scale back
        """
        required_replicas = self.estimate_required_replicas(job_size)
        service_name = f"ocr-worker-{provider}"
        
        # Get current replica count
        current_replicas = self.get_service_replicas(service_name)
        
        # Scale up if needed
        if required_replicas > current_replicas:
            logger.info(f"Scaling {service_name} from {current_replicas} to {required_replicas} replicas")
            self.scale_service(service_name, required_replicas)
            
            # Wait for new replicas to be ready
            self.wait_for_replicas(service_name, required_replicas, timeout=300)
        
        return required_replicas
```

### Phase 3: Progress Tracking Across Swarm

**Goal:** Track progress from multiple swarm nodes for a single bulk job

**Implementation:**

```python
class SwarmProgressTracker:
    def __init__(self, job_id, mongo):
        self.job_id = job_id
        self.mongo = mongo
    
    def aggregate_progress(self):
        """
        Get aggregated progress from all swarm tasks for this job
        
        Each task writes progress updates to MongoDB:
        - File processed
        - Status (success/failure)
        - Confidence score
        - Processing time
        """
        # Get job from MongoDB
        job = self.mongo.db.bulk_jobs.find_one({'_id': self.job_id})
        
        # Aggregate stats from processed files
        processed = job.get('processed_count', 0)
        failed = job.get('failed_count', 0)
        total = job.get('total_files', 0)
        
        return {
            'current': processed,
            'total': total,
            'percentage': (processed / total * 100) if total > 0 else 0,
            'failed': failed,
            'status': 'processing'
        }
    
    def update_from_task_result(self, file_path, result):
        """
        Called when a swarm task completes
        Update bulk job progress in MongoDB
        """
        self.mongo.db.bulk_jobs.update_one(
            {'_id': self.job_id},
            {
                '$inc': {'processed_count': 1},
                '$push': {
                    'results': {
                        'file': file_path,
                        'status': result.get('status'),
                        'confidence': result.get('confidence'),
                        'text': result.get('text'),
                        'timestamp': datetime.utcnow()
                    }
                }
            }
        )
```

### Phase 4: Unified Result Aggregation

**Goal:** Collect results from all swarm tasks into single report

**Implementation:**

```python
class SwarmResultAggregator:
    def aggregate_bulk_results(self, job_id, export_formats=['json', 'csv', 'text']):
        """
        Aggregate results from all task results and generate reports
        
        Process:
        1. Query MongoDB for all task results for this job
        2. Aggregate statistics
        3. Generate reports in requested formats
        4. Create zip archive
        """
        job = self.mongo.db.bulk_jobs.find_one({'_id': job_id})
        results = list(self.mongo.db.task_results.find({'job_id': job_id}))
        
        # Aggregate statistics
        summary = {
            'total_files': job['total_files'],
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'statistics': {
                'total_characters': sum(len(r.get('text', '')) for r in results),
                'average_confidence': self._calculate_avg_confidence(results),
                'languages': self._extract_languages(results),
            }
        }
        
        # Generate reports
        reports = {}
        if 'json' in export_formats:
            reports['json'] = self._generate_json_report(results, summary)
        if 'csv' in export_formats:
            reports['csv'] = self._generate_csv_report(results, summary)
        if 'text' in export_formats:
            reports['text'] = self._generate_text_report(results, summary)
        
        # Create zip archive
        return self._create_results_archive(reports)
```

## API Changes Required

### 1. Modify `/api/bulk/process` Endpoint

**Current behavior:** 
- Uses local ThreadPoolExecutor
- Single machine bottleneck

**New behavior:**
```python
@bulk_bp.route('/process', methods=['POST'])
@token_required
def process_bulk_via_swarm(current_user_id):
    """
    Start bulk processing with optional swarm routing
    
    Request body:
    {
        "folder_path": "/path/to/images",
        "provider": "tesseract",
        "languages": ["en"],
        "use_swarm": true,  # NEW: Enable swarm processing
        "auto_scale": true, # NEW: Auto-scale swarm services
        "export_formats": ["json", "csv"]
    }
    """
    data = request.get_json()
    use_swarm = data.get('use_swarm', False)
    
    if use_swarm:
        return start_swarm_bulk_job(data, current_user_id)
    else:
        return start_local_bulk_job(data, current_user_id)
```

### 2. New Swarm-Specific Endpoints

```python
@supervisor_bp.route('/swarm/bulk-status/<job_id>', methods=['GET'])
def get_swarm_bulk_status(job_id):
    """Get detailed status of swarm-based bulk job"""
    pass

@supervisor_bp.route('/swarm/auto-scale/<job_id>', methods=['POST'])
def enable_auto_scaling(job_id):
    """Enable/disable auto-scaling for a job"""
    pass

@supervisor_bp.route('/swarm/services/worker-count', methods=['GET'])
def get_worker_service_count():
    """Get current replica count for OCR worker services"""
    pass
```

## Configuration

### Environment Variables

```bash
# Enable Docker Swarm for bulk processing
ENABLE_SWARM_BULK_PROCESSING=true

# Swarm worker service name
SWARM_WORKER_SERVICE_NAME=ocr-worker

# Files per worker (for auto-scaling estimation)
SWARM_FILES_PER_WORKER=100

# Maximum replicas allowed in swarm
SWARM_MAX_REPLICAS=10

# Auto-scaling enabled by default
SWARM_AUTO_SCALE_ENABLED=true
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  ocr-worker:
    image: registry.docgenai.com:5010/gvpocr-worker:latest
    environment:
      - NSQD_ADDRESS=${NSQD_ADDRESS}
      - MONGO_URI=${MONGO_URI}
      - SWARM_MODE=true
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
```

## Workflow Example

### User Initiates Bulk Processing via Swarm

```
Frontend                Backend             NSQ Queue           Swarm
   |                       |                    |                |
   |--POST /bulk/process   |                    |                |
   |     (use_swarm=true)  |                    |                |
   |                       |                    |                |
   |                       |--Scan folder       |                |
   |                       |  (100 files)       |                |
   |                       |                    |                |
   |                       |--Estimate replicas |                |
   |                       |  (need 2 workers)  |                |
   |                       |                    |                |--Scale service
   |                       |                    |                |  to 2 replicas
   |                       |                    |                |
   |                       |--Publish 100 tasks |                |
   |                       |  to NSQ            |-->Task 1       |
   |                       |                    |-->Task 2       |
   |                       |                    |-->Task 3...    |
   |                       |                    |                |--Worker 1
   |<--202 Accepted       |                    |                |  processes task
   |   job_id             |                    |                |
   |                       |                    |                |--Worker 2
   |--GET /progress/id    |                    |                |  processes task
   |     (poll)           |                    |                |
   |                       |--Aggregate from    |                |
   |<--Progress {50%}     |  MongoDB            |                |
   |                       |                    |                |
   |                       |                    |                |<--Complete
   |--GET /results/id    |                    |                |  task results
   |                       |--Combine results   |                |
   |<--Results ZIP        |  from all workers  |                |
   |                       |                    |                |
```

## Benefits

1. **Scalability**: Process 1000s of files across multiple machines
2. **Performance**: Linear scaling with number of worker nodes
3. **Flexibility**: Use swarm for large jobs, local for small jobs
4. **Resource Efficiency**: Auto-scale based on job size
5. **Fault Tolerance**: Node failures don't stop entire job
6. **Progress Visibility**: Real-time progress from multiple sources

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Task redistribution on node failure | Implement job retry logic with NSQ requeue |
| Progress tracking complexity | Centralize in MongoDB with atomic updates |
| Result aggregation performance | Use MongoDB aggregation pipeline |
| Service scaling timing | Pre-warm nodes during low-usage periods |
| Network overhead | Batch results in memory before DB write |

## Migration Path

1. **Week 1-2**: Implement Phase 1 (basic swarm routing)
2. **Week 2-3**: Implement Phase 2 (auto-scaling)
3. **Week 3-4**: Implement Phase 3 (progress tracking)
4. **Week 4-5**: Implement Phase 4 (result aggregation)
5. **Week 5+**: Testing, optimization, deployment

## Testing Strategy

1. **Unit tests**: Individual components
2. **Integration tests**: End-to-end bulk processing
3. **Load tests**: 1000s of files across swarm
4. **Failure tests**: Node down scenarios
5. **Performance tests**: Compare local vs swarm processing time

## Monitoring & Observability

Add metrics for:
- Job completion time (local vs swarm)
- Worker utilization rates
- Task failure rates
- Progress update latency
- Resource consumption per job

## Future Enhancements

1. **Predictive Scaling**: Use ML to predict optimal replica count
2. **Heterogeneous Workers**: Different worker specs for different providers
3. **Cost Optimization**: Route jobs to cheapest available nodes
4. **Multi-Cloud Support**: Extend to Kubernetes/ECS
5. **Real-time Analytics**: Live dashboard with swarm insights
