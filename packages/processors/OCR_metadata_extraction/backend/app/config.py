import os
from datetime import timedelta
from urllib.parse import quote_plus

class Config:
    """Application configuration"""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # MongoDB
    # Handle URL encoding of credentials if they contain special characters
    _mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr')
    _mongo_username = os.getenv('MONGO_USERNAME')
    _mongo_password = os.getenv('MONGO_PASSWORD')

    if _mongo_uri and '@' in _mongo_uri:
        # If MONGO_URI already contains credentials, use it as-is
        MONGO_URI = _mongo_uri
    elif _mongo_username and _mongo_password:
        # URL encode username and password to handle special characters
        # Only encode if not already encoded (avoid double-encoding)
        _encoded_username = _mongo_username if '%' in _mongo_username else quote_plus(_mongo_username)
        _encoded_password = _mongo_password if '%' in _mongo_password else quote_plus(_mongo_password)
        # Extract host and port from _mongo_uri if provided
        if _mongo_uri and _mongo_uri.startswith('mongodb://'):
            # Parse the URI to get host and database
            uri_parts = _mongo_uri.replace('mongodb://', '').split('/')
            host_part = uri_parts[0]  # e.g., "localhost:27017" or "172.12.0.132:27017"
            db_name = uri_parts[1] if len(uri_parts) > 1 else 'gvpocr'
            MONGO_URI = f'mongodb://{_encoded_username}:{_encoded_password}@{host_part}/{db_name}?authSource=admin'
        else:
            # Fallback to localhost if no URI provided
            MONGO_URI = f'mongodb://{_encoded_username}:{_encoded_password}@mongodb:27017/gvpocr?authSource=admin'
    else:
        MONGO_URI = _mongo_uri

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/auth/google/callback')

    # Google Cloud Vision API
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    # File Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'pdf'}

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')

    # Archipelago Commons
    ARCHIPELAGO_BASE_URL = os.getenv('ARCHIPELAGO_BASE_URL', 'http://localhost:8001')
    ARCHIPELAGO_USERNAME = os.getenv('ARCHIPELAGO_USERNAME', '')
    ARCHIPELAGO_PASSWORD = os.getenv('ARCHIPELAGO_PASSWORD', '')
    ARCHIPELAGO_ENABLED = os.getenv('ARCHIPELAGO_ENABLED', 'false').lower() == 'true'

    # MinIO S3 Storage (for Archipelago file uploads)
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'esmero-minio:9000')  # Internal endpoint for backend
    MINIO_PUBLIC_ENDPOINT = os.getenv('MINIO_PUBLIC_ENDPOINT', 'localhost:9000')  # Public endpoint for browser access
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minio')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minio123')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'archipelago')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
    MINIO_PUBLIC_SECURE = os.getenv('MINIO_PUBLIC_SECURE', 'false').lower() == 'true'  # HTTPS for public endpoint
    MINIO_ENABLED = os.getenv('MINIO_ENABLED', 'true').lower() == 'true'

    # Bulk Processing
    BULK_PARALLEL_JOBS = int(os.getenv('BULK_PARALLEL_JOBS', '4'))  # Number of parallel jobs for bulk processing
    BULK_MAX_PARALLEL_JOBS = 16  # Maximum allowed parallel jobs to prevent resource exhaustion

    # Ollama Configuration
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://172.12.0.83:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'minicpm-v')  # MiniCPM-V for better multilingual OCR
    OLLAMA_ENABLED = os.getenv('OLLAMA_ENABLED', 'true').lower() == 'true'
    OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '600'))  # Request timeout in seconds

    # vLLM Configuration
    VLLM_HOST = os.getenv('VLLM_HOST', 'http://vllm:8000')
    VLLM_MODEL = os.getenv('VLLM_MODEL', 'llama-vision')
    VLLM_API_KEY = os.getenv('VLLM_API_KEY', 'vllm-secret-token')
    VLLM_ENABLED = os.getenv('VLLM_ENABLED', 'true').lower() == 'true'
    VLLM_TIMEOUT = int(os.getenv('VLLM_TIMEOUT', '1200'))  # Request timeout in seconds
    VLLM_MAX_TOKENS = int(os.getenv('VLLM_MAX_TOKENS', '8192'))  # Max tokens in response

    # LM Studio Configuration
    LMSTUDIO_HOST = os.getenv('LMSTUDIO_HOST', 'http://host.docker.internal:1234')
    LMSTUDIO_MODEL = os.getenv('LMSTUDIO_MODEL', 'gemma-3-12b') 
    LMSTUDIO_API_KEY = os.getenv('LMSTUDIO_API_KEY', 'lm-studio')
    LMSTUDIO_ENABLED = os.getenv('LMSTUDIO_ENABLED', 'true').lower() == 'true'
    LMSTUDIO_TIMEOUT = int(os.getenv('LMSTUDIO_TIMEOUT', '600'))  # Request timeout in seconds
    LMSTUDIO_MAX_TOKENS = int(os.getenv('LMSTUDIO_MAX_TOKENS', '4096'))  # Max tokens in response

    # Google Lens / Vision API
    GOOGLE_LENS_MAX_IMAGE_SIZE_MB = int(os.getenv('GOOGLE_LENS_MAX_IMAGE_SIZE_MB', '3'))  # Max image size before compression

    # OCR Image Processing Configuration
    # DPI settings for PDF to image conversion
    OCR_PDF_DPI_DEFAULT = int(os.getenv('OCR_PDF_DPI_DEFAULT', '200'))  # Standard documents
    OCR_PDF_DPI_HIGH_QUALITY = int(os.getenv('OCR_PDF_DPI_HIGH_QUALITY', '300'))  # High-quality/small text
    OCR_PDF_DPI_LOW_QUALITY = int(os.getenv('OCR_PDF_DPI_LOW_QUALITY', '150'))  # Large, clean text
    OCR_PDF_DPI_HANDWRITING = int(os.getenv('OCR_PDF_DPI_HANDWRITING', '300'))  # Handwritten documents

    # Image size optimization
    OCR_MAX_IMAGE_DIMENSION = int(os.getenv('OCR_MAX_IMAGE_DIMENSION', '2048'))  # Max width/height in pixels
    OCR_MIN_IMAGE_DIMENSION = int(os.getenv('OCR_MIN_IMAGE_DIMENSION', '512'))  # Min width/height for quality check
    OCR_IMAGE_QUALITY = int(os.getenv('OCR_IMAGE_QUALITY', '95'))  # JPEG quality (1-100)

    # Auto-optimization settings
    OCR_AUTO_OPTIMIZE_IMAGES = os.getenv('OCR_AUTO_OPTIMIZE_IMAGES', 'false').lower() == 'true'  # Enable auto-resize
    OCR_AUTO_CROP_DOCUMENT = os.getenv('OCR_AUTO_CROP_DOCUMENT', 'false').lower() == 'true'  # Enable auto document cropping
    OCR_DOCUMENT_MIN_AREA_RATIO = float(os.getenv('OCR_DOCUMENT_MIN_AREA_RATIO', '0.1'))  # Min document area (10% of image)

    # NSQ Configuration for distributed message queue
    USE_NSQ = os.getenv('USE_NSQ', 'false').lower() == 'true'  # Enable NSQ-based bulk processing
    NSQD_ADDRESS = os.getenv('NSQD_ADDRESS', 'nsqd:4150')  # NSQ daemon TCP address
    NSQLOOKUPD_ADDRESSES = [addr.strip() for addr in os.getenv('NSQLOOKUPD_ADDRESSES', 'nsqlookupd:4161').split(',')]  # NSQ lookupd HTTP addresses

    # SSHFS Configuration for remote worker file sharing
    SSHFS_ENABLED = os.getenv('SSHFS_ENABLED', 'true').lower() == 'true'
    SSHFS_MAIN_SERVER_USER = os.getenv('SSHFS_MAIN_SERVER_USER', 'sshfs_user')
    SSHFS_MAIN_SERVER_IP = os.getenv('MAIN_SERVER_IP', '172.12.0.132')
    SSHFS_MAIN_SERVER_PORT = int(os.getenv('SSHFS_MAIN_SERVER_PORT', '22'))
    SSHFS_KEY_PATH = os.getenv('SSHFS_KEY_PATH', '/app/ssh_keys/server_sshfs')

    # Model directories for LLM providers (shared via SSHFS)
    SSHFS_OLLAMA_MODELS_PATH = os.getenv('SSHFS_OLLAMA_MODELS_PATH', '/data/models/ollama')
    SSHFS_VLLM_MODELS_PATH = os.getenv('SSHFS_VLLM_MODELS_PATH', '/data/models/vllm')
    SSHFS_LLAMACPP_MODELS_PATH = os.getenv('SSHFS_LLAMACPP_MODELS_PATH', '/data/models/llamacpp')

    # Default SSHFS mount configuration
    SSHFS_DEFAULT_MOUNTS = [
        {
            'remote_path': '/data/Bhushanji',
            'local_path': '/mnt/bhushanji',
            'read_only': True,
            'options': 'allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3'
        },
        {
            'remote_path': '/data/newsletters',
            'local_path': '/mnt/newsletters',
            'read_only': True,
            'options': 'allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3'
        },
        {
            'remote_path': '/mnt/sda1/mango1_home/gvpocr/backend/google-credentials.json',
            'local_path': '/mnt/google-credentials/google-credentials.json',
            'read_only': True,
            'options': 'allow_other,default_permissions,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3'
        }
    ]
