# Use official Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for Python and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install Python dependencies
# Done before copying the rest of the application code to take advantage of Docker's layer caching mechanism
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code to the working directory
COPY . .

# Copy the import.csv and corresponding images
COPY ../database/sample_data/import.csv /app/import.csv

# Copy the startup script
COPY startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Set the PYTHONPATH environment variable
ENV PYTHONPATH "${PYTHONPATH}:/app/"

# Expose the port the application will run on
EXPOSE 8000

# Set the command to run the application
CMD ["/app/startup.sh"]