#!/bin/bash

echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true

# Initialize wine prefix and install dependencies if not already done
if [ ! -f "/home/wineuser/.wine/system.reg" ]; then
    echo "Initializing Wine prefix and installing dependencies..."
    WINEDEBUG=-all wineboot --init
    WINEDEBUG=-all winetricks -q -f win10 ie8 corefonts dotnet48 vcrun2015
    wineserver --wait
    echo "Wine setup complete."
fi

Xvfb :99 -screen 0 1280x720x16 -ac +extension GLX +render -noreset -nolisten tcp -dpi 96 +extension DAMAGE -fbdir /dev/shm -maxclients 256 &
sleep 1

fluxbox -rc /dev/null &
sleep 1

x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -noxdamage -noxfixes -nowf -noscr -threads &
sleep 1

websockify --web=/usr/share/novnc/ 6080 localhost:5900 &
sleep 1

cd /data
WOW_EXECUTABLE=${WOW_EXE:-WoW.exe}
echo "Starting $WOW_EXECUTABLE..."
WINEDEBUG=-all WINEPREFIX=/home/wineuser/.wine wine "$WOW_EXECUTABLE" &

wait
