FROM debian:bookworm-slim

FROM nvidia/cuda:12.6.1-runtime-ubuntu22.04

# Install all necessary libraries for running AppImage-based applications
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfuse2 \
    libglib2.0-0 \
    libstdc++6 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libfreetype6 \
    libgl1 \
    libglx0 \
    libglvnd0 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libasound2 \
    libxss1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libpixman-1-0 \
    libxinerama1 \
    libxrandr2 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libdrm2 \
    libgomp1 \
    libvulkan1 \
    curl \
    ca-certificates \
    xvfb \
    xauth \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory with write permissions
RUN mkdir -p /app && chmod 777 /app

# Set up environment for X11 display
ENV PATH="/app:$PATH"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics

# Expose the API port
EXPOSE 1234

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:1234/v1/models || exit 1

# AppImage will be mounted via docker-compose
# Run LM Studio with GPU support - connects to host's X11 display
CMD ["bash", "-c", "chmod +x /app/lmstudio.AppImage && /app/lmstudio.AppImage --no-sandbox"]


