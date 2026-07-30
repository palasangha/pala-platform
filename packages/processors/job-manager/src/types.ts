/**
 * Job status enumeration
 */
export enum JobStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
  FAILED = 'failed'
}

/**
 * Job interface
 */
export interface Job {
  id: string;
  type: string;
  status: JobStatus;
  progress: number;
  data: any;
  result?: any;
  error?: string;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  cancelledAt?: Date;
}

/**
 * Job processor function type
 */
export type JobProcessor = (job: Job, updateProgress: (progress: number) => void) => Promise<any>;
