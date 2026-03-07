# GVPOCR - Enterprise OCR Application

A comprehensive enterprise-grade Optical Character Recognition (OCR) application for processing scanned images with typed and handwritten text in English and Hindi.

## Features

- **Multi-Authentication System**
  - Email/Password registration and login
  - Google OAuth 2.0 integration
  - JWT-based authentication with token refresh

- **Project Management**
  - Create, update, and delete OCR projects
  - Organize images by project
  - Track project statistics

- **Image Processing**
  - Upload multiple images (PNG, JPG, TIFF, PDF, etc.)
  - Support for English and Hindi text recognition
  - Handwriting detection mode
  - Batch processing capability
  - **Multiple OCR Provider Support**
    - Google Cloud Vision API
    - Azure Computer Vision
    - Ollama (Gemma3 vision models)
    - VLLM (Vision Language Models)
    - Tesseract OCR (open-source)
    - EasyOCR (deep learning-based)
    - Easy switching between providers in the UI

- **Twin-Panel OCR Review Interface**
  - Side-by-side view of original image and OCR text
  - Real-time text editing and correction
  - Save and resume work
  - Processing status tracking

- **Data Persistence**
  - MongoDB database for project and image metadata
  - Local file storage for uploaded images
  - User session management

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: MongoDB
- **OCR Engines**:
  - Google Cloud Vision API
  - Azure Computer Vision
  - Ollama (Gemma3 vision models)
  - VLLM (Vision Language Models)
  - Tesseract OCR
  - EasyOCR
- **Authentication**: JWT + Google OAuth 2.0
- **File Storage**: Local filesystem

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Zustand
- **Data Fetching**: Axios + TanStack Query
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **Routing**: React Router v6

## Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- MongoDB (running locally or remotely)
- Google Cloud account with:
  - Cloud Vision API enabled
  - OAuth 2.0 credentials configured
  - Service account with Vision API access

## Quick Start with Docker

The easiest way to run GVPOCR is using Docker Compose, which sets up all services automatically.

### Prerequisites for Docker Setup

- Docker and Docker Compose installed
- Google Cloud credentials (see Google Cloud setup below)

### Running with Docker

1. **Clone the repository**

```bash
cd gvpocr
```

2. **Set up environment variables**

```bash
cp .env.docker .env
```

Edit `.env` and configure your Google Cloud credentials:

```env
SECRET_KEY=your-secret-key-here-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-here-change-in-production
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json
```

3. **Place Google Cloud credentials file**

Copy your Google Cloud service account JSON file to the backend directory:

```bash
cp /path/to/your/credentials.json backend/google-credentials.json
```

4. **Start all services**

```bash
docker-compose up -d
```

This will start:
- MongoDB (on port 27017)
- Backend API (on port 5000)
- Frontend (on port 3000)

5. **Access the application**

Open your browser and navigate to `http://localhost:3000`

6. **View logs**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

7. **Stop services**

```bash
docker-compose down
```

To remove all data (including database):

```bash
docker-compose down -v
```

### Docker Commands Reference

```bash
# Build and start services
docker-compose up --build

# Restart a specific service
docker-compose restart backend

# View running containers
docker-compose ps

# Execute commands in a container
docker-compose exec backend python run.py

# View database
docker-compose exec mongodb mongosh gvpocr
```

## Manual Setup Instructions

If you prefer to run services individually without Docker:

### 1. Clone the Repository

```bash
cd gvpocr
```

### 2. Backend Setup

#### Install Python Dependencies

**Option 1: Install All Providers (Recommended for Docker)**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Option 2: Install Minimal + Specific Providers (Recommended for Local)**
```bash
# Install minimal dependencies (Google Vision only)
pip install -r requirements-minimal.txt

# Then install only the providers you need:
pip install -r requirements-azure.txt        # For Azure
pip install -r requirements-tesseract.txt    # For Tesseract
pip install -r requirements-easyocr.txt      # For EasyOCR (large download)
```

**Note:** Ollama and VLLM don't need additional Python dependencies as they use HTTP APIs.

#### Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and configure the following:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
PORT=5000

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/gvpocr

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key-here

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback

# Google Cloud Vision API
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json

# CORS Configuration
CORS_ORIGINS=http://localhost:5173
```

#### Setup Google Cloud

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Cloud Vision API
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID
   - Add authorized redirect URI: `http://localhost:5000/api/auth/google/callback`
5. Create Service Account:
   - Go to IAM & Admin > Service Accounts
   - Create service account with Cloud Vision API access
   - Download JSON key file
6. Update `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

#### Start MongoDB

```bash
# If MongoDB is installed locally
mongod
```

Or use Docker:

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

#### Run Backend Server

```bash
python run.py
```

The backend API will be available at `http://localhost:5000`

### 3. Frontend Setup

#### Install Node Dependencies

```bash
cd ../frontend
npm install
```

#### Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_API_URL=http://localhost:5000/api
```

#### Run Frontend Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## OCR Provider Configuration

GVPOCR supports six different OCR providers. You can switch between them in the UI or set a default provider.

### Enabling/Disabling Providers

You can enable or disable specific providers using environment variables:

```bash
# In your .env file
GOOGLE_VISION_ENABLED=true    # Enable Google Vision
AZURE_ENABLED=true            # Enable Azure
OLLAMA_ENABLED=true           # Enable Ollama
VLLM_ENABLED=false            # Disable VLLM
TESSERACT_ENABLED=true        # Enable Tesseract
EASYOCR_ENABLED=true          # Enable EasyOCR
```

**To disable VLLM** (as requested), set:
```bash
VLLM_ENABLED=false
```

Disabled providers will not appear in the UI dropdown and will not attempt to initialize, saving resources.

### 1. Google Cloud Vision (Default)

Google Cloud Vision API provides high-quality OCR with excellent accuracy.

**Setup:**
1. Follow the Google Cloud setup instructions above
2. Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to your service account key
3. Set `DEFAULT_OCR_PROVIDER=google_vision` in `.env`

**Advantages:**
- Excellent accuracy for printed text
- Good multi-language support
- Handles handwriting reasonably well

### 2. Azure Computer Vision

Microsoft Azure's Computer Vision API provides enterprise-grade OCR with the Read API.

**Setup:**
1. Create an Azure Cognitive Services resource in Azure Portal
2. Get your endpoint URL and subscription key
3. Configure in `.env`:
   ```env
   AZURE_VISION_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_VISION_KEY=your-subscription-key
   DEFAULT_OCR_PROVIDER=azure
   ```

**Advantages:**
- Very accurate for printed text
- Excellent handwriting support with Read API
- Good multi-language support (50+ languages)
- Handles complex documents well
- Enterprise SLA and compliance

**Note:** Requires Azure subscription (free tier available).

### 3. Ollama (Gemma3)

Use Ollama running vision models like Gemma3 or LLaMA 3.2 Vision on your own infrastructure.

**Setup:**
1. Install and run Ollama on a server (e.g., at `172.12.0.83`)
2. Pull a vision model:
   ```bash
   ollama pull llama3.2-vision
   ```
3. Configure in `.env`:
   ```env
   OLLAMA_HOST=http://172.12.0.83:11434
   OLLAMA_MODEL=llama3.2-vision
   DEFAULT_OCR_PROVIDER=ollama
   ```

**Advantages:**
- No API costs (self-hosted)
- Privacy (data stays on your infrastructure)
- Customizable models

**Note:** Ollama requires a server with GPU for good performance.

### 4. VLLM

VLLM provides fast inference for vision-language models.

**Setup:**
1. Set up VLLM server with a vision model (e.g., at `172.12.0.132`)
2. Configure in `.env`:
   ```env
   VLLM_HOST=http://172.12.0.132:8000
   VLLM_MODEL=llama-3.2-11b-vision-instruct
   DEFAULT_OCR_PROVIDER=vllm
   ```

**Advantages:**
- Very fast inference
- Batch processing support
- Excellent for high-throughput scenarios

**Note:** VLLM requires a server with GPU and sufficient VRAM.

### 5. Tesseract OCR

Open-source OCR engine that runs locally without any API costs.

**Setup:**
1. Tesseract is included in the Docker image automatically
2. For local installation (non-Docker):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin

   # macOS
   brew install tesseract tesseract-lang

   # Windows
   # Download installer from https://github.com/UB-Mannheim/tesseract/wiki
   ```
3. Configure in `.env` (optional):
   ```env
   TESSERACT_CMD=/usr/bin/tesseract
   DEFAULT_OCR_PROVIDER=tesseract
   ```

**Advantages:**
- Completely free and open-source
- No API costs or internet required
- Fast processing
- Good for printed text
- Supports 100+ languages
- Privacy-friendly (all processing local)

**Limitations:**
- Less accurate than cloud-based solutions for complex documents
- Struggles with handwriting
- Requires good quality images

**Language Support:** Install additional languages with:
```bash
sudo apt-get install tesseract-ocr-[lang]
```

### 6. EasyOCR

Deep learning-based OCR that supports 80+ languages with high accuracy.

**Setup:**
1. EasyOCR will be installed via requirements.txt
2. For GPU support, ensure you have CUDA installed
3. Configure in `.env`:
   ```env
   EASYOCR_GPU=True  # Set to False if no GPU
   DEFAULT_OCR_PROVIDER=easyocr
   ```

**Advantages:**
- Very accurate for many languages
- Excellent multi-script support (Latin, Chinese, Arabic, Devanagari, etc.)
- Good for both printed and handwritten text
- No API costs
- Works offline
- Supports 80+ languages including:
  - English, Hindi, Spanish, French, German
  - Chinese, Japanese, Korean, Arabic, Thai
  - Bengali, Tamil, Telugu, Kannada, Malayalam, Marathi

**Limitations:**
- Slower than other providers (especially without GPU)
- Requires more memory (downloads models on first use)
- First run per language downloads model files (~100MB each)

**Note:**
- GPU highly recommended for good performance
- First use will download language models (may take time)
- Docker usage: Set `EASYOCR_GPU=False` unless Docker has GPU access

### Switching Providers in UI

Users can switch between available providers in the OCR review interface:
1. Open an image for processing
2. Select the desired provider from the "Provider" dropdown
3. Click "Process OCR"

Only properly configured and available providers will be selectable.

### Provider Comparison

| Provider | Accuracy | Speed | Cost | Languages | Handwriting | Best For |
|----------|----------|-------|------|-----------|-------------|----------|
| **Google Vision** | ⭐⭐⭐⭐⭐ | Fast | Pay per use | 50+ | Good | Production, high accuracy needs |
| **Azure Vision** | ⭐⭐⭐⭐⭐ | Fast | Pay per use | 50+ | Excellent | Enterprise, handwriting |
| **Ollama** | ⭐⭐⭐⭐ | Medium | Free | Many | Good | Self-hosted, privacy |
| **VLLM** | ⭐⭐⭐⭐ | Very Fast | Free | Many | Good | High throughput, batch |
| **Tesseract** | ⭐⭐⭐ | Very Fast | Free | 100+ | Poor | Simple docs, offline |
| **EasyOCR** | ⭐⭐⭐⭐ | Slow | Free | 80+ | Good | Multi-language, Asian scripts |

**Recommendations:**
- **For Production**: Google Vision or Azure (most accurate, enterprise support)
- **For Privacy/Self-hosted**: Ollama, VLLM, Tesseract, or EasyOCR
- **For Offline Use**: Tesseract or EasyOCR
- **For Simple Documents**: Tesseract (fastest free option)
- **For Handwriting**: Azure or EasyOCR
- **For Asian Languages**: EasyOCR or Google Vision
- **For Batch Processing**: VLLM or Tesseract

## Usage Guide

### 1. User Registration/Login

- Navigate to `http://localhost:5173`
- Click "Sign up" to create a new account with email/password
- Or click "Sign in with Google" for OAuth login

### 2. Create a Project

- After login, click "New Project"
- Enter project name and description
- Click "Create"

### 3. Upload Images

- Open a project
- Click "Upload Images"
- Select one or multiple image files
- Supported formats: PNG, JPG, JPEG, TIFF, BMP, GIF, PDF

### 4. Process OCR

- Click on an uploaded image to open the twin-panel view
- **Select OCR Provider** from the dropdown:
  - Google Cloud Vision (cloud-based, high accuracy)
  - Azure Computer Vision (cloud-based, excellent handwriting)
  - Ollama (self-hosted AI models)
  - VLLM (high-performance self-hosted)
  - Tesseract (fast, open-source, offline)
  - EasyOCR (deep learning, multi-language)
- Select language options (English/Hindi)
- Toggle "Handwriting" mode if needed
- Click "Process OCR" to extract text
- The original image appears on the left, OCR text on the right
- Use mouse wheel to zoom in/out on the image for closer inspection

### 5. Review and Edit

- Compare the original image with extracted text
- Manually correct any OCR errors in the text panel
- Click "Save Changes" to persist edits

### 6. Batch Processing

- Upload multiple images to a project
- Use the batch processing API endpoint to process multiple images at once

## API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/google` - Get Google OAuth URL
- `GET /api/auth/google/callback` - Google OAuth callback
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

### Project Endpoints

- `GET /api/projects` - Get all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/:id` - Get project details
- `PUT /api/projects/:id` - Update project
- `DELETE /api/projects/:id` - Delete project
- `GET /api/projects/:id/images` - Get project images
- `POST /api/projects/:id/images` - Upload image
- `DELETE /api/projects/:id/images/:imageId` - Delete image

### OCR Endpoints

- `GET /api/ocr/providers` - Get available OCR providers
- `POST /api/ocr/process/:imageId` - Process single image
  - Body: `{ languages: ['en', 'hi'], handwriting: false, provider: 'google_vision' }`
- `POST /api/ocr/batch-process` - Process multiple images
  - Body: `{ image_ids: [...], languages: ['en'], provider: 'tesseract' }`
- `GET /api/ocr/image/:imageId` - Get image file
- `GET /api/ocr/image/:imageId/details` - Get image details
- `PUT /api/ocr/image/:imageId/text` - Update OCR text

**Available Providers:**
- `google_vision` - Google Cloud Vision API
- `azure` - Azure Computer Vision
- `ollama` - Ollama (Gemma3/LLaMA Vision)
- `vllm` - VLLM
- `tesseract` - Tesseract OCR
- `easyocr` - EasyOCR

## Project Structure

```
gvpocr/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── project.py
│   │   │   └── image.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   └── ocr.py
│   │   ├── services/
│   │   │   ├── google_auth.py
│   │   │   ├── ocr_service.py
│   │   │   └── storage.py
│   │   └── utils/
│   │       └── decorators.py
│   ├── uploads/
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Auth/
│   │   │   ├── Projects/
│   │   │   └── OCRPanel/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example
├── .gitignore
└── README.md
```

## Database Schema

### Users Collection
```javascript
{
  _id: ObjectId,
  email: String,
  name: String,
  password_hash: String (optional),
  google_id: String (optional),
  created_at: DateTime,
  updated_at: DateTime
}
```

### Projects Collection
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,
  name: String,
  description: String,
  image_count: Number,
  created_at: DateTime,
  updated_at: DateTime
}
```

### Images Collection
```javascript
{
  _id: ObjectId,
  project_id: ObjectId,
  filename: String,
  filepath: String,
  original_filename: String,
  ocr_text: String,
  ocr_status: String, // pending, processing, completed, failed
  ocr_processed_at: DateTime,
  created_at: DateTime,
  updated_at: DateTime
}
```

## Troubleshooting

### Backend Issues

**MongoDB Connection Error**
- Ensure MongoDB is running
- Check `MONGO_URI` in `.env`

**Google Cloud Vision API Error**
- Verify service account key file exists
- Check `GOOGLE_APPLICATION_CREDENTIALS` path
- Ensure Vision API is enabled in Google Cloud Console

**OAuth Login Not Working**
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Check redirect URI in Google Cloud Console matches `.env`

### Frontend Issues

**API Connection Error**
- Ensure backend is running on port 5000
- Check `VITE_API_URL` in frontend `.env`
- Verify CORS settings in backend config

**Build Errors**
- Delete `node_modules` and run `npm install` again
- Clear npm cache: `npm cache clean --force`

### OCR Provider Issues

**Provider Shows as "Unavailable"**
- Check environment variables are set correctly
- Verify API keys and endpoints
- Check server connectivity for remote providers (Ollama, VLLM)
- For Tesseract: Ensure `tesseract` command is in PATH
- For EasyOCR: First run will download models (may take time)

**Azure Computer Vision Errors**
- Verify `AZURE_VISION_ENDPOINT` and `AZURE_VISION_KEY`
- Check Azure subscription is active
- Ensure Computer Vision resource is created in Azure Portal

**Tesseract Not Found**
- Docker: Tesseract is pre-installed
- Local: Install Tesseract and set `TESSERACT_CMD` in `.env`
- Linux: `sudo apt-get install tesseract-ocr`
- Mac: `brew install tesseract`
- Windows: Download from official repository

**EasyOCR Slow/Out of Memory**
- Set `EASYOCR_GPU=False` if no GPU available
- EasyOCR downloads models on first use (be patient)
- Reduce concurrent requests
- Consider using smaller images

**Ollama/VLLM Connection Failed**
- Verify server is running and accessible
- Check firewall rules
- Ensure correct IP address and port
- Test connectivity: `curl http://172.12.0.83:11434/api/tags`

## Production Deployment

### Docker Production Deployment (Recommended)

For production deployment using Docker:

1. **Update environment variables**

```bash
# Use strong, unique secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

2. **Modify docker-compose.yml for production**

- Change `FLASK_ENV=production`
- Update `CORS_ORIGINS` to your production domain
- Use Docker secrets for sensitive data
- Set up Docker healthchecks
- Configure resource limits

3. **Use reverse proxy**

Set up Nginx or Traefik as a reverse proxy with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
    }

    location /api {
        proxy_pass http://localhost:5000;
    }
}
```

4. **Deploy with Docker Compose**

```bash
docker-compose -f docker-compose.yml up -d
```

5. **Set up backups**

```bash
# Backup MongoDB data
docker-compose exec mongodb mongodump --out=/data/backup

# Backup uploads directory
tar -czf uploads-backup.tar.gz backend/uploads
```

### Manual Production Deployment

#### Backend

1. Set `FLASK_ENV=production` in `.env`
2. Use production-grade WSGI server (Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
   ```
3. Use environment variables instead of `.env` file
4. Set up reverse proxy (Nginx)
5. Enable HTTPS with SSL certificates

#### Frontend

1. Build production bundle:
   ```bash
   npm run build
   ```
2. Serve `dist/` folder with static file server
3. Update `VITE_API_URL` to production backend URL
4. Configure CDN for static assets

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the repository.
