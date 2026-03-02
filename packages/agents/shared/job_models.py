"""
Job tracking models for OCR processing.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class JobResult:
    """Single file OCR result"""
    
    def __init__(self, file_name: str, text: str = "", provider: str = "", confidence: float = 0.0, error: str = ""):
        self.file_name = file_name
        self.text = text
        self.provider = provider
        self.confidence = confidence
        self.error = error
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "text": self.text,
            "provider": self.provider,
            "confidence": self.confidence,
            "error": self.error,
            "timestamp": self.timestamp
        }


class Job:
    """OCR job state"""
    
    def __init__(self, job_id: str, job_type: str = "ocr", params: Dict[str, Any] = None):
        self.job_id = job_id
        self.job_type = job_type
        self.status = "pending"  # pending, processing, completed, failed
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        
        # Progress tracking
        self.files_total = 0
        self.files_processed = 0
        self.current_file = None
        
        # Results
        self.results: List[JobResult] = []
        self.errors: List[Dict[str, str]] = []
        
        # Metadata
        self.params = params or {}
        self.agent_id = "ocr-agent"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "files_total": self.files_total,
            "files_processed": self.files_processed,
            "current_file": self.current_file,
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
            "params": self.params,
            "agent_id": self.agent_id
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Job':
        """Reconstruct Job from dict (for persistence)"""
        job = Job(data['job_id'], data.get('job_type', 'ocr'), data.get('params', {}))
        job.status = data.get('status', 'pending')
        job.created_at = data.get('created_at')
        job.started_at = data.get('started_at')
        job.completed_at = data.get('completed_at')
        job.files_total = data.get('files_total', 0)
        job.files_processed = data.get('files_processed', 0)
        job.current_file = data.get('current_file')
        job.errors = data.get('errors', [])
        job.agent_id = data.get('agent_id', 'ocr-agent')
        
        # Reconstruct results
        for result_dict in data.get('results', []):
            result = JobResult(
                result_dict['file_name'],
                result_dict.get('text', ''),
                result_dict.get('provider', ''),
                result_dict.get('confidence', 0.0),
                result_dict.get('error', '')
            )
            result.timestamp = result_dict.get('timestamp')
            job.results.append(result)
        
        return job
