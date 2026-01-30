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

# Import inline enrichment service
try:
    from app.services.inline_enrichment_service import get_inline_enrichment_service
    ENRICHMENT_AVAILABLE = True
except ImportError as e:
    ENRICHMENT_AVAILABLE = False
    logger.error(f"Failed to import inline_enrichment_service: {e}", exc_info=True)


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

            # Check if results already have per-file enrichment (from BulkProcessor)
            pre_enriched_results = {}
            unenriched_results = []
            
            for result in results:
                logger.error(f"DEBUG: Processing result keys: {result.keys()}")
                if 'enrichment' in result:
                    pre_enriched_results[result.get('file')] = result.get('enrichment')
                else:
                    unenriched_results.append(result)
            
            if pre_enriched_results:
                logger.info(f"[ENRICHMENT] Found {len(pre_enriched_results)} pre-enriched results from file processing")
            
            # Trigger inline enrichment for unenriched results (BEFORE ZIP creation) - ALWAYS ENABLED
            if unenriched_results and ENRICHMENT_AVAILABLE:
                try:
                    logger.info(f"[ENRICHMENT] Step 1: Starting batch enrichment for remaining {len(unenriched_results)} OCR results")
                    
                    # Initialize inline enrichment service
                    logger.info(f"[ENRICHMENT] Step 2: Initializing enrichment service")
                    enrichment_service = get_inline_enrichment_service()
                    logger.info(f"[ENRICHMENT] Step 2: Service initialized: {enrichment_service}")
                    
                    # Process enrichment synchronously for unenriched results only
                    logger.info(f"[ENRICHMENT] Step 3: Calling enrich_ocr_results with timeout=900s for {len(unenriched_results)} results")
                    enrichment_output = enrichment_service.enrich_ocr_results(unenriched_results, timeout=900)
                    logger.info(f"[ENRICHMENT] Step 3: Enrichment completed, output keys: {list(enrichment_output.keys())}")
                    
                    batch_enriched_results = enrichment_output.get('enriched_results', {})
                    enrichment_stats = enrichment_output.get('statistics', {})
                    logger.info(f"[ENRICHMENT] Step 4: Extracted enriched_results count: {len(batch_enriched_results)}")
                    logger.info(f"[ENRICHMENT] Step 4: Enrichment stats: {enrichment_stats}")
                    
                    logger.info(f"[ENRICHMENT] Step 5: Batch enrichment completed for job {job_id}: "
                    f"{enrichment_stats.get('successful', 0)} successful, "
                    f"{enrichment_stats.get('failed', 0)} failed")
                    
                    # Merge batch-enriched results with pre-enriched ones
                    all_enriched_results = {**pre_enriched_results, **batch_enriched_results}
                    
                    # Save all enriched results to MongoDB for ZIP inclusion
                    if all_enriched_results:
                        logger.info(f"[ENRICHMENT] Step 6: Saving {len(all_enriched_results)} enriched documents to MongoDB (pre-enriched: {len(pre_enriched_results)}, batch-enriched: {len(batch_enriched_results)})")
                        self._save_enriched_results_to_db(job_id, all_enriched_results, enrichment_stats)
                        logger.info(f"[ENRICHMENT] Step 6: Enriched documents saved successfully")
                    else:
                        logger.warning(f"[ENRICHMENT] Step 6: No enriched results to save (all_enriched_results is empty)")
                    
                except Exception as enrich_error:
                    logger.error(f"[ENRICHMENT] ERROR: Batch enrichment failed: {enrich_error}", exc_info=True)
                    # Still use pre-enriched results even if batch enrichment fails
                    if pre_enriched_results:
                        logger.info(f"[ENRICHMENT] Using {len(pre_enriched_results)} pre-enriched results from file processing")
                        try:
                            self._save_enriched_results_to_db(job_id, pre_enriched_results, {})
                        except Exception as save_error:
                            logger.error(f"[ENRICHMENT] Failed to save pre-enriched results: {save_error}")
            elif pre_enriched_results and not unenriched_results:
                logger.info(f"[ENRICHMENT] All results already enriched during file processing, skipping batch enrichment")
                try:
                    self._save_enriched_results_to_db(job_id, pre_enriched_results, {})
                except Exception as save_error:
                    logger.error(f"[ENRICHMENT] Failed to save pre-enriched results: {save_error}")

            # Create ZIP archive with main reports, individual JSON files, AND enrichment data
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
        raw_outputs_folder = os.path.join(output_dir, 'raw_model_outputs')
        os.makedirs(individual_json_folder, exist_ok=True)
        os.makedirs(raw_outputs_folder, exist_ok=True)

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

                # Create raw outputs file if raw_llm_response exists
                raw_llm_response = result.get('raw_llm_response', '')
                if raw_llm_response:
                    raw_json_filename = f"{base_name}_raw_ocr.json"
                    raw_json_filepath = os.path.join(raw_outputs_folder, raw_json_filename)

                    raw_data = {
                        'file': original_filename,
                        'raw_llm_response': raw_llm_response,
                        'processed_at': result.get('processed_at', ''),
                        'provider': result.get('provider', 'unknown')
                    }

                    with open(raw_json_filepath, 'w', encoding='utf-8') as f:
                        json.dump(raw_data, f, indent=2, ensure_ascii=False)

                    individual_json_files.append(raw_json_filepath)
                    logger.debug(f"Created raw OCR output: {raw_json_filename}")

            logger.info(f"Created {len(individual_json_files)} individual JSON files")
        except Exception as e:
            logger.error(f"Error creating individual JSON files: {str(e)}")

        return individual_json_files

    def _create_zip_archive(self, output_dir, job_id, export_files, individual_json_files=None):
        """Create ZIP archive containing all reports, individual JSON files, and enrichment results"""
        zip_file = os.path.join(output_dir, f'{job_id}_bulk_ocr_results.zip')
        
        logger.info(f"[ZIP] Step 8: Starting ZIP creation for job {job_id}")
        logger.info(f"[ZIP] Step 8: ZIP file path: {zip_file}")

        try:
            logger.info(f"[ZIP] Step 9: Opening ZipFile for writing")
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                logger.info(f"[ZIP] Step 9a: Adding main report files")
                
                # Add main report files
                added_count = 0
                for format_type, file_path in export_files.items():
                    if format_type != 'zip' and file_path and os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
                        added_count += 1
                        logger.debug(f"[ZIP] Step 9a: Added to zip: {arcname}")
                
                logger.info(f"[ZIP] Step 9b: Added {added_count} report files to ZIP")

                # Add individual JSON files in a subfolder
                if individual_json_files:
                    logger.info(f"[ZIP] Step 9c: Adding {len(individual_json_files)} individual JSON files")
                    ind_count = 0
                    for json_file in individual_json_files:
                        if os.path.exists(json_file):
                            # Determine which subfolder this file belongs to
                            parent_folder = os.path.basename(os.path.dirname(json_file))
                            if parent_folder == 'raw_model_outputs':
                                arcname = os.path.join('raw_model_outputs', os.path.basename(json_file))
                            else:
                                arcname = os.path.join('individual_files', os.path.basename(json_file))
                            zipf.write(json_file, arcname=arcname)
                            ind_count += 1
                            logger.debug(f"[ZIP] Step 9c: Added to zip: {arcname}")
                    
                    logger.info(f"[ZIP] Step 9d: Added {ind_count} individual JSON files to ZIP")
                else:
                    logger.info(f"[ZIP] Step 9c: No individual JSON files provided")
                
                logger.info(f"[ZIP] Step 9e: Now calling _add_enrichment_results_to_zip")

                # Add enrichment results if available
                enrichment_count = self._add_enrichment_results_to_zip(zipf, job_id)
                if enrichment_count > 0:
                    logger.info(f"Added {enrichment_count} enriched documents to ZIP")

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

    def _add_enrichment_results_to_zip(self, zipf, ocr_job_id):
        """
        Add enrichment results to ZIP archive if they exist
        
        Args:
            zipf: ZipFile object
            ocr_job_id: OCR job ID to find corresponding enriched documents
            
        Returns:
            Count of enriched documents added
        """
        try:
            logger.info(f"[ZIP-ENRICHMENT] Step 10: Starting to add enrichment results for job {ocr_job_id}")
            
            # Find enrichment job(s) for this OCR job
            logger.info(f"[ZIP-ENRICHMENT] Step 10a: Querying enrichment_jobs collection")
            enrichment_jobs = list(self.mongo.db.enrichment_jobs.find({
                'ocr_job_id': ocr_job_id,
                'status': {'$in': ['completed', 'published', 'in_progress']}
            }))
            
            logger.info(f"[ZIP-ENRICHMENT] Step 10a: Found {len(enrichment_jobs)} enrichment jobs")
            
            if not enrichment_jobs:
                logger.info(f"[ZIP-ENRICHMENT] Step 10b: No enrichment jobs found, trying direct enriched_documents query")
                
                # Try direct query for inline enrichment
                enriched_docs = list(self.mongo.db.enriched_documents.find({'ocr_job_id': ocr_job_id}))
                logger.info(f"[ZIP-ENRICHMENT] Step 10b: Direct query for enriched_documents returned {len(enriched_docs)} documents")
                
                if enriched_docs:
                    logger.info(f"[ZIP-ENRICHMENT] Step 10c: Processing {len(enriched_docs)} enriched documents for ZIP")
                    enrichment_count = 0
                    
                    for doc in enriched_docs:
                        try:
                            filename = doc.get('filename', 'unknown')
                            base_name = os.path.splitext(filename)[0]
                            logger.info(f"[ZIP-ENRICHMENT] Step 10d: Adding enriched doc - filename: {filename}, base_name: {base_name}")

                            # Create enriched JSON
                            enriched_json = {
                                'filename': filename,
                                'enriched_data': doc.get('enriched_data', {}),
                                'enrichment_stats': doc.get('enrichment_stats', {}),
                                'created_at': str(doc.get('created_at', '')),
                                'updated_at': str(doc.get('updated_at', ''))
                            }

                            # Add to ZIP
                            arcname = os.path.join('enriched_results', f'{base_name}_enriched.json')
                            zipf.writestr(arcname, json.dumps(enriched_json, indent=2, ensure_ascii=False, default=str))
                            enrichment_count += 1
                            logger.info(f"[ZIP-ENRICHMENT] Step 10e: Added to ZIP: {arcname}")
                            
                        except Exception as e:
                            logger.error(f"[ZIP-ENRICHMENT] ERROR adding doc to ZIP: {e}", exc_info=True)
                            continue
                    
                    logger.info(f"[ZIP-ENRICHMENT] Step 10f: Successfully added {enrichment_count} enriched documents to ZIP")
                    return enrichment_count
                else:
                    logger.warning(f"[ZIP-ENRICHMENT] Step 10b: No enriched documents found for ocr_job_id={ocr_job_id}")
                    return 0
            
            enrichment_count = 0
            
            # For each enrichment job, fetch enriched documents
            logger.info(f"[ZIP-ENRICHMENT] Step 11: Processing {len(enrichment_jobs)} enrichment jobs (NSQ-based)")
            for enrichment_job in enrichment_jobs:
                enrichment_job_id = enrichment_job['_id']
                
                # Fetch enriched documents for this job (from inline enrichment service)
                enriched_docs = list(self.mongo.db.enriched_documents.find({
                    'ocr_job_id': ocr_job_id
                }))
                
                if not enriched_docs:
                    logger.debug(f"No enriched documents found for job {enrichment_job_id}")
                    continue
                
                # Create enriched_results folder in ZIP
                enrichment_folder = 'enriched_results'
                
                # Add individual enriched documents as JSON
                for doc in enriched_docs:
                    try:
                        # Get filename from saved document (from inline enrichment)
                        filename = doc.get('filename', 'unknown')
                        base_name = os.path.splitext(filename)[0]

                        # Create enriched JSON with inline enrichment data
                        enriched_json = {
                            'filename': filename,
                            'enriched_data': doc.get('enriched_data', {}),
                            'enrichment_stats': doc.get('enrichment_stats', {}),
                            'created_at': str(doc.get('created_at', '')),
                            'updated_at': str(doc.get('updated_at', ''))
                        }

                        # Add to ZIP
                        arcname = os.path.join(enrichment_folder, f'{base_name}_enriched.json')
                        zipf.writestr(arcname, json.dumps(enriched_json, indent=2, ensure_ascii=False, default=str))
                        enrichment_count += 1
                        logger.debug(f"Added enriched document to ZIP: {arcname}")
                    except Exception as e:
                        logger.error(f"Error adding enriched document to ZIP: {e}")
                        continue
                
                # Also add enrichment job summary
                try:
                    summary_data = {
                        'enrichment_job_id': enrichment_job_id,
                        'ocr_job_id': ocr_job_id,
                        'status': enrichment_job.get('status'),
                        'total_documents': enrichment_job.get('total_documents', 0),
                        'processed_count': enrichment_job.get('processed_count', 0),
                        'success_count': enrichment_job.get('success_count', 0),
                        'error_count': enrichment_job.get('error_count', 0),
                        'review_count': enrichment_job.get('review_count', 0),
                        'cost_summary': enrichment_job.get('cost_summary', {}),
                        'created_at': str(enrichment_job.get('created_at', '')),
                        'completed_at': str(enrichment_job.get('completed_at', ''))
                    }
                    arcname = os.path.join('enriched_results', 'enrichment_job_summary.json')
                    zipf.writestr(arcname, json.dumps(summary_data, indent=2, ensure_ascii=False, default=str))
                    logger.debug(f"Added enrichment job summary to ZIP: {arcname}")
                except Exception as e:
                    logger.error(f"Error adding enrichment summary to ZIP: {e}")
            
            return enrichment_count
            
        except Exception as e:
            logger.error(f"Error adding enrichment results to ZIP: {e}")
            return 0

    def regenerate_zip_with_enrichment(self, ocr_job_id: str) -> bool:
        """
        Regenerate ZIP file to include enrichment results
        
        Args:
            ocr_job_id: OCR job ID
            
        Returns:
            True if regenerated successfully
        """
        try:
            # Find the job
            job = self.mongo.db.bulk_jobs.find_one({'job_id': ocr_job_id})
            if not job:
                logger.error(f"OCR job {ocr_job_id} not found")
                return False
            
            # Get existing ZIP path
            results = job.get('results', {})
            report_files = results.get('report_files', {})
            old_zip_path = report_files.get('zip', '')
            
            if not old_zip_path or not os.path.exists(old_zip_path):
                logger.error(f"Original ZIP not found: {old_zip_path}")
                return False
            
            logger.info(f"Regenerating ZIP with enrichment data: {old_zip_path}")
            
            # Create new ZIP in temp location
            output_dir = os.path.dirname(old_zip_path)
            temp_zip = os.path.join(output_dir, f'{ocr_job_id}_temp.zip')
            
            # Copy original ZIP and add enrichment data
            with zipfile.ZipFile(old_zip_path, 'r') as zip_in:
                with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    # Copy all existing files
                    for item in zip_in.namelist():
                        data = zip_in.read(item)
                        zip_out.writestr(item, data)
                    
                    # Add enrichment results
                    enrichment_count = self._add_enrichment_results_to_zip(zip_out, ocr_job_id)
                    logger.info(f"Added {enrichment_count} enriched documents to ZIP")
            
            # Replace old ZIP with new one
            if os.path.exists(temp_zip):
                os.replace(temp_zip, old_zip_path)
                logger.info(f"✓ ZIP regenerated successfully: {old_zip_path}")
                return True
            else:
                logger.error("Temp ZIP was not created")
                return False
                
        except Exception as e:
            logger.error(f"Error regenerating ZIP: {e}", exc_info=True)
            return False

    def _save_enriched_results(self, ocr_job_id: str, enriched_results: dict, enrichment_stats: dict):
        """
        Save enriched results to MongoDB for ZIP inclusion
        
        Args:
            ocr_job_id: OCR job ID
            enriched_results: Dictionary of enriched document data
            enrichment_stats: Enrichment processing statistics
        """
        try:
            # Create enrichment documents for storage
            for filename, enriched_data in enriched_results.items():
                enriched_doc = {
                    'ocr_job_id': ocr_job_id,
                    'filename': filename,
                    'enriched_data': enriched_data,
                    'enrichment_stats': enrichment_stats,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                # Store in MongoDB collection for ZIP regeneration
                self.mongo.db.enriched_documents.insert_one(enriched_doc)
                logger.debug(f"Saved enriched document: {filename}")
            
            logger.info(f"Saved {len(enriched_results)} enriched documents to MongoDB for job {ocr_job_id}")
            
            # Regenerate ZIP with enrichment data
            logger.info(f"Regenerating ZIP with enrichment data for job {ocr_job_id}")
            self.regenerate_zip_with_enrichment(ocr_job_id)
            
        except Exception as e:
            logger.error(f"Error saving enriched results: {e}", exc_info=True)

    def _save_enriched_results_to_db(self, ocr_job_id: str, enriched_results: dict, enrichment_stats: dict):
        """
        Save enriched results to MongoDB for ZIP inclusion (without regenerating)
        
        Args:
            ocr_job_id: OCR job ID
            enriched_results: Dictionary of enriched document data
            enrichment_stats: Enrichment processing statistics
        """
        try:
            logger.info(f"[ENRICHMENT-DB] Step 6a: Starting to save enriched results, count={len(enriched_results)}")
            logger.info(f"[ENRICHMENT-DB] Step 6a: OCR Job ID: {ocr_job_id}")
            logger.info(f"[ENRICHMENT-DB] Step 6a: Enrichment Stats: {enrichment_stats}")
            
            # Create enrichment documents for storage
            saved_count = 0
            for filename, enriched_data in enriched_results.items():
                logger.info(f"[ENRICHMENT-DB] Step 6b: Processing file: {filename}")
                logger.info(f"[ENRICHMENT-DB] Step 6b: Enriched data keys: {list(enriched_data.keys()) if isinstance(enriched_data, dict) else 'NOT A DICT'}")
                
                enriched_doc = {
                    'ocr_job_id': ocr_job_id,
                    'filename': filename,
                    'enriched_data': enriched_data,
                    'enrichment_stats': enrichment_stats,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                
                logger.info(f"[ENRICHMENT-DB] Step 6c: Document to insert: {list(enriched_doc.keys())}")
                
                # Store in MongoDB collection for ZIP inclusion
                result = self.mongo.db.enriched_documents.insert_one(enriched_doc)
                saved_count += 1
                logger.info(f"[ENRICHMENT-DB] Step 6d: Saved document with ID: {result.inserted_id}, filename: {filename}")
            
            logger.info(f"[ENRICHMENT-DB] Step 6e: All saved! Total documents inserted: {saved_count}/{len(enriched_results)}")
            logger.info(f"[ENRICHMENT-DB] Step 7: Verifying MongoDB save by querying collection")
            
            # Verify save by querying
            verify_docs = list(self.mongo.db.enriched_documents.find({'ocr_job_id': ocr_job_id}))
            logger.info(f"[ENRICHMENT-DB] Step 7: Verification query returned {len(verify_docs)} documents")
            for doc in verify_docs:
                logger.info(f"[ENRICHMENT-DB] Step 7: Found doc - filename: {doc.get('filename')}, id: {doc.get('_id')}")
            
        except Exception as e:
            logger.error(f"[ENRICHMENT-DB] ERROR: Failed to save enriched results to DB: {e}", exc_info=True)
