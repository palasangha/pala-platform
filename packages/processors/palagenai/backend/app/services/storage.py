import os
import io
import uuid
import json
import csv
import zipfile
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename

class StorageService:
    """Service for file storage operations"""

    def __init__(self, upload_folder, allowed_extensions):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions

        # Create upload folder if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)

    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def save_file(self, file, project_id, project_name=None):
        """
        Save uploaded file to disk

        Args:
            file: FileStorage object from Flask
            project_id: ID of the project
            project_name: Optional name of the project for readable folder names

        Returns:
            tuple: (filename, filepath)
        """
        if not file or not self.allowed_file(file.filename):
            raise ValueError("Invalid file type")

        # Create project-specific folder with name if provided
        if project_name:
            # Sanitize project name for folder
            safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
            folder_name = f"{safe_name}_{project_id}"
        else:
            folder_name = str(project_id)

        project_folder = os.path.join(self.upload_folder, folder_name)
        os.makedirs(project_folder, exist_ok=True)

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        filepath = os.path.join(project_folder, unique_filename)

        # Save file
        file.save(filepath)

        return unique_filename, filepath

    def delete_file(self, filepath):
        """Delete file from disk"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def _find_project_folder(self, project_id):
        """Find project folder by ID (handles both old and new naming schemes)"""
        project_id_str = str(project_id)

        # Check if folder exists with just project_id (old scheme)
        old_folder = os.path.join(self.upload_folder, project_id_str)
        if os.path.exists(old_folder):
            return old_folder

        # Search for folder with new naming scheme (name_id)
        if os.path.exists(self.upload_folder):
            for folder_name in os.listdir(self.upload_folder):
                if folder_name.endswith(f"_{project_id_str}"):
                    return os.path.join(self.upload_folder, folder_name)

        # Return old-style path as fallback
        return old_folder

    def get_file_path(self, project_id, filename):
        """Get full path to file"""
        project_folder = self._find_project_folder(project_id)
        return os.path.join(project_folder, filename)

    def delete_project_files(self, project_id):
        """Delete all files for a project"""
        project_folder = self._find_project_folder(project_id)
        try:
            if os.path.exists(project_folder):
                for filename in os.listdir(project_folder):
                    file_path = os.path.join(project_folder, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(project_folder)
            return True
        except Exception as e:
            print(f"Error deleting project files: {e}")
            return False

    def export_chain_results(self, mongo, job_id):
        """
        Export chain processing results as ZIP file

        Args:
            mongo: MongoDB connection
            job_id: Job identifier

        Returns:
            str: Path to generated ZIP file
        """
        import logging
        logger = logging.getLogger(__name__)

        temp_dir = None
        try:
            from app.models.bulk_job import BulkJob

            # Get job from database
            job = BulkJob.get_by_job_id(mongo, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Create temporary directory for export
            temp_dir = tempfile.mkdtemp(prefix='chain_export_')
            zip_path = os.path.join(temp_dir, f"chain_results_{job_id[:8]}.zip")

            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Create results.json with full step-by-step data
                results_data = {
                    'job_id': job.get('job_id'),
                    'status': job.get('status'),
                    'created_at': job.get('created_at').isoformat() if job.get('created_at') else None,
                    'completed_at': job.get('completed_at').isoformat() if job.get('completed_at') else None,
                    'total_processing_time_ms': 0,
                    'images': [],
                }

                checkpoint = job.get('checkpoint', {})
                results = checkpoint.get('results', [])
                total_time = 0

                for result in results:
                    image_data = {
                        'filename': result.get('file'),
                        'file_path': result.get('file_path'),
                        'status': result.get('status'),
                        'processing_mode': result.get('processing_mode', 'single'),
                        'final_output': result.get('text', ''),
                        'final_output_length': len(result.get('text', '')),
                        'processing_time_ms': result.get('metadata', {}).get('processing_time', 0) * 1000,
                        'steps': result.get('chain_steps', []),
                    }

                    if result.get('processing_mode') == 'chain':
                        image_data['total_chain_time_ms'] = result.get('metadata', {}).get('total_chain_time_ms', 0)
                        total_time += image_data['total_chain_time_ms']

                    results_data['images'].append(image_data)

                results_data['total_processing_time_ms'] = int(total_time)
                results_data['total_images'] = len(results_data['images'])

                # Write results.json
                zipf.writestr('results.json', json.dumps(results_data, indent=2))

                # 2. Create timeline.json for visualization
                timeline_data = {
                    'total_images': len(results),
                    'total_time_ms': int(total_time),
                    'success_count': sum(1 for r in results if r.get('status') == 'success'),
                    'error_count': sum(1 for r in results if r.get('status') == 'error'),
                    'images': [],
                }

                for result in results:
                    if result.get('chain_steps'):
                        image_timeline = {
                            'filename': result.get('file'),
                            'steps': result.get('chain_steps', []),
                        }
                        timeline_data['images'].append(image_timeline)

                zipf.writestr('timeline.json', json.dumps(timeline_data, indent=2))

                # 3. Create summary.csv
                csv_buffer = []
                csv_buffer.append(['Filename', 'Status', 'Output Length', 'Processing Time (ms)', 'Chain Steps'])

                for result in results:
                    chain_steps = len(result.get('chain_steps', []))
                    csv_buffer.append([
                        result.get('file', ''),
                        result.get('status', ''),
                        str(len(result.get('text', ''))),
                        str(int(result.get('metadata', {}).get('processing_time', 0) * 1000)),
                        str(chain_steps),
                    ])

                csv_content = io.StringIO()
                writer = csv.writer(csv_content)
                writer.writerows(csv_buffer)
                zipf.writestr('summary.csv', csv_content.getvalue())

                # 4. Create metadata.json
                metadata = {
                    'job_id': job.get('job_id'),
                    'status': job.get('status'),
                    'processing_mode': job.get('processing_mode', 'single'),
                    'chain_config': job.get('chain_config', {}),
                    'total_files': job.get('total_files', len(results)),
                    'processed_files': job.get('consumed_count', 0),
                    'created_at': job.get('created_at').isoformat() if job.get('created_at') else None,
                    'completed_at': job.get('completed_at').isoformat() if job.get('completed_at') else None,
                    'export_date': datetime.utcnow().isoformat(),
                }

                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))

                # 5. Create final_outputs directory with text files
                for result in results:
                    if result.get('text'):
                        filename = result.get('file', 'output.txt')
                        txt_filename = os.path.splitext(filename)[0] + '.txt'
                        zipf.writestr(f'final_outputs/{txt_filename}', result.get('text', ''))

                # 6. Create step_outputs directories
                if results and results[0].get('chain_steps'):
                    # Get number of steps from first result
                    num_steps = len(results[0].get('chain_steps', []))

                    for step_num in range(1, num_steps + 1):
                        for result in results:
                            steps = result.get('chain_steps', [])
                            if step_num <= len(steps):
                                step = steps[step_num - 1]
                                if step.get('output', {}).get('text'):
                                    filename = result.get('file', 'output.txt')
                                    txt_filename = os.path.splitext(filename)[0] + '.txt'
                                    output_text = step.get('output', {}).get('text', '')
                                    zipf.writestr(
                                        f'step_outputs/step_{step_num}/{txt_filename}',
                                        output_text
                                    )

            logger.info(f"Chain results exported to {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"Error exporting chain results: {str(e)}", exc_info=True)
            # Clean up temp directory on error
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
            raise

        finally:
            # Ensure temp directory is cleaned up
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
