#!/bin/bash

# Start the FastAPI application in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait for the application to be up (adjust sleep duration if needed)
sleep 8

# Import the CSV file using the API endpoint
echo "Starting prelim data import via API..."
curl -X POST "http://127.0.0.1:8000/api/albums" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@/app/import.csv"

# Vectorize the data
echo "Starting vectorization..."
curl -X GET "http://127.0.0.1:8000/api/vectorize"

# Keep the container running
wait
