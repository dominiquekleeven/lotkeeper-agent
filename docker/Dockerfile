FROM scottyhardy/docker-wine:stable-10.0

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        mesa-utils \
        libgl1-mesa-dri \
        libglx-mesa0 \
        libgl1 \
        libvulkan1 \
        libvulkan1:i386 \
        libgl1-mesa-dri:i386 \
        libglx-mesa0:i386 \
        libgl1:i386 \
        xvfb \
        x11vnc \
        fluxbox \
        xauth \
        novnc \
        websockify \
        winetricks \
        wget \
        curl \
        unzip \
        cabextract \
        p7zip-full \
        winbind \
        xdotool \
        tesseract-ocr \
        tesseract-ocr-eng \
        python3 \
        python3-pip \
        python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

ENV DISPLAY=:99
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV GALLIUM_DRIVER=llvmpipe
ENV MESA_GL_VERSION_OVERRIDE=4.5
ENV WINEDEBUG=-all,-dll,-heap,-loaddll,-fixme
ENV WINEDLLOVERRIDES="mscoree,mshtml="
ENV WINEARCH=win64
ENV WINEPREFIX=/home/wineuser/.wine
ENV WINE_LARGE_ADDRESS_AWARE=1
ENV MESA_NO_ERROR=1
ENV MESA_GLTHREAD=true
ENV __GL_THREADED_OPTIMIZATIONS=1
ENV __GL_SYNC_TO_VBLANK=0
ENV MESA_GLSL_VERSION_OVERRIDE=450
ENV LP_NUM_THREADS=2
ENV WINEESYNC=1
ENV WINEFSYNC=1

# Copy the Python project
COPY pyproject.toml uv.lock /app/
COPY src/ /app/src/

# Set up Python project structure and fix permissions
WORKDIR /app
RUN chown -R 1010:1010 /app

# Copy and make the startup script executable
COPY docker/startup.sh /startup.sh
RUN chmod +x /startup.sh && \
    sed -i 's/\r$//' /startup.sh

# Set back to data directory as working directory
WORKDIR /data