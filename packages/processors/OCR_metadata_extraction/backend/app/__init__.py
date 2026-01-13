from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.models import init_db
import os
import logging

logger = logging.getLogger(__name__)


def _initialize_job_recovery(app):
    """
    Check for interrupted jobs on server startup and prepare them for recovery

    This function runs during app initialization and:
    1. Finds all jobs with status 'processing' (interrupted by server shutdown)
    2. Marks them as 'paused' so they can be manually restored via /api/bulk/restore/<job_id>
    3. Logs information about recoverable jobs
    
    Note: Job recovery is skipped for remote workers via SKIP_JOB_RECOVERY env var
    """
    # Skip job recovery for remote workers that don't have access to the main MongoDB
    skip_recovery = os.getenv('SKIP_JOB_RECOVERY', 'false').lower() == 'true'
    if skip_recovery:
        print("✓ Job recovery skipped (SKIP_JOB_RECOVERY=true)")
        return
    
    try:
        with app.app_context():
            from app.models import mongo
            from app.models.bulk_job import BulkJob

            # Find all jobs that were processing when server shut down
            interrupted_jobs = list(mongo.db.bulk_jobs.find({
                'status': 'processing'
            }))

            if interrupted_jobs:
                paused_count = 0

                # Mark interrupted jobs as 'paused' so they can be manually restored
                # BUT: Skip NSQ jobs as they continue processing independently
                for job in interrupted_jobs:
                    job_id = job.get('job_id')
                    checkpoint = job.get('checkpoint', {})
                    processed_count = checkpoint.get('processed_count', 0)

                    # Check if this is an NSQ job (has published_count/consumed_count)
                    is_nsq_job = 'published_count' in job or 'consumed_count' in job

                    if is_nsq_job:
                        # NSQ jobs continue processing, don't pause them
                        print(f"  • Skipping NSQ job {job_id} - Workers continue processing independently")
                    else:
                        # Threading-based jobs need to be paused
                        mongo.db.bulk_jobs.update_one(
                            {'job_id': job_id},
                            {'$set': {'status': 'paused'}}
                        )
                        print(f"  • Paused job {job_id} - Progress: {processed_count} files processed")
                        print(f"    → Can be restored via: POST /api/bulk/restore/{job_id}")
                        paused_count += 1

                if paused_count > 0:
                    print(f"✓ Job recovery system initialized. {paused_count} threading jobs paused, NSQ jobs continue.")
                else:
                    print("✓ Job recovery system initialized (no interrupted jobs found)")
            else:
                print("✓ Job recovery system initialized (no interrupted jobs found)")

    except Exception as e:
        print(f"⚠ Error during job recovery initialization: {str(e)}")
        logger.error(f"Error during job recovery initialization: {str(e)}", exc_info=True)
        # Don't fail app startup if job recovery fails
        pass


def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize database
    init_db(app)

    # Create upload folder
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Initialize job recovery system (only for main server, skip for remote workers)
    _initialize_job_recovery(app)

    # Initialize supervisor health checker
    try:
        from app.services.supervisor_health_checker import start_health_checker
        check_interval = int(os.getenv('SUPERVISOR_HEALTH_CHECK_INTERVAL', 60))
        start_health_checker(check_interval)
        print(f"✓ Supervisor health checker started (interval: {check_interval}s)")
    except Exception as e:
        print(f"⚠ Warning: Could not start supervisor health checker: {str(e)}")
        logger.warning(f"Could not start supervisor health checker: {str(e)}")

    # Register blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {'status': 'healthy', 'message': 'GVPOCR API is running'}, 200

    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return {
            'name': 'GVPOCR API',
            'version': '1.0.0',
            'description': 'Enterprise OCR Application API'
        }, 200

    return app
