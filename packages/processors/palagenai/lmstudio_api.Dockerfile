# LMStudio API Wrapper - Lightweight REST API interface
FROM python:3.11-slim

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
RUN mkdir -p /app && chmod 777 /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    requests==2.31.0 \
    python-dotenv==1.0.0 \
    pydantic==2.5.0 \
    waitress==2.1.2

# Copy the wrapper script
COPY lmstudio_api_wrapper.py /app/lmstudio_api_wrapper.py
RUN chmod +x /app/lmstudio_api_wrapper.py

# Expose the API port
EXPOSE 1234

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:1234/health || exit 1

# Start the wrapper
CMD ["python3", "/app/lmstudio_api_wrapper.py"]
