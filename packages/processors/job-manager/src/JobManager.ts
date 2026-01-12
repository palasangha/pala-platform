import EventEmitter from 'eventemitter3';
import { Job, JobStatus, JobProcessor } from './types';

/**
 * JobManager - Handles job lifecycle, queuing, and cancellation
 */
export class JobManager extends EventEmitter {
  private jobs: Map<string, Job> = new Map();
  private processors: Map<string, JobProcessor> = new Map();
  private processingJobs: Set<string> = new Set();
  private cancelRequests: Set<string> = new Set();
  private maxConcurrentJobs: number = 5;

  constructor(maxConcurrentJobs: number = 5) {
    super();
    this.maxConcurrentJobs = maxConcurrentJobs;
  }

  /**
   * Register a job processor for a specific job type
   */
  registerProcessor(jobType: string, processor: JobProcessor): void {
    this.processors.set(jobType, processor);
  }

  /**
   * Create a new job
   */
  createJob(type: string, data: any): Job {
    const job: Job = {
      id: this.generateJobId(),
      type,
      status: JobStatus.PENDING,
      progress: 0,
      data,
      createdAt: new Date()
    };

    this.jobs.set(job.id, job);
    this.emit('job:created', job);
    
    // Try to process immediately if capacity available
    this.processNextJob();
    
    return job;
  }

  /**
   * Get job by ID
   */
  getJob(jobId: string): Job | undefined {
    return this.jobs.get(jobId);
  }

  /**
   * Get all jobs
   */
  getAllJobs(): Job[] {
    return Array.from(this.jobs.values());
  }

  /**
   * Cancel a job
   */
  async cancelJob(jobId: string): Promise<boolean> {
    const job = this.jobs.get(jobId);
    
    if (!job) {
      throw new Error(`Job ${jobId} not found`);
    }

    // Job already completed, failed, or cancelled
    if ([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED].includes(job.status)) {
      return false;
    }

    // If job is pending, cancel immediately
    if (job.status === JobStatus.PENDING) {
      job.status = JobStatus.CANCELLED;
      job.cancelledAt = new Date();
      this.emit('job:cancelled', job);
      this.cleanupJob(job);
      return true;
    }

    // If job is in progress, mark for cancellation
    if (job.status === JobStatus.IN_PROGRESS) {
      this.cancelRequests.add(jobId);
      this.emit('job:cancelling', job);
      return true;
    }

    return false;
  }

  /**
   * Process next job in queue
   */
  private async processNextJob(): Promise<void> {
    // Check if we have capacity
    if (this.processingJobs.size >= this.maxConcurrentJobs) {
      return;
    }

    // Find next pending job
    const pendingJob = Array.from(this.jobs.values()).find(
      job => job.status === JobStatus.PENDING
    );

    if (!pendingJob) {
      return;
    }

    await this.processJob(pendingJob);
  }

  /**
   * Process a specific job
   */
  private async processJob(job: Job): Promise<void> {
    const processor = this.processors.get(job.type);
    
    if (!processor) {
      job.status = JobStatus.FAILED;
      job.error = `No processor registered for job type: ${job.type}`;
      job.completedAt = new Date();
      this.emit('job:failed', job);
      return;
    }

    // Mark job as in progress
    job.status = JobStatus.IN_PROGRESS;
    job.startedAt = new Date();
    this.processingJobs.add(job.id);
    this.emit('job:started', job);

    try {
      // Create progress updater with cancellation check
      const updateProgress = (progress: number) => {
        if (this.cancelRequests.has(job.id)) {
          throw new Error('Job cancelled');
        }
        job.progress = Math.min(100, Math.max(0, progress));
        this.emit('job:progress', job);
      };

      // Execute the processor
      const result = await processor(job, updateProgress);

      // Check if cancelled during processing
      if (this.cancelRequests.has(job.id)) {
        job.status = JobStatus.CANCELLED;
        job.cancelledAt = new Date();
        this.cancelRequests.delete(job.id);
        this.emit('job:cancelled', job);
        this.cleanupJob(job);
      } else {
        job.status = JobStatus.COMPLETED;
        job.result = result;
        job.progress = 100;
        job.completedAt = new Date();
        this.emit('job:completed', job);
      }
    } catch (error) {
      // Check if error is due to cancellation
      if (this.cancelRequests.has(job.id)) {
        job.status = JobStatus.CANCELLED;
        job.cancelledAt = new Date();
        this.cancelRequests.delete(job.id);
        this.emit('job:cancelled', job);
        this.cleanupJob(job);
      } else {
        job.status = JobStatus.FAILED;
        job.error = error instanceof Error ? error.message : String(error);
        job.completedAt = new Date();
        this.emit('job:failed', job);
      }
    } finally {
      this.processingJobs.delete(job.id);
      // Process next job
      this.processNextJob();
    }
  }

  /**
   * Clean up intermediate results from a job
   */
  private cleanupJob(job: Job): void {
    // Clear intermediate results
    if (job.result) {
      delete job.result;
    }
    // Emit cleanup event for external cleanup handlers
    this.emit('job:cleanup', job);
  }

  /**
   * Clear old jobs from history (completed, failed, cancelled)
   */
  clearHistory(olderThanMs: number = 24 * 60 * 60 * 1000): number {
    const now = Date.now();
    let cleared = 0;

    for (const [id, job] of this.jobs.entries()) {
      if ([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED].includes(job.status)) {
        const completionTime = (job.completedAt || job.cancelledAt)?.getTime() || now;
        if (now - completionTime > olderThanMs) {
          this.jobs.delete(id);
          cleared++;
        }
      }
    }

    return cleared;
  }

  /**
   * Generate unique job ID
   */
  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get queue statistics
   */
  getStats(): {
    total: number;
    pending: number;
    inProgress: number;
    completed: number;
    cancelled: number;
    failed: number;
  } {
    const jobs = Array.from(this.jobs.values());
    return {
      total: jobs.length,
      pending: jobs.filter(j => j.status === JobStatus.PENDING).length,
      inProgress: jobs.filter(j => j.status === JobStatus.IN_PROGRESS).length,
      completed: jobs.filter(j => j.status === JobStatus.COMPLETED).length,
      cancelled: jobs.filter(j => j.status === JobStatus.CANCELLED).length,
      failed: jobs.filter(j => j.status === JobStatus.FAILED).length
    };
  }
}

export default JobManager;
