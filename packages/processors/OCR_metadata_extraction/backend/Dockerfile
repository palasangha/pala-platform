# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Tesseract, poppler, OpenGL for OpenCV, and Chrome for Selenium
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-spa \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    smbclient \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with caching enabled
# BuildKit will cache pip packages between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# passed via docker-compose.yml or .env file, not hardcoded in Dockerfile

# Run the application
CMD ["python", "run.py"]
# Run in debug mode with debugpy
#CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "run.py"]
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "run.py"]
