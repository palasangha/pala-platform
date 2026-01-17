"""Service to monitor job completion and trigger final aggregation"""
import time
import logging
import os
import json
import csv
import zipfile
from datetime import datetime
from pathlib import Path
from flask import current_app
from app import create_app
from app.models.bulk_job import BulkJob

logger = logging.getLogger(__name__)

# Import enrichment coordinator if available
try:
    import sys
    sys.path.insert(0, '/app/enrichment_service')
    from coordinator.enrichment_coordinator import trigger_enrichment_after_ocr
    ENRICHMENT_AVAILABLE = True
except ImportError:
    ENRICHMENT_AVAILABLE = False
    logger.warning("Enrichment service not available")


class ResultAggregator:
    """Monitors NSQ jobs for completion and generates final reports"""

    def __init__(self, check_interval=10):
        """
        Initialize result aggregator

        Args:
            check_interval: Seconds between completion checks (default: 10)
        """
        self.check_interval = check_interval

        # Initialize Flask app for MongoDB access
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Get MongoDB connection directly from models
        from app.models import mongo
        self.mongo = mongo

        logger.info(f"Result Aggregator initialized (check interval: {check_interval}s)")

    def run(self):
        """Continuously monitor for completed jobs"""
        logger.info("Result Aggregator starting...")

        try:
            while True:
                self.check_for_completed_jobs()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Result Aggregator shutting down...")
        except Exception as e:
            logger.error(f"Result Aggregator error: {e}", exc_info=True)
        finally:
            if hasattr(self, 'app_context'):
                self.app_context.pop()

    def check_for_completed_jobs(self):
        """
        Find jobs where consumed_count == published_count
        and status == 'processing'
        """
        try:
            completed_jobs = BulkJob.find_ready_for_aggregation(self.mongo)

            if completed_jobs:
                logger.info(f"Found {len(completed_jobs)} jobs ready for aggregation")

            for job in completed_jobs:
                job_id = job['job_id']
                published = job.get('published_count', 0)
                consumed = job.get('consumed_count', 0)

                # Verify job has at least some checkpoint data
                checkpoint = job.get('checkpoint', {})
                results_count = len(checkpoint.get('results', []))
                errors_count = len(checkpoint.get('errors', []))
                total_saved = results_count + errors_count

                logger.info(f"Job {job_id}: published={published}, consumed={consumed}, results={results_count}, errors={errors_count}, total_saved={total_saved}")

                # CRITICAL CHECK: Ensure saved results match published count
                # This prevents race condition where consumed_count == published_count
                # but results haven't been committed to MongoDB yet
                if total_saved < published:
                    logger.warning(f"Job {job_id} data incomplete: {total_saved}/{published} results saved. Waiting for data to settle...")
                    # Skip this round, will retry on next check in 10 seconds
                    continue

                # Additional safety: check if counts make sense
                if total_saved > published:
                    logger.error(f"Job {job_id} data corruption: {total_saved} saved but only {published} published!")
                    try:
                        BulkJob.mark_as_error(self.mongo, job_id, "Data corruption detected: more results than tasks")
                    except Exception as mark_error:
                        logger.error(f"Failed to mark job {job_id} as error: {mark_error}")
                    continue

                # Safety check: ensure we have results or errors (not just completed message processing)
                if total_saved == 0 and published > 0:
                    logger.warning(f"Job {job_id} marked complete but has no results! published={published}, consumed={consumed}")
                    # This might indicate a race condition, skip for now
                    continue

                # All validation passed, proceed with aggregation
                logger.info(f"Aggregating results for job {job_id}")

                # Wait briefly to ensure MongoDB write consistency
                time.sleep(2)

                # Re-fetch job to get latest data
                latest_job = BulkJob.get_by_job_id(self.mongo, job_id)
                if latest_job:
                    job = latest_job

                self.aggregate_job_results(job_id)

        except Exception as e:
            logger.error(f"Error checking for completed jobs: {e}", exc_info=True)

    def aggregate_job_results(self, job_id):
        """
        Generate final reports and update job status

        Args:
            job_id: Job identifier to aggregate
        """
        try:
            # Fetch job from MongoDB
            job = BulkJob.get_by_job_id(self.mongo, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Check entire checkpoint structure
            checkpoint = job.get('checkpoint', {})
            logger.error(f"Job {job_id} checkpoint keys: {list(checkpoint.keys())}")
            logger.error(f"Job {job_id} checkpoint size: {len(str(checkpoint))} bytes")
            logger.error(f"Job {job_id} full checkpoint structure: {checkpoint}")

            results = checkpoint.get('results', [])
            errors = checkpoint.get('errors', [])

            # CRITICAL FIX: Deduplicate results by filename
            # Some files may be processed twice due to NSQ redelivery or race conditions
            # Keep only the first occurrence of each file
            results_before_dedup = len(results)
            results = self._deduplicate_results(results)
            results_after_dedup = len(results)

            if results_before_dedup > results_after_dedup:
                logger.warning(f"Job {job_id}: Removed {results_before_dedup - results_after_dedup} duplicate results")

            logger.error(f"Job {job_id}: {len(results)} successful, {len(errors)} failed")

            # Critical: Log if results exist
            if len(results) > 0:
                logger.error(f"Job {job_id} has {len(results)} results")
                logger.error(f"Job {job_id} first result: {results[0]}")
            else:
                logger.error(f"Job {job_id} has NO results in checkpoint! This is the problem.")
                logger.error(f"Job {job_id} published_count={job.get('published_count', 0)}, consumed_count={job.get('consumed_count', 0)}")

            # Generate statistics
            statistics = self._generate_statistics(results)

            # Create output directory
            output_dir = self._get_output_dir(job_id)
            os.makedirs(output_dir, exist_ok=True)

            # Export results to various formats
            export_files = {}

            # JSON export
            json_file = self._export_to_json(output_dir, job_id, results, errors, statistics)
            export_files['json'] = json_file

            # CSV export
            csv_file = self._export_to_csv(output_dir, job_id, results, errors)
            export_files['csv'] = csv_file

            # Text export
            txt_file = self._export_to_text(output_dir, job_id, results, errors, statistics)
            export_files['txt'] = txt_file

            # Create individual JSON files for each result (for compatibility with threading mode)
            individual_json_files = self._create_individual_json_files(output_dir, results)

            # Create ZIP archive with main reports and individual JSON files
            zip_file = self._create_zip_archive(output_dir, job_id, export_files, individual_json_files)
            export_files['zip'] = zip_file

            # Update job with final results (match threading job format for frontend compatibility)
            final_results = {
                'summary': {
                    'total_files': job.get('total_files', 0),
                    'successful': len(results),
                    'failed': len(errors),
                    'processed_at': datetime.utcnow().isoformat(),
                    'statistics': statistics
                },
                'report_files': export_files,
                'zip_path': zip_file,
                # Add download_url for frontend compatibility
                'download_url': f'/api/bulk/download/{job_id}',
                # Add results_preview for frontend compatibility
                'results_preview': {
                    'total_results': len(results),
                    'successful_samples': [
                        {
                            'file': r.get('file') or r.get('filename') or r.get('file_info', {}).get('filename', 'unknown'),
                            'file_path': r.get('file_path', ''),
                            'confidence': r.get('confidence', 0),
                            'text': r.get('text', ''),
                            'text_length': len(r.get('text', '')),
                            'language': r.get('detected_language', 'unknown'),
                            'provider': r.get('provider', 'unknown')
                        }
                        for r in results
                    ],
                    'error_samples': [
                        {
                            'file': e.get('file') or e.get('filename') or e.get('file_info', {}).get('filename', 'unknown'),
                            'error': e.get('error', 'Unknown error')
                        }
                        for e in errors
                    ]
                }
            }

            BulkJob.mark_as_completed(self.mongo, job_id, final_results)

            logger.info(f"Job {job_id} aggregation completed successfully")

            # Trigger enrichment pipeline if available and enabled
            if ENRICHMENT_AVAILABLE and os.getenv('ENRICHMENT_ENABLED', 'true').lower() == 'true':
                try:
                    collection_id = job.get('collection_id', 'auto')
                    collection_metadata = {
                        'collection_id': collection_id,
                        'collection_name': job.get('collection_name', 'Unknown'),
                        'archive_name': job.get('archive_name', 'Unknown'),
                        'total_documents': len(results)
                    }

                    enrichment_job_id = trigger_enrichment_after_ocr(
                        ocr_job_id=job_id,
                        collection_id=collection_id,
                        collection_metadata=collection_metadata
                    )

                    if enrichment_job_id:
                        logger.info(f"Triggered enrichment job {enrichment_job_id} for OCR job {job_id}")
                    else:
                        logger.warning(f"Failed to trigger enrichment for OCR job {job_id}")

                except Exception as enrich_error:
                    logger.error(f"Error triggering enrichment: {enrich_error}", exc_info=True)

        except Exception as e:
            logger.error(f"Failed to aggregate results for job {job_id}: {e}", exc_info=True)
            try:
                BulkJob.mark_as_error(self.mongo, job_id, str(e))
            except:
                pass

    def _deduplicate_results(self, results):
        """
        Remove duplicate results by filename, keeping only the first occurrence

        Args:
            results: List of result dictionaries

        Returns:
            List of results with duplicates removed
        """
        seen_files = set()
        deduped = []
        duplicates_removed = []

        for result in results:
            # Get filename from result (might be in 'file' or 'filename' field)
            filename = result.get('file') or result.get('filename')

            if filename not in seen_files:
                # First occurrence - keep it
                deduped.append(result)
                seen_files.add(filename)
            else:
                # Duplicate - log and skip
                logger.warning(
                    f"Duplicate result found for: {filename} - "
                    f"provider={result.get('provider')}, "
                    f"text_len={len(result.get('text', ''))}"
                )
                duplicates_removed.append(filename)

        if duplicates_removed:
            logger.info(f"Removed {len(duplicates_removed)} duplicate results: {set(duplicates_removed)}")

        return deduped

    def _generate_statistics(self, results):
        """Generate statistics from processed results"""
        if not results:
            return {
                'total_characters': 0,
                'average_confidence': 0,
                'average_words': 0,
                'average_blocks': 0,
                'languages': []
            }

        total_chars = sum(len(r.get('text', '')) for r in results)
        avg_confidence = sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
        avg_words = sum(r.get('words_count', 0) for r in results) / len(results) if results else 0
        avg_blocks = sum(r.get('blocks_count', 0) for r in results) / len(results) if results else 0

        # Collect unique languages
        languages = set()
        for result in results:
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

    def _get_output_dir(self, job_id):
        """Get output directory for job"""
        base_dir = current_app.config.get('UPLOAD_FOLDER', '/app/uploads')
        return os.path.join(base_dir, 'bulk_results', job_id)

    def _export_to_json(self, output_dir, job_id, results, errors, statistics):
        """Export results to JSON file"""
        output_file = os.path.join(output_dir, f'{job_id}_results.json')

        export_data = {
            'metadata': {
                'job_id': job_id,
                'generated_at': datetime.utcnow().isoformat(),
                'total_files': len(results) + len(errors),
                'successful': len(results),
                'failed': len(errors),
            },
            'summary': statistics,
            'results': results,
            'errors': errors
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        file_size = os.path.getsize(output_file)
        logger.info(f"JSON report exported to: {output_file} ({file_size} bytes)")
        logger.debug(f"JSON export: {len(results)} results, {len(errors)} errors")
        return output_file

    def _export_to_csv(self, output_dir, job_id, results, errors):
        """Export results to CSV file"""
        output_file = os.path.join(output_dir, f'{job_id}_results.csv')

        # Combine successful and error results
        all_results = []
        for result in results:
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
                'Character Count': len(result.get('text', '')),
                'Blocks Count': result.get('blocks_count', 0),
                'Words Count': result.get('words_count', 0),
                'Pages Processed': result.get('pages_processed', 1),
                'Processed At': result.get('processed_at', ''),
                'File Size': file_info.get('size', ''),
                'File Extension': file_info.get('extension', ''),
                'Processing Time': metadata.get('processing_time', ''),
                'Worker ID': metadata.get('worker_id', ''),
                'OCR Text': result.get('text', ''),
                'Error': ''
            }
            all_results.append(row)

        for error in errors:
            row = {
                'File': error.get('file', ''),
                'File Path': error.get('file_path', ''),
                'Status': 'Error',
                'Provider': '',
                'Languages': '',
                'Confidence': '',
                'Detected Language': '',
                'Handwriting': '',
                'Character Count': '',
                'Blocks Count': '',
                'Words Count': '',
                'Pages Processed': '',
                'Processed At': error.get('processed_at', ''),
                'File Size': '',
                'File Extension': '',
                'Processing Time': '',
                'Worker ID': '',
                'OCR Text': '',
                'Error': error.get('error', '')
            }
            all_results.append(row)

        if all_results:
            fieldnames = list(all_results[0].keys())
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)

        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
        logger.info(f"CSV report exported to: {output_file} ({file_size} bytes)")
        logger.debug(f"CSV export: {len(all_results)} total rows")
        return output_file

    def _export_to_text(self, output_dir, job_id, results, errors, statistics):
        """Export results to plain text file"""
        output_file = os.path.join(output_dir, f'{job_id}_results.txt')

        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("=" * 80 + "\n")
            f.write("BULK OCR PROCESSING REPORT\n")
            f.write("=" * 80 + "\n\n")

            # Write summary
            f.write(f"Job ID: {job_id}\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
            f.write(f"Total Files: {len(results) + len(errors)}\n")
            f.write(f"Successful: {len(results)}\n")
            f.write(f"Failed: {len(errors)}\n\n")

            # Write statistics
            if statistics:
                f.write("-" * 80 + "\n")
                f.write("STATISTICS\n")
                f.write("-" * 80 + "\n")
                f.write(f"Total Characters: {statistics.get('total_characters', 0):,}\n")
                f.write(f"Average Confidence: {statistics.get('average_confidence', 0):.2f}\n")
                f.write(f"Average Words per File: {statistics.get('average_words', 0):.2f}\n")
                f.write(f"Average Blocks per File: {statistics.get('average_blocks', 0):.2f}\n")
                languages = statistics.get('languages', [])
                if languages:
                    f.write(f"Languages Detected: {', '.join(languages)}\n")
                f.write("\n")

            # Write successful results
            if results:
                f.write("-" * 80 + "\n")
                f.write("SUCCESSFUL RESULTS\n")
                f.write("-" * 80 + "\n\n")

                for idx, result in enumerate(results, 1):
                    f.write(f"[{idx}] {result.get('file', 'Unknown')}\n")
                    f.write(f"Path: {result.get('file_path', '')}\n")
                    f.write(f"Provider: {result.get('provider', '')}\n")
                    f.write(f"Confidence: {result.get('confidence', 0):.2f}\n")
                    f.write(f"Text Length: {len(result.get('text', ''))} characters\n")
                    f.write(f"Extracted Text:\n{result.get('text', '')}\n")
                    f.write("\n" + "-" * 40 + "\n\n")

            # Write errors
            if errors:
                f.write("-" * 80 + "\n")
                f.write("ERRORS\n")
                f.write("-" * 80 + "\n\n")

                for idx, error in enumerate(errors, 1):
                    f.write(f"[{idx}] {error.get('file', 'Unknown')}\n")
                    f.write(f"Path: {error.get('file_path', '')}\n")
                    f.write(f"Error: {error.get('error', '')}\n")
                    f.write("\n")

        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
        logger.info(f"Text report exported to: {output_file} ({file_size} bytes)")
        logger.debug(f"Text export: {len(results)} successful, {len(errors)} failed")
        return output_file

    def _create_individual_json_files(self, output_dir, results):
        """Create individual JSON file for each processed result"""
        individual_json_folder = os.path.join(output_dir, 'individual_files')
        os.makedirs(individual_json_folder, exist_ok=True)

        individual_json_files = []
        try:
            for result in results:
                # Get original filename without extension
                original_filename = result.get('file', 'unknown')
                base_name = os.path.splitext(original_filename)[0]

                # Create JSON filename
                json_filename = f"{base_name}.json"
                json_filepath = os.path.join(individual_json_folder, json_filename)

                # Write individual JSON file
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                individual_json_files.append(json_filepath)
                logger.debug(f"Created individual JSON: {json_filename}")

            logger.info(f"Created {len(individual_json_files)} individual JSON files")
        except Exception as e:
            logger.error(f"Error creating individual JSON files: {str(e)}")

        return individual_json_files

    def _create_zip_archive(self, output_dir, job_id, export_files, individual_json_files=None):
        """Create ZIP archive containing all reports and individual JSON files"""
        zip_file = os.path.join(output_dir, f'{job_id}_bulk_ocr_results.zip')

        try:
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add main report files
                for format_type, file_path in export_files.items():
                    if format_type != 'zip' and file_path and os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        logger.debug(f"Added to zip: {arcname}")

                # Add individual JSON files in a subfolder
                if individual_json_files:
                    for json_file in individual_json_files:
                        if os.path.exists(json_file):
                            # Store in 'individual_files/' folder within zip
                            arcname = os.path.join('individual_files', os.path.basename(json_file))
                            zipf.write(json_file, arcname=arcname)
                            logger.debug(f"Added to zip: {arcname}")

            # Log zip file information
            if os.path.exists(zip_file):
                zip_size = os.path.getsize(zip_file)
                logger.info(f"ZIP archive created successfully: {zip_file} ({zip_size} bytes)")

                # List contents for debugging
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zipf_check:
                        file_list = zipf_check.namelist()
                        logger.debug(f"ZIP contents ({len(file_list)} files): {file_list}")
                except Exception as e:
                    logger.error(f"Error reading ZIP contents: {e}")
            else:
                logger.error(f"ZIP file not created at: {zip_file}")
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {str(e)}", exc_info=True)
            raise

        return zip_file
