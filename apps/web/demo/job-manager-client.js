// Simple in-browser job manager simulation
// This demonstrates the job cancellation feature

class JobManagerClient {
    constructor() {
        this.jobs = new Map();
        this.processingJobs = new Set();
        this.cancelRequests = new Set();
        this.maxConcurrentJobs = 3;
        this.eventCallbacks = new Map();
        
        // Auto-refresh UI
        setInterval(() => this.updateUI(), 500);
    }

    on(event, callback) {
        if (!this.eventCallbacks.has(event)) {
            this.eventCallbacks.set(event, []);
        }
        this.eventCallbacks.get(event).push(callback);
    }

    emit(event, data) {
        const callbacks = this.eventCallbacks.get(event) || [];
        callbacks.forEach(cb => cb(data));
    }

    generateId() {
        return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    createJob(type, data) {
        const job = {
            id: this.generateId(),
            type,
            status: 'pending',
            progress: 0,
            data,
            createdAt: new Date()
        };

        this.jobs.set(job.id, job);
        this.emit('job:created', job);
        this.processNextJob();
        this.updateUI();
        
        return job;
    }

    async cancelJob(jobId) {
        const job = this.jobs.get(jobId);
        
        if (!job) {
            console.error(`Job ${jobId} not found`);
            return false;
        }

        if (['completed', 'failed', 'cancelled'].includes(job.status)) {
            return false;
        }

        if (job.status === 'pending') {
            job.status = 'cancelled';
            job.cancelledAt = new Date();
            this.emit('job:cancelled', job);
            this.updateUI();
            return true;
        }

        if (job.status === 'in_progress') {
            this.cancelRequests.add(jobId);
            console.log(`Cancellation requested for job ${jobId}`);
            return true;
        }

        return false;
    }

    async processNextJob() {
        if (this.processingJobs.size >= this.maxConcurrentJobs) {
            return;
        }

        const pendingJob = Array.from(this.jobs.values()).find(
            job => job.status === 'pending'
        );

        if (!pendingJob) {
            return;
        }

        await this.processJob(pendingJob);
    }

    async processJob(job) {
        job.status = 'in_progress';
        job.startedAt = new Date();
        this.processingJobs.add(job.id);
        this.emit('job:started', job);
        this.updateUI();

        try {
            // Simulate job processing
            const steps = 20;
            for (let i = 0; i <= steps; i++) {
                // Check for cancellation
                if (this.cancelRequests.has(job.id)) {
                    throw new Error('Job cancelled');
                }

                job.progress = Math.round((i / steps) * 100);
                this.emit('job:progress', job);
                this.updateUI();
                
                // Simulate work with random duration
                await new Promise(resolve => setTimeout(resolve, Math.random() * 500 + 200));
            }

            // Check one last time before completion
            if (this.cancelRequests.has(job.id)) {
                throw new Error('Job cancelled');
            }

            job.status = 'completed';
            job.progress = 100;
            job.completedAt = new Date();
            job.result = { success: true, processedAt: new Date() };
            this.emit('job:completed', job);
        } catch (error) {
            if (this.cancelRequests.has(job.id)) {
                job.status = 'cancelled';
                job.cancelledAt = new Date();
                this.cancelRequests.delete(job.id);
                // Clear intermediate results
                delete job.result;
                this.emit('job:cancelled', job);
                this.emit('job:cleanup', job);
            } else {
                job.status = 'failed';
                job.error = error.message;
                job.completedAt = new Date();
                this.emit('job:failed', job);
            }
        } finally {
            this.processingJobs.delete(job.id);
            this.updateUI();
            // Process next job
            this.processNextJob();
        }
    }

    getAllJobs() {
        return Array.from(this.jobs.values()).sort((a, b) => 
            b.createdAt.getTime() - a.createdAt.getTime()
        );
    }

    getStats() {
        const jobs = Array.from(this.jobs.values());
        return {
            total: jobs.length,
            pending: jobs.filter(j => j.status === 'pending').length,
            inProgress: jobs.filter(j => j.status === 'in_progress').length,
            completed: jobs.filter(j => j.status === 'completed').length,
            cancelled: jobs.filter(j => j.status === 'cancelled').length,
            failed: jobs.filter(j => j.status === 'failed').length
        };
    }

    clearHistory() {
        const jobs = Array.from(this.jobs.values());
        jobs.forEach(job => {
            if (['completed', 'failed', 'cancelled'].includes(job.status)) {
                this.jobs.delete(job.id);
            }
        });
        this.updateUI();
    }

    updateUI() {
        // Update statistics
        const stats = this.getStats();
        document.getElementById('stat-pending').textContent = stats.pending;
        document.getElementById('stat-progress').textContent = stats.inProgress;
        document.getElementById('stat-completed').textContent = stats.completed;
        document.getElementById('stat-cancelled').textContent = stats.cancelled;
        document.getElementById('stat-failed').textContent = stats.failed;

        // Update job list
        const jobList = document.getElementById('job-list');
        const jobs = this.getAllJobs();

        if (jobs.length === 0) {
            jobList.innerHTML = '<div class="empty-state">No jobs yet. Create some jobs to get started!</div>';
            return;
        }

        jobList.innerHTML = jobs.map(job => this.renderJob(job)).join('');
    }

    renderJob(job) {
        const canCancel = ['pending', 'in_progress'].includes(job.status);
        const showProgress = job.status === 'in_progress' || job.progress > 0;

        return `
            <div class="job-item">
                <div class="job-header">
                    <div class="job-info">
                        <span class="job-id">${job.id}</span>
                        <span class="job-type">${job.type.toUpperCase()}</span>
                    </div>
                    <span class="job-status status-${job.status}">${job.status.replace('_', ' ')}</span>
                </div>
                
                ${showProgress ? `
                    <div class="job-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${job.progress}%"></div>
                        </div>
                        <div class="progress-text">${job.progress}% complete</div>
                    </div>
                ` : ''}
                
                ${job.error ? `
                    <div style="color: #e74c3c; font-size: 12px; margin-top: 8px;">
                        Error: ${job.error}
                    </div>
                ` : ''}
                
                <div class="timestamp">
                    Created: ${job.createdAt.toLocaleTimeString()}
                    ${job.completedAt ? ` | Completed: ${job.completedAt.toLocaleTimeString()}` : ''}
                    ${job.cancelledAt ? ` | Cancelled: ${job.cancelledAt.toLocaleTimeString()}` : ''}
                </div>
                
                <div class="job-actions">
                    <button 
                        class="btn-danger btn-small" 
                        onclick="cancelJob('${job.id}')"
                        ${!canCancel ? 'disabled' : ''}
                    >
                        ${canCancel ? '✕ Cancel Job' : 'Cannot Cancel'}
                    </button>
                </div>
            </div>
        `;
    }
}

// Initialize job manager
const jobManager = new JobManagerClient();

// Event listeners
jobManager.on('job:created', (job) => {
    console.log('Job created:', job.id);
});

jobManager.on('job:cancelled', (job) => {
    console.log('Job cancelled:', job.id);
});

jobManager.on('job:completed', (job) => {
    console.log('Job completed:', job.id);
});

jobManager.on('job:cleanup', (job) => {
    console.log('Cleaning up job resources:', job.id);
});

// UI Functions
function createOCRJob() {
    jobManager.createJob('ocr', { 
        document: 'sample-document.pdf',
        language: 'en'
    });
}

function createMetadataJob() {
    jobManager.createJob('metadata', { 
        document: 'sample-image.jpg',
        extractFields: ['title', 'author', 'date']
    });
}

function createMultipleJobs() {
    for (let i = 0; i < 5; i++) {
        const type = Math.random() > 0.5 ? 'ocr' : 'metadata';
        jobManager.createJob(type, { 
            document: `document-${i + 1}.pdf`,
            batch: true
        });
    }
}

function cancelJob(jobId) {
    if (confirm('Are you sure you want to cancel this job?')) {
        jobManager.cancelJob(jobId);
    }
}

function refreshJobs() {
    jobManager.updateUI();
}

function clearHistory() {
    if (confirm('Clear all completed, failed, and cancelled jobs?')) {
        jobManager.clearHistory();
    }
}

// Initialize UI
jobManager.updateUI();
