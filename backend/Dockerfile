# Use official Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for Python and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    libice6 \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install Python dependencies
# Done before copying the rest of the application code to take advantage of Docker's layer caching mechanism
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code to the working directory
COPY . .

# Copy the startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Set the PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/app/"

# Expose the port the application will run on
EXPOSE 8000

# Set the command to run the application
CMD ["/app/startup.sh"]