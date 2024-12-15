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


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing import_albums module")


async def import_albums(app: FastAPI, csv_file: str):
    """
    Import album data from a CSV file into the PostgreSQL database.

    Args:
    - app (FastAPI): The FastAPI application instance with the database pool.
    - csv_file (str): Path to the CSV file containing album data.
    """
    logger.info("Starting import from %s", csv_file)

    # Load the CSV file
    try:
        data = pd.read_csv(csv_file)
        logger.debug("CSV file %s loaded successfully", csv_file)
    except Exception as e:
        logger.error("Error reading CSV file: %s", e)
        raise ValueError(f"Error reading CSV file: {e}") from e

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
                        INSERT INTO albums (title, artist_id, cover_image)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING;
                        """,
                        row["Release"],
                        artist_id,
                        row["Ground Truth"],
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
