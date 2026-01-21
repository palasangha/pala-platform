from flask_pymongo import PyMongo
from datetime import datetime
from bson import ObjectId
import os

mongo = PyMongo()

def init_db(app):
    """Initialize database with Flask app"""
    skip_recovery = os.getenv('SKIP_JOB_RECOVERY', 'false').lower() == 'true'
    
    try:
        mongo.init_app(app)
        print("✓ MongoDB initialized successfully")
    except Exception as e:
        if skip_recovery:
            # For remote workers, silently handle MongoDB initialization errors
            print(f"⚠ MongoDB initialization error (remote worker - will retry on first use): {type(e).__name__}")
            # Don't fail startup - MongoDB will be lazily initialized on first use
        else:
            # For main server, re-raise the error
            raise
    
    return mongo

# Import models
from app.models.project import Project
from app.models.image import Image
from app.models.bulk_job import BulkJob
from app.models.export import Export
from app.models.verification_audit import VerificationAudit
