FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    xvfb x11vnc novnc websockify python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Copy your app
COPY . /app
WORKDIR /app

# Install Python packages
RUN pip install -r requirements.txt

# Copy custom auto-connect VNC page
COPY auto_vnc.html /usr/share/novnc/

# Create index.html that uses direct websocket connection
RUN echo '<!DOCTYPE html><html><head><title>Mock Draft Simulator</title><meta charset="utf-8"><style>body{margin:0;overflow:hidden;}iframe{width:100vw;height:100vh;border:none;}</style></head><body><iframe src="/vnc_lite.html?autoconnect=1&reconnect=1&resize=scale&show_dot=0&view_only=0"></iframe></body></html>' > /usr/share/novnc/index.html

# Expose port
EXPOSE 8080

# Start command

# Use 1920x1080 resolution for the virtual display
CMD ["bash", "-c", "Xvfb :1 -screen 0 1920x1080x24 & x11vnc -display :1 -nopw -listen 0.0.0.0 -xkb -forever -scale 1920x1080 & websockify --web /usr/share/novnc 8080 0.0.0.0:5900 & sleep 3 && DISPLAY=:1 python main.py"]