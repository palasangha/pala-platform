"""
Job registry for tracking OCR processing jobs.
Thread-safe in-memory storage with optional JSON persistence.
"""

import logging
import json
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from job_models import Job, JobResult

logger = logging.getLogger(__name__)


class JobRegistry:
    """Thread-safe job registry for tracking OCR jobs"""
    
    def __init__(self, persist_dir: Optional[str] = None):
        """
        Initialize job registry
        
        Args:
            persist_dir: Directory for persisting job state (optional)
        """
        self.jobs: Dict[str, Job] = {}
        self.lock = asyncio.Lock()
        self.persist_dir = Path(persist_dir) if persist_dir else None
        
        if self.persist_dir:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_persisted_jobs()
            logger.info(f"Job registry initialized with persistence: {self.persist_dir}")
        else:
            logger.info("Job registry initialized (in-memory only)")
    
    def _load_persisted_jobs(self):
        """Load previously saved jobs from disk"""
        if not self.persist_dir:
            return
        
        try:
            for job_file in self.persist_dir.glob("job-*.json"):
                try:
                    with open(job_file, 'r') as f:
                        data = json.load(f)
                        job = Job.from_dict(data)
                        self.jobs[job.job_id] = job
                        logger.debug(f"Loaded persisted job: {job.job_id}")
                except Exception as e:
                    logger.warning(f"Failed to load job file {job_file}: {e}")
        except Exception as e:
            logger.warning(f"Error loading persisted jobs: {e}")
    
    async def create_job(self, job_type: str = "ocr", params: Dict = None) -> str:
        """
        Create a new job
        
        Args:
            job_type: Type of job (e.g., "ocr")
            params: Job parameters
        
        Returns:
            Job ID
        """
        async with self.lock:
            job_id = str(uuid.uuid4())[:8]
            job = Job(job_id, job_type, params or {})
            self.jobs[job_id] = job
            
            logger.info(f"Created job: {job_id}")
            self._persist_job(job)
            
            return job_id
    
    async def update_job_status(self, job_id: str, status: str, **updates) -> bool:
        """
        Update job status and fields
        
        Args:
            job_id: Job ID
            status: New status (pending, processing, completed, failed)
            **updates: Additional fields to update
        
        Returns:
            True if successful, False if job not found
        """
        async with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job not found: {job_id}")
                return False
            
            job = self.jobs[job_id]
            job.status = status
            
            # Update timestamp based on status
            if status == "processing" and not job.started_at:
                job.started_at = datetime.now().isoformat()
            elif status in ("completed", "failed") and not job.completed_at:
                job.completed_at = datetime.now().isoformat()
            
            # Apply any other updates
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            logger.debug(f"Updated job {job_id} status to {status}")
            self._persist_job(job)
            
            return True
    
    async def append_result(self, job_id: str, file_name: str, text: str, provider: str, confidence: float = 0.0) -> bool:
        """
        Add a successful result to a job
        
        Args:
            job_id: Job ID
            file_name: Name of processed file
            text: Extracted text
            provider: Provider used
            confidence: Confidence score (0-1)
        
        Returns:
            True if successful
        """
        async with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            result = JobResult(file_name, text, provider, confidence)
            job.results.append(result)
            job.files_processed += 1
            
            self._persist_job(job)
            return True
    
    async def append_error(self, job_id: str, file_name: str, error: str) -> bool:
        """
        Add an error to a job
        
        Args:
            job_id: Job ID
            file_name: Name of file that failed
            error: Error message
        
        Returns:
            True if successful
        """
        async with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            job.errors.append({"file": file_name, "error": error})
            job.files_processed += 1
            
            self._persist_job(job)
            return True
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID
        
        Args:
            job_id: Job ID
        
        Returns:
            Job object or None if not found
        """
        async with self.lock:
            return self.jobs.get(job_id)
    
    async def get_job_dict(self, job_id: str) -> Optional[Dict]:
        """
        Get job as dictionary (for JSON responses)
        
        Args:
            job_id: Job ID
        
        Returns:
            Job dictionary or None
        """
        job = await self.get_job(job_id)
        return job.to_dict() if job else None
    
    async def mark_failed(self, job_id: str, error: str) -> bool:
        """
        Mark job as failed
        
        Args:
            job_id: Job ID
            error: Error message
        
        Returns:
            True if successful
        """
        return await self.update_job_status(job_id, "failed")
    
    async def cleanup_job(self, job_id: str) -> bool:
        """
        Remove job from registry and persistence
        
        Args:
            job_id: Job ID
        
        Returns:
            True if successful
        """
        async with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                
                # Remove from persistence
                if self.persist_dir:
                    job_file = self.persist_dir / f"job-{job_id}.json"
                    if job_file.exists():
                        job_file.unlink()
                
                logger.info(f"Cleaned up job: {job_id}")
                return True
            
            return False
    
    def _persist_job(self, job: Job):
        """Save job to disk"""
        if not self.persist_dir:
            return
        
        try:
            job_file = self.persist_dir / f"job-{job.job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(job.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist job {job.job_id}: {e}")
