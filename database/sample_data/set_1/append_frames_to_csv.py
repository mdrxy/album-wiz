import os
import pandas as pd
import sys


def append_frames_to_csv(csv_path, frames_folder, output_csv):
    print(f"Loading CSV: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)

    print(f"Scanning frames in folder: {frames_folder}")
    if not os.path.isdir(frames_folder):
        print(f"Error: Folder {frames_folder} not found.")
        sys.exit(1)

    # Get a dictionary mapping original filenames to their associated metadata
    file_metadata = {}
    for _, row in df.iterrows():
        original_file = os.path.basename(row["Input"])
        file_metadata[original_file] = {
            "Ground Truth": row["Ground Truth"],
            "Release": row["Release"],
            "Artist": row["Artist"],
        }

    print("Mapping complete. Starting to process frame files...")
    new_rows = []
    frame_count = 0  # Track number of frames processed

    for frame_file in os.listdir(frames_folder):
        if not frame_file.lower().endswith(".jpg"):
            continue  # Skip non-image or non-jpg files

        parts = frame_file.split("-")
        if len(parts) < 2:
            print(f"Skipping file (not matching schema): {frame_file}")
            continue

        original_file = parts[0] + ".jpg"
        if not os.path.isfile(os.path.join(frames_folder, original_file)):
            original_file = parts[0] + ".JPG"
        frame_path = os.path.join("capture", frame_file)

        if original_file in file_metadata:
            metadata = file_metadata[original_file]
            new_rows.append(
                {
                    "Input": frame_path.replace("\\", "/"),
                    "Ground Truth": metadata["Ground Truth"],
                    "Release": metadata["Release"],
                    "Artist": metadata["Artist"],
                }
            )
            frame_count += 1
        else:
            print(f"No matching metadata for frame: {frame_file}")

    print(f"Processed {frame_count} frames. Appending to CSV...")

    if new_rows:
        # Append new rows to the existing CSV
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df = df.sort_values(by="Input", key=lambda col: col.str.lower()).reset_index(
            drop=True
        )

        # Save updated CSV
        df.to_csv(output_csv, index=False)
        print(f"Updated and sorted CSV saved to {output_csv}")
    else:
        print("No frames matched metadata. CSV unchanged.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python append_frames_to_csv.py <csv_path> <frames_folder> <output_csv>"
        )
        sys.exit(1)

    csv_path = sys.argv[1]
    frames_folder = sys.argv[2]
    output_csv = sys.argv[3]

    append_frames_to_csv(csv_path, frames_folder, output_csv)
