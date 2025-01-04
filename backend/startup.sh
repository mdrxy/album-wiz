#!/bin/bash

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Wait for the application to be up and import the CSV file using the API endpoint
echo "Waiting for the application to be up..."
until curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/" | grep -q "200"; do
    echo "Application not up yet, retrying in 1 second..."
    sleep 1
done

echo "Starting prelim data import via API..."
curl -X POST "http://127.0.0.1:8000/api/albums" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@/app/import-albums.csv"

sleep 5
curl -X POST "http://127.0.0.1:8000/api/songs" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@/app/import-songs.csv"

# Vectorize the data
echo "Starting vectorization..."
curl -X GET "http://127.0.0.1:8000/api/vectorize"

# Keep the container running
wait
