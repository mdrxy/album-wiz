FROM python:3.10-slim
WORKDIR /app
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

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

# Done before copying the rest of the application code to take advantage of Docker's layer caching mechanism
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh
ENV PYTHONPATH "${PYTHONPATH}:/app/"
EXPOSE 8000
CMD ["/app/startup.sh"]