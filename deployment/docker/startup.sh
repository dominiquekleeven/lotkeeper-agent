#!/bin/bash

echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1 || true

Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset -nolisten tcp -dpi 96 +extension DAMAGE -fbdir /dev/shm -maxclients 256 &
sleep 1

fluxbox -rc /dev/null &
sleep 1

# Set up VNC password if provided, otherwise use no password (local access only)
VNC_ARGS="-display :99 -forever -shared -rfbport 5900 -noxdamage -noxfixes -nowf -noscr -threads"
if [ -n "$VNC_PASSWORD" ]; then
    echo "Setting up VNC with password protection..."
    mkdir -p /home/wineuser/.vnc
    
    x11vnc -storepasswd "$VNC_PASSWORD" /home/wineuser/.vnc/passwd
    
    if [ -f "/home/wineuser/.vnc/passwd" ] && [ -s "/home/wineuser/.vnc/passwd" ]; then
        chown wineuser:wineuser /home/wineuser/.vnc/passwd
        chmod 600 /home/wineuser/.vnc/passwd
        VNC_ARGS="$VNC_ARGS -rfbauth /home/wineuser/.vnc/passwd"
        echo "VNC password protection enabled"
        echo "Password file created:"
        ls -la /home/wineuser/.vnc/passwd
    else
        echo "Failed to create password file, using no password"
        VNC_ARGS="$VNC_ARGS -nopw"
    fi
else
    echo "VNC running without password (local access only)"
    VNC_ARGS="$VNC_ARGS -nopw"
fi

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
echo "Syncing Python dependencies..."
~/.local/bin/uv sync
echo "Starting open-ah-agent (which will start WoW)..."
~/.local/bin/uv run python -m open_ah_agent.main

wait
