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

# Expose port
EXPOSE 8080

# Start command
CMD ["bash", "-c", "Xvfb :1 -screen 0 1280x720x24 & x11vnc -display :1 -nopw -listen 0.0.0.0 -xkb -forever & websockify --web /usr/share/novnc 8080 0.0.0.0:5900 & sleep 3 && DISPLAY=:1 python main.py"]