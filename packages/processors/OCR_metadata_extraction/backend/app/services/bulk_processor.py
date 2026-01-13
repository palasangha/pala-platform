"""
Bulk image processing service for scanning folders and processing multiple images
with progress tracking and report generation.
"""

import os
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event
import time

from .ocr_service import OCRService
from .pdf_service import PDFService

logger = logging.getLogger(__name__)


class BulkProcessor:
    """Handle bulk processing of images from folders with progress tracking"""
    
    # Supported image extensions
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp',
        '.pdf'  # Also support PDFs
    }
    
    def __init__(self, ocr_service: OCRService, progress_callback: Optional[Callable] = None, max_workers: int = 4, job_id: str = None):
        """
        Initialize bulk processor

        Args:
            ocr_service: OCRService instance for processing images
            progress_callback: Optional callback function(current, total, filename) for progress tracking
            max_workers: Maximum number of parallel workers (default: 4)
            job_id: Unique job identifier for pause/resume functionality
        """
        self.ocr_service = ocr_service
        self.progress_callback = progress_callback
        self.max_workers = max_workers
        self.job_id = job_id
        self.results = []
        self.errors = []
        self._lock = Lock()  # Thread-safe access to results and errors
        self._processed_count = 0  # Track processed files for progress

        # Pause/Resume control
        self._pause_event = Event()
        self._pause_event.set()  # Start in running state
        self._stop_event = Event()  # For cancellation
        self._is_paused = False
        self._pause_requested = False

        # Error handling
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5  # Auto-pause after 5 consecutive errors
        self._retry_count = {}  # Track retries per file
        self._max_retries = 3

    def pause(self):
        """Pause the processing"""
        logger.info(f"Pause requested for job {self.job_id}")
        self._pause_requested = True
        self._pause_event.clear()
        with self._lock:
            self._is_paused = True

    def resume(self):
        """Resume the processing"""
        logger.info(f"Resume requested for job {self.job_id}")
        self._pause_requested = False
        self._pause_event.set()
        with self._lock:
            self._is_paused = False
            self._consecutive_errors = 0  # Reset error count on manual resume

    def stop(self):
        """Stop the processing (cancellation)"""
        logger.info(f"Stop requested for job {self.job_id}")
        self._stop_event.set()
        self._pause_event.set()  # Unblock any waiting threads

    def is_paused(self):
        """Check if processing is paused"""
        return self._is_paused

    def is_stopped(self):
        """Check if processing is stopped"""
        return self._stop_event.is_set()

    def get_state(self):
        """Get current processing state"""
        if self.is_stopped():
            return 'stopped'
        elif self.is_paused():
            return 'paused'
        else:
            return 'running'

    def _wait_if_paused(self):
        """Wait if processing is paused"""
        if self._pause_requested:
            logger.info(f"Job {self.job_id} paused, waiting for resume...")
            self._pause_event.wait()  # Block until resume() is called
            logger.info(f"Job {self.job_id} resumed")

    def scan_folder(self, folder_path: str, recursive: bool = True) -> List[str]:
        """
        Scan folder for image files
        
        Args:
            folder_path: Root folder to scan
            recursive: Whether to scan subfolders (default: True)
            
        Returns:
            List of image file paths found
        """
        if not os.path.isdir(folder_path):
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        image_files = []
        folder_path = Path(folder_path)
        
        # Use glob pattern for recursion
        pattern = "**/*" if recursive else "*"
        
        for file_path in folder_path.glob(pattern):
            if file_path.is_file():
                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    image_files.append(str(file_path))
        
        # Sort for consistent ordering
        return sorted(image_files)
    
    def _process_single_file(
        self,
        image_path: str,
        provider: str,
        languages: List[str],
        handwriting: bool,
        idx: int,
        total: int
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Process a single image file with retry logic and error handling

        Args:
            image_path: Path to image file
            provider: OCR provider
            languages: List of languages
            handwriting: Whether to detect handwriting
            idx: Index of file (for progress)
            total: Total files (for progress)

        Returns:
            Tuple of (result_dict, error_dict) - one will be None
        """
        filename = os.path.basename(image_path)
        current = idx + 1

        # Check if stopped
        if self.is_stopped():
            return None, {
                'file': filename,
                'file_path': image_path,
                'status': 'cancelled',
                'error': 'Processing was cancelled',
                'processed_at': datetime.now().isoformat()
            }

        # Wait if paused
        self._wait_if_paused()

        # Retry logic
        retry_count = self._retry_count.get(image_path, 0)
        max_attempts = self._max_retries + 1

        for attempt in range(retry_count, max_attempts):
            try:
                logger.info(f"Processing {current}/{total}: {filename} (attempt {attempt + 1}/{max_attempts})")

                # Process image
                ocr_result = self.ocr_service.process_image(
                    image_path=image_path,
                    provider=provider,
                    languages=languages,
                    handwriting=handwriting
                )

                # Reset consecutive errors on success
                with self._lock:
                    self._consecutive_errors = 0
                    if image_path in self._retry_count:
                        del self._retry_count[image_path/Bhushanji]

                # Prepare result with metadata
                result = {
                    'file': filename,
                    'file_path': image_path,
                    'status': 'success',
                    'processed_at': datetime.now().isoformat(),
                    'provider': provider,
                    'languages': languages,
                    'handwriting': handwriting,
                    'text': ocr_result.get('text', ''),
                    'confidence': ocr_result.get('confidence', 0),
                    'detected_language': ocr_result.get('detected_language', ''),
                    'file_info': ocr_result.get('file_info', {}),
                    'metadata': ocr_result.get('metadata', {}),
                    'blocks_count': len(ocr_result.get('blocks', [])),
                    'words_count': len(ocr_result.get('words', [])),
                    'retry_count': attempt
                }

                # Add page count for PDFs
                if ocr_result.get('pages_processed'):
                    result['pages_processed'] = ocr_result.get('pages_processed')

                return result, None

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing {filename} (attempt {attempt + 1}/{max_attempts}): {error_msg}")

                # Check for network/connection errors
                is_network_error = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'unreachable', 'refused', 'reset'
                ])

                # Increment consecutive errors
                with self._lock:
                    self._consecutive_errors += 1
                    self._retry_count[image_path] = attempt + 1

                # Auto-pause on too many consecutive errors
                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.warning(f"Too many consecutive errors ({self._consecutive_errors}), auto-pausing job {self.job_id}")
                    self.pause()
                    # Wait for manual resume
                    self._wait_if_paused()

                # If network error or not last attempt, wait and retry
                if (is_network_error or attempt < max_attempts - 1):
                    retry_delay = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                    logger.info(f"Retrying {filename} in {retry_delay}s...")
                    time.sleep(retry_delay)

                    # Check again if stopped during sleep
                    if self.is_stopped():
                        break

                    continue

                # Last attempt failed
                break

        # All attempts failed
        return None, {
            'file': filename,
            'file_path': image_path,
            'status': 'error',
            'error': error_msg,
            'retry_count': attempt + 1,
            'processed_at': datetime.now().isoformat()
        }

    def process_folder(
        self,
        folder_path: str,
        provider: str = 'tesseract',
        languages: List[str] = None,
        handwriting: bool = False,
        recursive: bool = True,
        parallel: bool = True
    ) -> Dict:
        """
        Process all images in a folder

        Args:
            folder_path: Root folder to process
            provider: OCR provider to use (default: tesseract)
            languages: List of languages (default: ['en'])
            handwriting: Whether to detect handwriting
            recursive: Whether to process subfolders
            parallel: Whether to use parallel processing (default: True)

        Returns:
            Dictionary with results, errors, and statistics
        """
        if not languages:
            languages = ['en']

        # Scan folder for images
        image_files = self.scan_folder(folder_path, recursive=recursive)

        if not image_files:
            raise ValueError(f"No supported image files found in {folder_path}")

        logger.info(f"Found {len(image_files)} image files to process")
        logger.info(f"Using {'parallel' if parallel else 'sequential'} processing with {self.max_workers if parallel else 1} workers")

        # Initialize results
        self.results = []
        self.errors = []
        self._processed_count = 0

        if parallel and self.max_workers > 1:
            # Parallel processing with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self._process_single_file,
                        image_path,
                        provider,
                        languages,
                        handwriting,
                        idx,
                        len(image_files)
                    ): (idx, image_path)
                    for idx, image_path in enumerate(image_files)
                }

                # Process completed tasks
                for future in as_completed(future_to_file):
                    idx, image_path = future_to_file[future]
                    filename = os.path.basename(image_path)

                    # Update progress with thread safety
                    with self._lock:
                        self._processed_count += 1
                        current = self._processed_count

                    # Call progress callback
                    if self.progress_callback:
                        self.progress_callback(current, len(image_files), filename)

                    try:
                        result, error = future.result()

                        # Thread-safe append to results/errors
                        with self._lock:
                            if result:
                                self.results.append(result)
                            if error:
                                self.errors.append(error)

                    except Exception as e:
                        logger.error(f"Unexpected error processing {filename}: {str(e)}")
                        with self._lock:
                            self.errors.append({
                                'file': filename,
                                'file_path': image_path,
                                'status': 'error',
                                'error': str(e),
                                'processed_at': datetime.now().isoformat()
                            })
        else:
            # Sequential processing (original behavior)
            for idx, image_path in enumerate(image_files):
                current = idx + 1
                total = len(image_files)
                filename = os.path.basename(image_path)

                # Call progress callback
                if self.progress_callback:
                    self.progress_callback(current, total, filename)

                result, error = self._process_single_file(
                    image_path, provider, languages, handwriting, idx, total
                )

                if result:
                    self.results.append(result)
                if error:
                    self.errors.append(error)

        # Generate summary statistics
        stats = self._generate_statistics()

        return {
            'summary': {
                'total_files': len(image_files),
                'successful': len(self.results),
                'failed': len(self.errors),
                'folder_path': folder_path,
                'processed_at': datetime.now().isoformat(),
                'parallel_processing': parallel,
                'max_workers': self.max_workers if parallel else 1,
                'state': self.get_state(),
                'paused': self.is_paused(),
                'stopped': self.is_stopped(),
                'consecutive_errors': self._consecutive_errors,
                'statistics': stats
            },
            'results': self.results,
            'errors': self.errors
        }

    def get_checkpoint_data(self) -> Dict:
        """Get checkpoint data for resuming"""
        with self._lock:
            return {
                'job_id': self.job_id,
                'processed_count': self._processed_count,
                'results_count': len(self.results),
                'errors_count': len(self.errors),
                'state': self.get_state(),
                'consecutive_errors': self._consecutive_errors,
                'retry_count': dict(self._retry_count),
                'results': self.results.copy(),
                'errors': self.errors.copy()
            }

    def restore_from_checkpoint(self, checkpoint_data: Dict):
        """Restore processor state from checkpoint"""
        with self._lock:
            self._processed_count = checkpoint_data.get('processed_count', 0)
            self.results = checkpoint_data.get('results', [])
            self.errors = checkpoint_data.get('errors', [])
            self._retry_count = checkpoint_data.get('retry_count', {})
            self._consecutive_errors = checkpoint_data.get('consecutive_errors', 0)
        logger.info(f"Restored job {self.job_id} from checkpoint: {len(self.results)} results, {len(self.errors)} errors")
    
    def _generate_statistics(self) -> Dict:
        """Generate statistics from processed results"""
        if not self.results:
            return {
                'total_characters': 0,
                'average_confidence': 0,
                'average_words': 0,
                'average_blocks': 0,
                'languages': []
            }
        
        total_chars = sum(len(r.get('text', '')) for r in self.results)
        avg_confidence = sum(r.get('confidence', 0) for r in self.results) / len(self.results)
        avg_words = sum(r.get('words_count', 0) for r in self.results) / len(self.results)
        avg_blocks = sum(r.get('blocks_count', 0) for r in self.results) / len(self.results)
        
        # Collect unique languages
        languages = set()
        for result in self.results:
            lang = result.get('detected_language', '')
            if lang:
                languages.add(lang)
        
        return {
            'total_characters': total_chars,
            'average_confidence': round(avg_confidence, 2),
            'average_words': round(avg_words, 2),
            'average_blocks': round(avg_blocks, 2),
            'languages': sorted(list(languages))
        }
    
    def export_to_json(self, output_path: str) -> str:
        """
        Export results to JSON file
        
        Args:
            output_path: Path where to save the JSON file
            
        Returns:
            Path to created JSON file
        """
        if not self.results and not self.errors:
            raise ValueError("No results to export. Run process_folder first.")
        
        output_file = output_path if output_path.endswith('.json') else f"{output_path}.json"
        
        export_data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_files': len(self.results) + len(self.errors),
                'successful': len(self.results),
                'failed': len(self.errors),
            },
            'summary': self._generate_statistics(),
            'results': self.results,
            'errors': self.errors
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON report exported to: {output_file}")
        return output_file
    
    def export_to_csv(self, output_path: str) -> str:
        """
        Export results to CSV file with all data from each processed file

        Args:
            output_path: Path where to save the CSV file

        Returns:
            Path to created CSV file
        """
        if not self.results and not self.errors:
            raise ValueError("No results to export. Run process_folder first.")

        output_file = output_path if output_path.endswith('.csv') else f"{output_path}.csv"

        # Combine successful and error results with ALL available data
        all_results = []
        for result in self.results:
            # Get file info
            file_info = result.get('file_info', {})
            metadata = result.get('metadata', {})

            row = {
                'File': result.get('file', ''),
                'File Path': result.get('file_path', ''),
                'Status': 'Success',
                'Provider': result.get('provider', ''),
                'Languages': ','.join(result.get('languages', [])),
                'Confidence': result.get('confidence', 0),
                'Detected Language': result.get('detected_language', ''),
                'Handwriting': result.get('handwriting', False),
                'Text Length': len(result.get('text', '')),
                'Character Count': len(result.get('text', '')),
                'Blocks Count': result.get('blocks_count', 0),
                'Words Count': result.get('words_count', 0),
                'Pages Processed': result.get('pages_processed', 1),
                'Processed At': result.get('processed_at', ''),
                # File info
                'File Size': file_info.get('size', ''),
                'File Type': file_info.get('type', ''),
                'File Extension': file_info.get('extension', ''),
                'Is PDF': file_info.get('is_pdf', False),
                'Image Width': file_info.get('width', ''),
                'Image Height': file_info.get('height', ''),
                # Metadata
                'Processing Time': metadata.get('processing_time', ''),
                'OCR Text': result.get('text', ''),  # Full OCR text in CSV
                'Error': ''
            }
            all_results.append(row)

        for error in self.errors:
            row = {
                'File': error.get('file', ''),
                'File Path': error.get('file_path', ''),
                'Status': 'Error',
                'Provider': '',
                'Languages': '',
                'Confidence': '',
                'Detected Language': '',
                'Handwriting': '',
                'Text Length': '',
                'Character Count': '',
                'Blocks Count': '',
                'Words Count': '',
                'Pages Processed': '',
                'Processed At': error.get('processed_at', ''),
                'File Size': '',
                'File Type': '',
                'File Extension': '',
                'Is PDF': '',
                'Image Width': '',
                'Image Height': '',
                'Processing Time': '',
                'OCR Text': '',
                'Error': error.get('error', '')
            }
            all_results.append(row)

        if not all_results:
            raise ValueError("No results to export")

        # Write CSV with all columns
        fieldnames = list(all_results[0].keys())

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        
        logger.info(f"CSV report exported to: {output_file}")
        return output_file
    
    def export_to_text(self, output_path: str) -> str:
        """
        Export results to plain text file
        
        Args:
            output_path: Path where to save the text file
            
        Returns:
            Path to created text file
        """
        if not self.results and not self.errors:
            raise ValueError("No results to export. Run process_folder first.")
        
        output_file = output_path if output_path.endswith('.txt') else f"{output_path}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("BULK OCR PROCESSING REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Write summary
            stats = self._generate_statistics()
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Files Processed: {len(self.results) + len(self.errors)}\n")
            f.write(f"Successful: {len(self.results)}\n")
            f.write(f"Failed: {len(self.errors)}\n")
            f.write(f"Generated At: {datetime.now().isoformat()}\n\n")
            
            # Write statistics
            f.write("STATISTICS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Characters Extracted: {stats['total_characters']}\n")
            f.write(f"Average Confidence: {stats['average_confidence']:.2%}\n")
            f.write(f"Average Words per File: {stats['average_words']:.2f}\n")
            f.write(f"Average Blocks per File: {stats['average_blocks']:.2f}\n")
            f.write(f"Languages Detected: {', '.join(stats['languages']) or 'None'}\n\n")
            
            # Write successful results
            if self.results:
                f.write("=" * 80 + "\n")
                f.write("SUCCESSFULLY PROCESSED FILES\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, result in enumerate(self.results, 1):
                    f.write(f"[{idx}] {result.get('file', 'Unknown')}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Status: {result.get('status', '')}\n")
                    f.write(f"Provider: {result.get('provider', '')}\n")
                    f.write(f"Confidence: {result.get('confidence', 0):.2%}\n")
                    f.write(f"Detected Language: {result.get('detected_language', '')}\n")
                    f.write(f"Text Length: {len(result.get('text', ''))} characters\n")
                    f.write(f"Blocks: {result.get('blocks_count', 0)}\n")
                    f.write(f"Words: {result.get('words_count', 0)}\n")
                    if result.get('pages_processed'):
                        f.write(f"Pages: {result.get('pages_processed')}\n")
                    f.write(f"Processed At: {result.get('processed_at', '')}\n\n")
                    
                    # Write extracted text
                    f.write("EXTRACTED TEXT:\n")
                    f.write(result.get('text', '[No text extracted]'))
                    f.write("\n\n")
            
            # Write errors
            if self.errors:
                f.write("=" * 80 + "\n")
                f.write("FAILED FILES\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, error in enumerate(self.errors, 1):
                    f.write(f"[{idx}] {error.get('file', 'Unknown')}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Status: Error\n")
                    f.write(f"Error: {error.get('error', 'Unknown error')}\n")
                    f.write(f"Processed At: {error.get('processed_at', '')}\n\n")
        
        logger.info(f"Text report exported to: {output_file}")
        return output_file
    
    def export_all_reports(self, output_folder: str, base_name: str = "ocr_report") -> Dict[str, str]:
        """
        Export results to all formats (JSON, CSV, TXT)
        
        Args:
            output_folder: Folder where to save all report files
            base_name: Base name for the report files (without extension)
            
        Returns:
            Dictionary with paths to all created files
        """
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder, exist_ok=True)
        
        base_path = os.path.join(output_folder, base_name)
        
        return {
            'json': self.export_to_json(base_path),
            'csv': self.export_to_csv(base_path),
            'text': self.export_to_text(base_path)
        }
