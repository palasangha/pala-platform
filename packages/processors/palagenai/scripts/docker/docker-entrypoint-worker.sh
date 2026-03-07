#!/bin/bash
set -e

# Install SSHFS if not already installed
if ! command -v sshfs &> /dev/null; then
    apk add --no-cache sshfs openssh-client
fi

# Mount SSHFS for Bhushanji folder if not already mounted
if [ ! -d "/app/Bhushanji" ] || [ -z "$(ls -A /app/Bhushanji)" ]; then
    mkdir -p /app/Bhushanji
    
    # Wait for SSH server to be ready
    max_attempts=30
    attempt=1
    while ! nc -z gvpocr-ssh-server 22 2>/dev/null; do
        if [ $attempt -eq $max_attempts ]; then
            echo "SSH server did not become available"
            exit 1
        fi
        echo "Waiting for SSH server... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    # Mount using SSHFS
    sshfs -o password_stdin,allow_other,follow_symlinks,reconnect,ServerAliveInterval=15 \
        gvpocr@gvpocr-ssh-server:/home/gvpocr/Bhushanji /app/Bhushanji <<< "mango1" || \
        echo "SSHFS mount failed, continuing with empty directory"
fi

# Run the worker
if [ -z "$WORKER_ID" ]; then
    export WORKER_ID=$(hostname)-worker
fi

python run_worker.py --worker-id $WORKER_ID --nsqlookupd gvpocr-nsqlookupd:4161
