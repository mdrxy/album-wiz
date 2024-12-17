"""
From a .csv file, import albums into the database.

Expects columns:
- Ground truth (image file name string)
- Release (album name string)
- Artist (artist name string)
"""

import logging
import pandas as pd
from fastapi import FastAPI
from datetime import datetime


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing import_csv module")


async def import_albums(app: FastAPI, csv_file: str) -> None:
    """
    Import album data from a CSV file into the PostgreSQL database.

    Parameters:
    - app (FastAPI): The FastAPI application instance with the database pool.
    - csv_file (str): Path to the CSV file containing album data.

    Returns:
    - None

    Raises:
    - ValueError: If there is an error reading the CSV file.
    - RuntimeError: If there is an error importing the data into the database.
    """
    logger.info("Starting import from %s", csv_file)

    try:
        data = pd.read_csv(csv_file)
        logger.debug("CSV file %s loaded successfully", csv_file)
    except Exception as e:
        logger.error("Error reading CSV file: %s", e)
        raise ValueError(f"Error reading CSV file: {e}") from e

    # Handle the 'Released' column by adding a default day
    if "Released" in data.columns:

        def parse_released(date_str):
            try:
                # Append '-01' to make it 'YYYY-MM-01'
                return datetime.strptime(date_str, "%Y-%m").date()
            except ValueError as ve:
                logger.error("Error parsing date '%s': %s", date_str, ve)
                raise ve

        data["Released"] = data["Released"].apply(parse_released)
    else:
        logger.error("'Released' column is missing in the CSV.")
        raise ValueError("'Released' column is missing in the CSV.")

    # Insert data into the database
    try:
        async with app.state.pool.acquire() as connection:
            async with connection.transaction():
                for _, row in data.iterrows():
                    # Insert artist
                    artist_id = await connection.fetchval(
                        """
                        INSERT INTO artists (name)
                        VALUES ($1)
                        ON CONFLICT (name) DO NOTHING
                        RETURNING id;
                        """,
                        row["Artist"],
                    )

                    if artist_id is None:
                        artist_id = await connection.fetchval(
                            "SELECT id FROM artists WHERE name = $1", row["Artist"]
                        )

                    # Insert album
                    await connection.execute(
                        """
                        INSERT INTO albums (title, artist_id, cover_image, release_date, album_url, genres, duration_seconds)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT DO NOTHING;
                        """,
                        row["Release"],
                        artist_id,
                        row["Ground Truth"],
                        row["Released"],
                        row["AlbumURL"],
                        row["Genres"],
                        row["DurationSeconds"],
                    )
                    logger.debug(
                        "Inserted album '%s' by artist '%s'",
                        row["Release"],
                        row["Artist"],
                    )
        logger.info("Import completed successfully")

    except Exception as e:
        logger.error("Error importing data: %s", e)
        raise RuntimeError(f"Error importing data: {e}") from e


async def import_songs(app: FastAPI, csv_file: str) -> None:
    """
    Import song data from a CSV file into the PostgreSQL database.

    Parameters:
    - app (FastAPI): The FastAPI application instance with the database pool.
    - csv_file (str): Path to the CSV file containing song data.

    Returns:
    - None

    Raises:
    - ValueError: If there is an error reading the CSV file.
    - RuntimeError: If there is an error importing the data into the database.
    """
    logger.info("Starting import from %s", csv_file)

    try:
        data = pd.read_csv(csv_file)
        logger.debug("CSV file %s loaded successfully", csv_file)
    except Exception as e:
        logger.error("Error reading CSV file: %s", e)
        raise ValueError(f"Error reading CSV file: {e}") from e

    # Validate required columns
    required_columns = {"AlbumTitle", "SongTitle", "DurationSeconds", "Explicit"}
    if not required_columns.issubset(data.columns):
        missing = required_columns - set(data.columns)
        logger.error("Missing columns in CSV: %s", missing)
        raise ValueError(f"Missing columns in CSV: {missing}")

    # Clean and convert the 'Explicit' column
    def clean_explicit(value):
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.strip().lower()
            if value_lower in {"true", "t", "yes", "1"}:
                return True
            elif value_lower in {"false", "f", "no", "0"}:
                return False
            elif value_lower == "none" or value_lower == "":
                return None
        # If value is not recognizable, log and set to None
        logger.warning("Unrecognized value for 'Explicit': %s. Setting to NULL.", value)
        return None

    data["Explicit"] = data["Explicit"].apply(clean_explicit)

    # Insert data into the database
    try:
        async with app.state.pool.acquire() as connection:
            async with connection.transaction():
                for _, row in data.iterrows():
                    # Fetch album ID based on AlbumTitle
                    album_id = await connection.fetchval(
                        "SELECT id FROM albums WHERE title = $1",
                        row["AlbumTitle"],
                    )

                    if album_id is None:
                        logger.warning(
                            "Album '%s' not found. Skipping song '%s'.",
                            row["AlbumTitle"],
                            row["SongTitle"],
                        )
                        continue  # Skip songs with non-existent albums

                    # Insert song into tracks table
                    await connection.execute(
                        """
                        INSERT INTO tracks (album_id, title, duration_seconds, explicit)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (title, album_id) DO NOTHING;
                        """,
                        album_id,
                        row["SongTitle"],
                        row["DurationSeconds"],
                        row["Explicit"],
                    )
                    logger.debug(
                        "Inserted song '%s' into album '%s'",
                        row["SongTitle"],
                        row["AlbumTitle"],
                    )
        logger.info("Song import completed successfully")

    except Exception as e:
        logger.error("Error importing songs: %s", e)
        raise RuntimeError(f"Error importing songs: {e}") from e
