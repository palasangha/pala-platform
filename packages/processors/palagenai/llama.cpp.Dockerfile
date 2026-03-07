FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install llama-cpp-python
RUN pip install --no-cache-dir llama-cpp-python

# Create models directory
RUN mkdir -p /models

# Create server script
COPY server.py /app/server.py
RUN chmod +x /app/server.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["python3", "/app/server.py"]
CMD ["-m", "/models/ggml-model-q4_k_m.gguf"]
