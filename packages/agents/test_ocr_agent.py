"""
Tests for OCR Agent

Tests include:
- Single image OCR extraction
- Folder batch processing
- Job status tracking
- Provider selection
"""

import asyncio
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import the modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from job_models import Job, JobResult
from job_registry import JobRegistry


class TestJobModels:
    """Tests for job models"""
    
    def test_job_result_creation(self):
        """Test creating a JobResult"""
        result = JobResult(
            file_name="test.png",
            text="Sample text",
            provider="tesseract",
            confidence=0.95
        )
        
        assert result.file_name == "test.png"
        assert result.text == "Sample text"
        assert result.provider == "tesseract"
        assert result.confidence == 0.95
        assert result.timestamp is not None
    
    def test_job_result_to_dict(self):
        """Test converting JobResult to dict"""
        result = JobResult(
            file_name="test.png",
            text="Sample text",
            provider="tesseract",
            confidence=0.95
        )
        
        result_dict = result.to_dict()
        assert result_dict["file_name"] == "test.png"
        assert result_dict["text"] == "Sample text"
        assert result_dict["provider"] == "tesseract"
        assert result_dict["confidence"] == 0.95
    
    def test_job_creation(self):
        """Test creating a Job"""
        job = Job(job_id="job-123", job_type="ocr_folder")
        
        assert job.job_id == "job-123"
        assert job.job_type == "ocr_folder"
        assert job.status == "pending"
        assert job.files_processed == 0
        assert len(job.results) == 0
    
    def test_job_to_dict(self):
        """Test converting Job to dict"""
        job = Job(job_id="job-123", job_type="ocr_folder")
        job.files_total = 5
        job.files_processed = 2
        
        job_dict = job.to_dict()
        assert job_dict["job_id"] == "job-123"
        assert job_dict["status"] == "pending"
        assert job_dict["files_total"] == 5
        assert job_dict["files_processed"] == 2
    
    def test_job_from_dict(self):
        """Test reconstructing Job from dict"""
        original_dict = {
            "job_id": "job-123",
            "job_type": "ocr_folder",
            "status": "processing",
            "files_total": 5,
            "files_processed": 2,
            "results": [{
                "file_name": "test.png",
                "text": "Sample text",
                "provider": "tesseract",
                "confidence": 0.95,
                "error": "",
                "timestamp": "2024-01-01T00:00:00"
            }],
            "errors": [],
            "params": {},
            "created_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
            "current_file": None,
            "agent_id": "ocr-agent"
        }
        
        job = Job.from_dict(original_dict)
        assert job.job_id == "job-123"
        assert job.status == "processing"
        assert len(job.results) == 1
        assert job.results[0].file_name == "test.png"


@pytest.mark.asyncio
class TestJobRegistry:
    """Tests for JobRegistry"""
    
    async def test_create_job(self):
        """Test creating a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            
            assert job_id is not None
            assert len(job_id) > 0
    
    async def test_get_job(self):
        """Test retrieving a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            job = await registry.get_job(job_id)
            
            assert job is not None
            assert job.job_id == job_id
            assert job.status == "pending"
    
    async def test_update_job_status(self):
        """Test updating job status"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            await registry.update_job_status(job_id, "processing", files_total=5)
            
            job = await registry.get_job(job_id)
            assert job.status == "processing"
            assert job.files_total == 5
    
    async def test_append_result(self):
        """Test appending results to a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            
            await registry.append_result(
                job_id,
                file_name="test.png",
                text="Sample text",
                provider="tesseract",
                confidence=0.95
            )
            
            job = await registry.get_job(job_id)
            assert len(job.results) == 1
            assert job.results[0].file_name == "test.png"
            assert job.files_processed == 1
    
    async def test_append_error(self):
        """Test appending errors to a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            
            await registry.append_error(
                job_id,
                file_name="test.png",
                error="Failed to process"
            )
            
            job = await registry.get_job(job_id)
            assert len(job.errors) == 1
            assert job.errors[0]["error"] == "Failed to process"
    
    async def test_persistence(self):
        """Test that jobs are persisted to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate job
            registry1 = JobRegistry(persist_dir=tmpdir)
            job_id = await registry1.create_job(job_type="ocr_folder")
            await registry1.append_result(job_id, "test.png", "Sample text", "tesseract", 0.95)
            
            # Create new registry and verify persistence
            registry2 = JobRegistry(persist_dir=tmpdir)
            job = await registry2.get_job(job_id)
            
            assert job is not None
            assert len(job.results) == 1
    
    async def test_cleanup_job(self):
        """Test cleaning up a job"""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = JobRegistry(persist_dir=tmpdir)
            
            job_id = await registry.create_job(job_type="ocr_folder")
            
            # Verify job exists
            job = await registry.get_job(job_id)
            assert job is not None
            
            # Clean up
            await registry.cleanup_job(job_id)
            
            # Verify job is gone
            job = await registry.get_job(job_id)
            assert job is None


class TestImageOptimizer:
    """Tests for image optimization"""
    
    def test_optimize_image_no_resize_needed(self):
        """Test image optimization when no resize needed"""
        from providers.services.image_optimizer import ImageOptimizer
        from PIL import Image
        
        # Create small image
        img = Image.new('RGB', (100, 100), color='red')
        
        optimized = ImageOptimizer.optimize_image(img, auto_optimize=True)
        
        # Should not resize since it's small
        assert optimized.width == img.width
        assert optimized.height == img.height


class TestPDFService:
    """Tests for PDF service"""
    
    def test_is_pdf(self):
        """Test PDF detection"""
        from providers.services.pdf_service import PDFService
        
        assert PDFService.is_pdf("document.pdf") == True
        assert PDFService.is_pdf("image.png") == False
        assert PDFService.is_pdf("file.PDF") == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
