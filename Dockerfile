# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for audio and GUI (though GUI won't work in headless Docker)
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    libcanberra-gtk-module \
    libcanberra-gtk3-module \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Dash port
EXPOSE 8050

# Expose the UDP Telemetry port
EXPOSE 20777/udp

# Command to run the application
# Note: In Docker, we typically run run_all.py (no GUI) since Docker is headless
CMD ["python", "run_all.py"]
