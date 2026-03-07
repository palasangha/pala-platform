#!/bin/bash
set -e

# Use host X11 display if available, otherwise fall back to Xvfb
if [ -n "$DISPLAY" ] && [ -S "/tmp/.X11-unix/X${DISPLAY#:}" ] 2>/dev/null || [ -e "/tmp/.X11-unix/X0" ]; then
    echo "Using host X11 display: $DISPLAY"
    export DISPLAY="${DISPLAY:-:0}"
else
    echo "Host X11 not available, starting Xvfb virtual display..."
    Xvfb :99 -screen 0 1920x1080x24 &
    XVFB_PID=$!
    echo "Xvfb started with PID $XVFB_PID"
    sleep 2
    export DISPLAY=:99
fi

export XAUTHORITY=/tmp/.Xauthority
export QT_X11_NO_MITSHM=1
export QT_QPA_PLATFORM=xcb
export NVIDIA_VISIBLE_DEVICES=all
export NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics

# Start LMStudio
echo "Starting LMStudio on display $DISPLAY..."
chmod +x /app/lmstudio.AppImage
/app/lmstudio.AppImage --no-sandbox &
LMSTUDIO_PID=$!
echo "LMStudio started with PID $LMSTUDIO_PID"

# Wait for processes
wait
