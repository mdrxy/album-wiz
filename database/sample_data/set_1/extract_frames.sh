#!/bin/bash

for file in *.mov; do
  # Extract the base filename without extension
  base_name="${file%.*}"
  # Use ffmpeg to extract frames and save with the desired naming convention
  ffmpeg -i "$file" "${base_name}-%04d.jpg"
done
