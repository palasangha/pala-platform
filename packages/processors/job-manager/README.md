# Job Manager

Job management service for Pala Platform processors with support for job cancellation, queuing, and progress tracking.

## Features

- ✅ Job queue management
- ✅ Job cancellation with resource cleanup
- ✅ Progress tracking
- ✅ Concurrent job processing with configurable limits
- ✅ Event-based status updates
- ✅ Automatic cleanup of intermediate results on cancellation

## Installation

```bash
pnpm install @pala/job-manager
```

## Usage

### Basic Setup

```typescript
import { JobManager, JobStatus } from '@pala/job-manager';

// Create job manager with max 5 concurrent jobs
const jobManager = new JobManager(5);

// Register a processor for a job type
jobManager.registerProcessor('ocr', async (job, updateProgress) => {
  // Simulate OCR processing
  for (let i = 0; i <= 100; i += 10) {
    await new Promise(resolve => setTimeout(resolve, 100));
    updateProgress(i); // Update progress, will throw if job is cancelled
  }
  return { text: 'Processed text...' };
});

// Create a job
const job = jobManager.createJob('ocr', { 
  documentId: '123',
  filePath: '/path/to/document.pdf'
});

console.log('Job created:', job.id);
```

### Cancelling Jobs

```typescript
// Cancel a job
await jobManager.cancelJob(job.id);

// The job status will be updated to CANCELLED
// Intermediate results will be cleaned up
// The 'job:cancelled' event will be emitted
```

### Listening to Events

```typescript
jobManager.on('job:created', (job) => {
  console.log('Job created:', job.id);
});

jobManager.on('job:started', (job) => {
  console.log('Job started:', job.id);
});

jobManager.on('job:progress', (job) => {
  console.log(`Job ${job.id} progress: ${job.progress}%`);
});

jobManager.on('job:completed', (job) => {
  console.log('Job completed:', job.id, job.result);
});

jobManager.on('job:cancelled', (job) => {
  console.log('Job cancelled:', job.id);
});

jobManager.on('job:failed', (job) => {
  console.log('Job failed:', job.id, job.error);
});

jobManager.on('job:cleanup', (job) => {
  // Perform additional cleanup (e.g., delete temporary files)
  console.log('Cleaning up job:', job.id);
});
```

### Getting Job Information

```typescript
// Get a specific job
const job = jobManager.getJob('job_123');

// Get all jobs
const allJobs = jobManager.getAllJobs();

// Get statistics
const stats = jobManager.getStats();
console.log(stats);
// {
//   total: 10,
//   pending: 2,
//   inProgress: 3,
//   completed: 4,
//   cancelled: 1,
//   failed: 0
// }
```

### Clearing Old Jobs

```typescript
// Clear jobs older than 24 hours (default)
const clearedCount = jobManager.clearHistory();

// Clear jobs older than 1 hour
const clearedCount = jobManager.clearHistory(60 * 60 * 1000);
```

## Job Lifecycle

1. **PENDING** - Job is created and waiting to be processed
2. **IN_PROGRESS** - Job is currently being processed
3. **COMPLETED** - Job finished successfully
4. **CANCELLED** - Job was cancelled by user
5. **FAILED** - Job failed with an error

## Cancellation Behavior

When a job is cancelled:

- If **PENDING**: Immediately transitions to CANCELLED status
- If **IN_PROGRESS**: Processor is notified via exception when `updateProgress()` is called, allowing graceful cleanup
- Intermediate results are cleared from the job object
- `job:cleanup` event is emitted for external cleanup handlers
- Resources are freed for the next job in the queue

## API Reference

### JobManager

#### Constructor
- `constructor(maxConcurrentJobs?: number)` - Create a new JobManager instance

#### Methods
- `registerProcessor(jobType: string, processor: JobProcessor): void` - Register a job processor
- `createJob(type: string, data: any): Job` - Create and queue a new job
- `getJob(jobId: string): Job | undefined` - Get a job by ID
- `getAllJobs(): Job[]` - Get all jobs
- `cancelJob(jobId: string): Promise<boolean>` - Cancel a job
- `getStats(): object` - Get queue statistics
- `clearHistory(olderThanMs?: number): number` - Clear old jobs from history

#### Events
- `job:created` - Job created
- `job:started` - Job processing started
- `job:progress` - Job progress updated
- `job:completed` - Job completed successfully
- `job:cancelled` - Job cancelled
- `job:cancelling` - Job cancellation requested (for in-progress jobs)
- `job:failed` - Job failed
- `job:cleanup` - Job cleanup needed (emitted on cancellation)

## License

MIT
