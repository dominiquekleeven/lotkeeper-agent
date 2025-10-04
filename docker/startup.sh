#!/bin/bash

echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1 || true

Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset -nolisten tcp -dpi 96 +extension DAMAGE -fbdir /dev/shm -maxclients 256 &
sleep 1

fluxbox -rc /dev/null &
sleep 1

# VNC runs without password - security is handled by SSH tunneling
VNC_ARGS="-display :99 -forever -shared -rfbport 5900 -noxdamage -noxfixes -nowf -noscr -threads -nopw"
echo "VNC can be accessed via SSH tunneling at localhost:5900 or noVNC at localhost:6080"

x11vnc $VNC_ARGS &
sleep 1

# Always start noVNC web interface
echo "Starting noVNC web interface on port 6080..."
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 1

# Prepare to start the Python application
# Install UV if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

cd /app
echo "Syncing Python dependencies (base + ocr extra)…"
~/.local/bin/uv sync --extra ocr

echo "Starting lotkeeper-agent..."
~/.local/bin/uv run python -m lotkeeper_agent.main

wait
