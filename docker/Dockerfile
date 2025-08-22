FROM scottyhardy/docker-wine:stable-10.0

# Install all required packages in a single layer for better caching
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core graphics libraries (only essential ones)
        mesa-utils \
        libgl1-mesa-dri \
        libglx-mesa0 \
        libgl1 \
        libvulkan1 \
        libvulkan1:i386 \
        libgl1-mesa-dri:i386 \
        libglx-mesa0:i386 \
        libgl1:i386 \
        # Virtual display and VNC
        xvfb \
        x11vnc \
        fluxbox \
        xauth \
        novnc \
        websockify \
        # Remove unnecessary packages to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Set optimized display environment variables
ENV DISPLAY=:99
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV GALLIUM_DRIVER=llvmpipe
ENV MESA_GL_VERSION_OVERRIDE=4.5
ENV WINEDEBUG=-all
ENV WINEDLLOVERRIDES="mscoree,mshtml="
ENV WINEARCH=win64
ENV WINEPREFIX=/home/wineuser/.wine
ENV MESA_NO_ERROR=1
ENV MESA_GLTHREAD=true
ENV __GL_THREADED_OPTIMIZATIONS=1
ENV __GL_SYNC_TO_VBLANK=0
ENV MESA_GLSL_VERSION_OVERRIDE=450
ENV LP_NUM_THREADS=2
ENV WINEESYNC=1
ENV WINEFSYNC=1


