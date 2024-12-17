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
logger.info("Initializing import_albums module")


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
                        INSERT INTO albums (title, artist_id, cover_image, release_date, genres, duration_seconds)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT DO NOTHING;
                        """,
                        row["Release"],
                        artist_id,
                        row["Ground Truth"],
                        row["Released"],
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
