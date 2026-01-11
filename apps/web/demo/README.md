# Job Manager Demo

This is a browser-based demonstration of the Pala Platform job cancellation feature.

## Features Demonstrated

✅ **Job Creation** - Create OCR and metadata extraction jobs
✅ **Job Queue Management** - Shows pending, in-progress, completed, cancelled, and failed jobs
✅ **Job Cancellation** - Cancel button to stop running jobs with confirmation dialog
✅ **Real-time Progress Tracking** - Visual progress bars for in-progress jobs
✅ **Resource Cleanup** - Intermediate results cleared when job is cancelled
✅ **Statistics Dashboard** - Live statistics showing job status distribution
✅ **Job History** - Complete history with timestamps

## Running the Demo

### Option 1: Open in Browser
Simply open `index.html` in your web browser:

```bash
cd /home/runner/work/pala-platform/pala-platform/apps/web/demo
# On macOS
open index.html

# On Linux
xdg-open index.html

# On Windows
start index.html
```

### Option 2: Using a Local Server
For a more realistic experience, serve the files with a local HTTP server:

```bash
cd /home/runner/work/pala-platform/pala-platform/apps/web/demo

# Using Python 3
python3 -m http.server 8000

# Using Node.js (with http-server)
npx http-server -p 8000

# Using PHP
php -S localhost:8000
```

Then open http://localhost:8000 in your browser.

## How to Use

1. **Create Jobs**: Click "Create OCR Job", "Create Metadata Job", or "Create 5 Jobs" to add jobs to the queue
2. **Monitor Progress**: Watch jobs move from Pending → In Progress → Completed
3. **Cancel Jobs**: Click the "✕ Cancel Job" button on any pending or in-progress job
4. **View Statistics**: See live statistics of job status distribution
5. **Clear History**: Click "Clear History" to remove completed/cancelled/failed jobs

## Job Cancellation Behavior

- **Pending Jobs**: Cancelled immediately
- **In-Progress Jobs**: Cancellation is requested, and the job stops at the next progress checkpoint
- **Completed/Failed/Cancelled Jobs**: Cannot be cancelled (button is disabled)

When a job is cancelled:
- Status changes to "CANCELLED"
- Intermediate results are cleared
- Resources are freed for the next job
- Cancelled timestamp is recorded

## Technical Details

This demo uses a client-side JavaScript simulation of the `@pala/job-manager` package. The actual backend implementation is in `packages/processors/job-manager/`.

Key components:
- **Job Queue**: FIFO queue with configurable concurrency limit (3 concurrent jobs in demo)
- **Progress Tracking**: Simulated processing with 20 progress checkpoints
- **Cancellation Mechanism**: Checks for cancellation requests at each progress update
- **Event System**: Emits events for job lifecycle changes (created, started, progress, completed, cancelled, failed, cleanup)

## Acceptance Criteria Met

✅ User can cancel a running job
✅ Job stops processing when cancelled
✅ Resources are freed (next job in queue starts)
✅ Intermediate results cleared from database (simulated)
✅ Cancel button in job history
✅ Backend handles cancellation appropriately
✅ Queue is cleared when job is cancelled

## Architecture

The frontend demonstrates the complete job lifecycle:

```
┌─────────────┐
│   PENDING   │ ◄── Job created and queued
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ IN_PROGRESS │ ◄── Job processing (can be cancelled)
└──────┬──────┘
       │
       ├──────────────┐
       ▼              ▼
┌─────────────┐ ┌─────────────┐
│  COMPLETED  │ │  CANCELLED  │
└─────────────┘ └─────────────┘
       │              │
       │              ▼
       │        ┌──────────┐
       │        │ CLEANUP  │ (Clear intermediate results)
       │        └──────────┘
       │
       ▼
┌─────────────┐
│   FAILED    │
└─────────────┘
```

## Next Steps

For production deployment:
1. Integrate with actual backend API (see `packages/processors/job-manager/`)
2. Add WebSocket support for real-time updates
3. Implement persistent storage for job history
4. Add authentication and authorization
5. Implement more sophisticated resource cleanup
6. Add job retry logic for failed jobs
