from flask import Blueprint, request, jsonify, send_file
from app.models import mongo
from app.models.project import Project
from app.models.image import Image
from app.models.export import Export
from app.utils.decorators import token_required
from app.services.storage import StorageService
from app.config import Config
import json
import os
import csv
import zipfile
import tempfile
from datetime import datetime

projects_bp = Blueprint('projects', __name__)

# Initialize storage service
storage_service = StorageService(Config.UPLOAD_FOLDER, Config.ALLOWED_EXTENSIONS)

@projects_bp.route('', methods=['GET'])
@token_required
def get_projects(current_user_id):
    """Get all projects for current user"""
    try:
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 50, type=int)

        projects = Project.find_by_user(mongo, current_user_id, skip=skip, limit=limit)
        projects_list = [Project.to_dict(p) for p in projects]

        return jsonify({
            'projects': projects_list,
            'count': len(projects_list)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('', methods=['POST'])
@token_required
def create_project(current_user_id):
    """Create a new project"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')

        if not name:
            return jsonify({'error': 'Project name is required'}), 400

        # Create project
        project = Project.create(mongo, current_user_id, name, description)

        return jsonify({
            'message': 'Project created successfully',
            'project': Project.to_dict(project)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>', methods=['GET'])
@token_required
def get_project(current_user_id, project_id):
    """Get a specific project"""
    try:
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)

        if not project:
            return jsonify({'error': 'Project not found'}), 404

        return jsonify({
            'project': Project.to_dict(project)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>', methods=['PUT'])
@token_required
def update_project(current_user_id, project_id):
    """Update a project"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')

        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Update project
        update_data = {}
        if name:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description

        if update_data:
            Project.update(mongo, project_id, current_user_id, update_data)

        # Get updated project
        updated_project = Project.find_by_id(mongo, project_id)

        return jsonify({
            'message': 'Project updated successfully',
            'project': Project.to_dict(updated_project)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>', methods=['DELETE'])
@token_required
def delete_project(current_user_id, project_id):
    """Delete a project"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Delete project files
        storage_service.delete_project_files(project_id)

        # Delete project and associated images
        Project.delete(mongo, project_id, current_user_id)

        return jsonify({
            'message': 'Project deleted successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/images', methods=['GET'])
@token_required
def get_project_images(current_user_id, project_id):
    """Get all images for a project"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 100, type=int)

        images = Image.find_by_project(mongo, project_id, skip=skip, limit=limit)
        images_list = [Image.to_dict(img) for img in images]

        return jsonify({
            'images': images_list,
            'count': len(images_list)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/images', methods=['POST'])
@token_required
def upload_image(current_user_id, project_id):
    """Upload an image to a project"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save file with project name for readable folder structure
        try:
            filename, filepath = storage_service.save_file(file, project_id, project['name'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Create image record
        image = Image.create(
            mongo,
            project_id,
            filename,
            filepath,
            file.filename
        )

        # If OCR text is provided in form data, save it
        ocr_text = request.form.get('ocr_text')
        if ocr_text:
            Image.update_text(mongo, str(image['_id']), ocr_text)
            # Mark as processed
            Image.update_status(mongo, str(image['_id']), 'completed')

        # Update project image count
        Project.increment_image_count(mongo, project_id)

        return jsonify({
            'message': 'Image uploaded successfully',
            'image': Image.to_dict(image)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/bulk-results', methods=['POST'])
@token_required
def save_bulk_results(current_user_id, project_id):
    """Save bulk processing results to project folder"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Get project folder path
        project_folder = storage_service._find_project_folder(project_id)

        # Save result.json with all OCR results
        results_file = os.path.join(project_folder, 'result.json')
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Also save a summary file
        if 'summary' in data:
            summary_file = os.path.join(project_folder, 'summary.txt')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("BULK OCR PROCESSING SUMMARY\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Project: {project['name']}\n")
                f.write(f"Total Files: {data['summary'].get('total_files', 0)}\n")
                f.write(f"Successful: {data['summary'].get('successful', 0)}\n")
                f.write(f"Failed: {data['summary'].get('failed', 0)}\n")
                f.write(f"Source Folder: {data['summary'].get('folder_path', 'N/A')}\n")
                f.write(f"Processed At: {data['summary'].get('processed_at', 'N/A')}\n\n")

                if 'statistics' in data['summary']:
                    stats = data['summary']['statistics']
                    f.write("STATISTICS\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Total Characters: {stats.get('total_characters', 0)}\n")
                    f.write(f"Average Confidence: {stats.get('average_confidence', 0):.2f}%\n")
                    f.write(f"Average Words: {stats.get('average_words', 0):.2f}\n")
                    f.write(f"Languages Detected: {', '.join(stats.get('languages', []))}\n")

        return jsonify({
            'message': 'Bulk results saved successfully',
            'files': {
                'result_json': 'result.json',
                'summary': 'summary.txt'
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/results.json', methods=['GET'])
@token_required
def get_project_results_json(current_user_id, project_id):
    """Get project bulk processing results as JSON"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Get project folder path
        project_folder = storage_service._find_project_folder(project_id)
        results_file = os.path.join(project_folder, 'result.json')

        # Check if result.json exists
        if not os.path.exists(results_file):
            return jsonify({'error': 'No results found for this project'}), 404

        # Read and return the results
        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)

        return jsonify(results_data), 200

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON in results file: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/images/<image_id>', methods=['DELETE'])
@token_required
def delete_image(current_user_id, project_id, image_id):
    """Delete an image"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Get image
        image = Image.find_by_id(mongo, image_id)
        if not image or str(image['project_id']) != project_id:
            return jsonify({'error': 'Image not found'}), 404

        # Delete file
        storage_service.delete_file(image['filepath'])

        # Delete image record
        Image.delete(mongo, image_id)

        # Update project image count
        Project.decrement_image_count(mongo, project_id)

        return jsonify({
            'message': 'Image deleted successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/export-corrected', methods=['GET'])
@token_required
def export_corrected_results(current_user_id, project_id):
    """Export project images with corrected OCR text as ZIP"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        # Get all images with their corrected OCR text
        images = Image.find_by_project(mongo, project_id, skip=0, limit=10000)
        images_list = list(images)

        if not images_list:
            return jsonify({'error': 'No images found in project'}), 404

        # Create temporary directory for export files
        temp_dir = tempfile.mkdtemp(prefix='project_export_')

        try:
            # Prepare data for export
            results = []
            for img in images_list:
                img_dict = Image.to_dict(img)
                result = {
                    'file': img_dict.get('original_filename', img_dict.get('filename', '')),
                    'file_path': img_dict.get('filepath', ''),
                    'text': img_dict.get('ocr_text', ''),
                    'confidence': 100.0,  # Corrected text assumed to be 100% accurate
                    'status': img_dict.get('ocr_status', 'completed'),
                    'processed_at': img_dict.get('ocr_processed_at', img_dict.get('created_at', '')),
                    'text_length': len(img_dict.get('ocr_text', '')),
                    'provider': 'corrected',
                    'image_id': img_dict.get('id', '')
                }
                results.append(result)

            # Generate JSON export
            json_file = os.path.join(temp_dir, 'corrected_results.json')
            json_data = {
                'metadata': {
                    'project_id': project_id,
                    'project_name': project['name'],
                    'exported_at': datetime.now().isoformat(),
                    'total_images': len(results),
                    'description': 'Corrected OCR results from project review'
                },
                'statistics': {
                    'total_characters': sum(r.get('text_length', 0) for r in results),
                    'total_images': len(results),
                    'average_text_length': sum(r.get('text_length', 0) for r in results) / len(results) if results else 0
                },
                'results': results
            }

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)

            # Generate CSV export
            csv_file = os.path.join(temp_dir, 'corrected_results.csv')
            if results:
                fieldnames = ['file', 'file_path', 'status', 'provider', 'text_length', 'processed_at', 'text']
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    writer.writerows(results)

            # Generate TXT export
            txt_file = os.path.join(temp_dir, 'corrected_results.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("CORRECTED OCR RESULTS EXPORT\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Project: {project['name']}\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Images: {len(results)}\n")
                f.write(f"Total Characters: {sum(r.get('text_length', 0) for r in results)}\n")
                f.write("\n" + "=" * 80 + "\n\n")

                for i, result in enumerate(results, 1):
                    f.write(f"File {i}: {result['file']}\n")
                    f.write("-" * 80 + "\n")
                    f.write(result.get('text', '') + "\n")
                    f.write("\n" + "=" * 80 + "\n\n")

            # Create individual JSON files for each image
            individual_dir = os.path.join(temp_dir, 'individual_files')
            os.makedirs(individual_dir, exist_ok=True)

            for result in results:
                filename = result['file']
                # Create safe filename
                safe_filename = os.path.splitext(filename)[0] + '.json'
                individual_file = os.path.join(individual_dir, safe_filename)

                with open(individual_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'file': result['file'],
                        'text': result['text'],
                        'metadata': {
                            'status': result['status'],
                            'processed_at': result['processed_at'],
                            'text_length': result['text_length'],
                            'provider': result['provider']
                        }
                    }, f, ensure_ascii=False, indent=2)

            # Create ZIP file
            zip_path = os.path.join(temp_dir, f"{project['name']}_corrected_results.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(json_file, arcname='corrected_results.json')
                zipf.write(csv_file, arcname='corrected_results.csv')
                zipf.write(txt_file, arcname='corrected_results.txt')

                # Add individual files
                for filename in os.listdir(individual_dir):
                    file_path = os.path.join(individual_dir, filename)
                    zipf.write(file_path, arcname=os.path.join('individual_files', filename))

            # Get zip file size
            zip_size = os.path.getsize(zip_path)
            zip_filename = f"{project['name']}_corrected_results.zip"

            # Save export record to MongoDB
            export_data = {
                'project_name': project['name'],
                'total_images': len(results),
                'total_characters': sum(r.get('text_length', 0) for r in results),
                'average_text_length': sum(r.get('text_length', 0) for r in results) / len(results) if results else 0,
                'export_format': 'zip',
                'zip_filename': zip_filename,
                'zip_size': zip_size,
                'results_summary': [
                    {
                        'file': r['file'],
                        'text_length': r['text_length'],
                        'status': r['status']
                    }
                    for r in results[:10]  # Store summary of first 10 results
                ]
            }

            Export.create(mongo, current_user_id, project_id, export_data)

            # Send the ZIP file
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )

        except Exception as e:
            # Clean up temp directory on error
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@projects_bp.route('/<project_id>/exports', methods=['GET'])
@token_required
def get_export_history(current_user_id, project_id):
    """Get export history for a project"""
    try:
        # Check if project exists and belongs to user
        project = Project.find_by_id(mongo, project_id, user_id=current_user_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404

        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 50, type=int)

        exports = Export.find_by_project(mongo, project_id, user_id=current_user_id, skip=skip, limit=limit)
        exports_list = [Export.to_dict(exp) for exp in exports]

        return jsonify({
            'exports': exports_list,
            'count': len(exports_list)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
