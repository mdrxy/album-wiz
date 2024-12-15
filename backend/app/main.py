"""
Main FastAPI application.

This module contains the main FastAPI application and defines the API routes.

Each route has /api as a prefix, so the full path to the route is /api/{route}.
"""

import os
import io
import logging
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter, Query
import asyncpg
from PIL import Image

from app import normalize
from app.metadata_orchestrator import MetadataOrchestrator
from app.import_albums import import_albums
from app.process.utils import validate_image, get_image
from app.process.logic import extract_album_cover, vectorize_image, match_vector


# Configure logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing backend")


# Config database connection

DATABASE_URL = os.getenv("DATABASE_URL")  # From docker-compose.yml
MEDIA_DIR = os.getenv("MEDIA_DIR")  # /media


async def lifespan(application: FastAPI) -> AsyncGenerator:
    """
    Database connection pool setup and teardown.

    A connection pool is a cache of database connections maintained so that the
    connections can be reused when needed.

    Function creates a connection pool when the application starts and closes
    the pool when the application stops.
    """
    # Create the connection pool using DATABASE_URL
    application.state.pool = await asyncpg.create_pool(DATABASE_URL)
    yield  # Yield control to the application
    await application.state.pool.close()


# Initialize FastAPI application
app = FastAPI(lifespan=lifespan)

router = APIRouter()
orchestrator = MetadataOrchestrator()


@router.get("/")
async def read_root():
    """
    Default route to test if the API is running.
    """
    return {"message": "Hello, World!"}


@router.post("/upload")
async def upload_image(image: UploadFile = File(...)):
    """
    Endpoint to receive an image file from the homepage.

    Args:
    - file (UploadFile): The image file to save.

    Returns:
    - JSON with the matched album or an error message.
    """
    # if not image.filename.endswith((".jpg", ".jpeg", ".png")):
    #     raise HTTPException(
    #         status_code=400, detail="Only .jpg, .jpeg, and .png files are supported."
    #     )

    # # Step 1: Validate the uploaded image
    # if not await validate_image(image):
    #     raise HTTPException(status_code=400, detail="Invalid image file.")

    # # Step 2: Extract the album cover from the image
    # album_cover = await extract_album_cover(image)
    # if not album_cover:
    #     raise HTTPException(status_code=400, detail="No album cover found in the image")

    # # Step 3: Vectorize the extracted album cover
    # image_vector = await vectorize_image(album_cover)
    # if not image_vector:
    #     raise HTTPException(status_code=500, detail="Failed to vectorize the image")

    # # Step 4: Query the database for the most similar records
    # matched_records = await match_vector(image_vector)

    # # Step 5: Return the album metadata
    # # return matched_album

    return {
        "artist_name": "Radiohead",
        "album_name": "OK Computer",
        "genres": [
            "Alternative Rock",
            "Art Rock",
            "Progressive Rock",
            "Electronic",
            "Experimental",
        ],
        "artist_image": "https://i.scdn.co/image/ab6761610000e5eba03696716c9ee605006047fd",
        "album_image": "https://static.independent.co.uk/s3fs-public/thumbnails/image/2017/05/10/11/ok-computer.png",
        "release_date": "1997-05",
        "total_tracks": 12,
        "tracks": [
            {"name": "Airbag", "duration": 295, "explicit": True},
            {"name": "Paranoid Android", "duration": 386, "explicit": None},
            {"name": "Subterranean Homesick Alien", "duration": 269, "explicit": False},
            {"name": "Exit Music (For a Film)", "duration": 270, "explicit": False},
            {"name": "Let Down", "duration": 295, "explicit": False},
            {"name": "Karma Police", "duration": 258, "explicit": False},
            {"name": "Fitter Happier", "duration": 90, "explicit": False},
            {"name": "Electioneering", "duration": 270, "explicit": False},
            {"name": "Climbing Up the Walls", "duration": 297, "explicit": False},
            {"name": "No Surprises", "duration": 228, "explicit": False},
            {"name": "Lucky", "duration": 303, "explicit": None},
            {"name": "The Tourist", "duration": 269, "explicit": True},
        ],
        "artist_url": "https://open.spotify.com/artist/4Z8W4fKeB5YxbusRsdQVPb",
        "album_url": "https://open.spotify.com/album/2fGCAYUMssLKiUAoNdxGLx",
    }


@router.post("/album")
async def upload_album(data: dict):
    """
    Endpoint to receive album metadata and store it in the database.

    Args:
    - data (dict): Album metadata to store in the database.

    Required keys:
    - artist_name (str): Name of the artist.
    - album_name (str): Name of the album.
    - genres (list): List of genres.
    - artist_image (str): URL to the artist image.
    - album_image (str): URL to the album image.
    - release_date (str): Release date of the album.
    - total_tracks (int): Total number of tracks.
    - tracks (list): List of track metadata dictionaries.
    - artist_url (str): URL to the artist's page.
    - album_url (str): URL to the album

    Returns:
    - A success message if the metadata is stored successfully.
    """
    async with app.state.pool.acquire() as connection:
        try:
            # Insert artist
            artist_id = await connection.fetchval(
                """
                INSERT INTO artists (name, image, url)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO UPDATE
                SET image = EXCLUDED.image, url = EXCLUDED.url
                RETURNING id;
                """,
                data["artist_name"],
                data["artist_image"],
                data["artist_url"],
            )

            # Insert album
            album_id = await connection.execute(
                """
                INSERT INTO albums (title, artist_id, image, url, release_date, genres, total_tracks)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING;
                """,
                data["album_name"],
                artist_id,
                data["album_image"],
                data["album_url"],
                data["release_date"],
                data["genres"],
                data["total_tracks"],
            )

            # Insert tracks
            for track in data["tracks"]:
                await connection.execute(
                    """
                    INSERT INTO tracks (album_id, title, duration, explicit)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING;
                    """,
                    album_id,
                    track["name"],
                    track["duration"],
                    track["explicit"],
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/album/{album_id}")
async def delete_album(album_id: int):
    """
    Endpoint to delete an album record from the database.

    Args:
    - album_id (int): ID of the album record to delete.

    Returns:
    - A success message if the record is deleted successfully.
    """
    async with app.state.pool.acquire() as connection:
        try:
            await connection.execute("DELETE FROM albums WHERE id = $1;", album_id)
            return {"message": "Album deleted successfully."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/albums")
async def upload_csv(file: UploadFile = File(...)):
    """
    Endpoint to upload a CSV file and import album data into the database.

    Args:
    - file (UploadFile): CSV file containing album data.

    Returns:
    - A success message if the import completes.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    try:
        # Save the file temporarily
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            contents = await file.read()
            temp_file.write(contents)

        # Invoke the import_albums function
        await import_albums(app, temp_file_path)

        # Delete the temporary file after use
        os.remove(temp_file_path)

        return {"message": "Albums imported successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to import albums: {str(e)}"
        ) from e


@router.get("/vectorize")
async def vectorize_albums():
    """
    Endpoint to vectorize all album covers in the database.
    """
    logger.debug("Starting vectorization of album covers.")
    try:
        async with app.state.pool.acquire() as connection:
            sql_query = "SELECT * FROM albums WHERE embedding IS NULL;"
            rows = await connection.fetch(sql_query)
            logger.debug("Fetched %d albums to vectorize.", len(rows))
            for row in rows:
                album_id = row["id"]
                image_path = row["cover_image"]
                logger.debug(
                    "Processing album ID %d with image path %s.", album_id, image_path
                )

                image = await get_image(image_path)
                logger.debug("Image retrieved successfully for album ID %d.", album_id)
                image_vector = await vectorize_image(image)
                if image_vector:
                    logger.debug(
                        "Vectorized image successfully for album ID. Size: %s, ID: %d.",
                        len(image_vector),
                        album_id,
                    )

                    # TODO: get the encoding and use here

                    sql_query = "UPDATE albums SET embedding = $1 WHERE id = $2;"
                    await connection.execute(sql_query, image_vector, album_id)
                    logger.debug(
                        "Vector updated successfully for album ID %d.", album_id
                    )
            return {"message": "Albums vectorized successfully."}
    except Exception as e:
        logger.error("Error during vectorization: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/db/{table_name}")
async def get_table_data(table_name: str):
    """
    Retrieve all data from the specified table in the database.
    """
    sql_query = f"SELECT * FROM {table_name};"
    try:
        async with app.state.pool.acquire() as connection:
            rows = await connection.fetch(sql_query)
            data = [dict(row) for row in rows]
            return data
    except Exception as e:
        if "does not exist" in str(e).lower():
            logger.debug("Table %s does not exist.", table_name)
            return {"message": f"The table `{table_name}` does not exist."}
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/db/resolve")
async def upload_resolution(data: dict):
    """
    Accept resolved metadata and store it in the database.
    """
    # TODO

    # try:
    #     async with app.state.pool.acquire() as connection:
    #         sql_query = """
    #             INSERT INTO resolved_metadata (search_query, resolution)
    #             VALUES ($1, $2)
    #             ON CONFLICT (search_query) DO UPDATE
    #             SET resolution = EXCLUDED.resolution
    #         """
    #         await connection.execute(sql_query, data["query"], data["resolution"])
    #     return {"message": "Resolution uploaded successfully."}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e)) from e


def hashify(value):
    """
    Recursively convert dictionaries and lists into tuples so that the value is hashable.
    - dict -> tuple of (key, value) pairs sorted by key
    - list -> tuple of hashified elements

    Needed for comparison of metadata fields.
    """
    if isinstance(value, dict):
        # Sort by keys to ensure consistent ordering
        return tuple((k, hashify(v)) for k, v in sorted(value.items()))
    if isinstance(value, list):
        return tuple(hashify(v) for v in value)
    return value  # Scalars (str, int, etc.) are already hashable


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """
    Flatten a nested dictionary for easier comparison of metadata fields.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Convert lists to tuples after we've done all flattening
            # We'll just store them as-is and let hashify handle them
            items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def _merge_metadata(metadata: dict) -> dict:
    """
    Merge metadata from multiple sources into a single dictionary.
    """
    merged = {}
    for _source, source_metadata in metadata.items():
        for key, value in source_metadata.items():
            if key not in merged:
                merged[key] = value
            else:
                # If the key already exists, we can decide how to handle conflicts
                # For simplicity, we'll just overwrite with the latest value
                merged[key] = value
    return merged


def _group_by_field(metadata: dict) -> dict:
    """
    Group metadata fields by their values across different sources.
    """
    grouped = {}
    for source, source_metadata in metadata.items():
        if isinstance(source_metadata, dict):
            flattened = _flatten_dict(source_metadata)
            for key, value in flattened.items():
                if key not in grouped:
                    grouped[key] = {}
                # Convert the value into a hashable form
                grouped[key][source] = hashify(value)
    return grouped


@router.get("/metadata/{search_query}")
async def get_metadata(
    search_query: str,
    source: Optional[str] = Query(None),
    compare: Optional[bool] = Query(False),
    include_all: Optional[bool] = Query(False),
):
    """
    Collect metadata for a record, either from all sources or specific sources.

    NOTE: if only one source returns the album, the album data will return as "identical".

    Args:
    - search_query (str): The query to search for, in the format "{artist} - {album}".
    - source (str, optional): Comma-separated list of sources to collect metadata from.
        If None, collect from all sources.
    - compare (bool, optional): If True and multiple sources are queried, highlight differences
        between sources.

    Returns:
    - dict: Metadata from the specified source(s), or a comparison highlighting differences
        if applicable.
    """
    # Validate that the search query is not empty and is in the correct format
    if not search_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    # Validate {artist} - {album} format with content on both sides of the hyphen
    if " - " not in search_query or not all(
        part.strip() for part in search_query.split(" - ", 1)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Search query must be in the format '{artist} - {album}', "
                "with content on both sides of the hyphen."
            ),
        )

    try:
        available_sources = [
            collector.get_name() for collector in orchestrator.collectors
        ]

        sources = (
            [s.strip() for s in source.split(",")] if source else available_sources
        )
        # Check for invalid sources
        invalid_sources = [src for src in sources if src not in available_sources]
        if invalid_sources:
            logger.warning("Invalid sources requested: %s", invalid_sources)
            return {
                "message": "Some sources are invalid.",
                "invalid_sources": invalid_sources,
                "available_sources": available_sources,
            }

        metadata = {}

        for src in sources:
            metadata[src] = await orchestrator.collect_metadata(src, search_query)

        if len(sources) == 1:
            # If only one source, return metadata directly
            return {
                "query": search_query,
                "sources": sources[0],
                "metadata": metadata[sources[0]],
            }

        if compare:
            # Compare metadata across multiple sources
            differences = {}
            identical = {}
            combined_metadata = _merge_metadata(metadata)
            for field, source_values in _group_by_field(combined_metadata).items():
                unique_values = set(source_values.values())
                if len(unique_values) > 1:
                    differences[field] = source_values  # Fields with differences
                else:
                    identical[field] = next(iter(unique_values))  # Single unique value

            if not include_all:
                # Don't care about fields that will always be different
                # differences.pop("artist.image", None)
                differences.pop("artist.url", None)
                differences.pop("artist.popularity", None)
                # differences.pop("album.image", None)
                differences.pop("album.url", None)

            return {
                "query": search_query,
                "sources": sources,
                "compare": True,
                "differences": differences,
                "identical": identical,
            }

        # Flatten nested metadata dictionaries
        for src, src_metadata in metadata.items():
            metadata[src] = _merge_metadata(src_metadata)

        return {"query": search_query, "sources": sources, "metadata": metadata}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/meta-sources")
async def get_sources():
    """
    Retrieve the list of available metadata sources.
    """
    sources = [collector.get_name() for collector in orchestrator.collectors]
    return {"sources": sources}


@router.post("/query")
async def vectorize(file: UploadFile = File(...)):
    """
    Endpoint to receive an image file and convert it to a PIL image.
    """
    logger.debug("Received file: %s", file)
    try:
        contents = await file.read()
        logger.debug("File contents read successfully.")

        image = Image.open(io.BytesIO(contents))
        logger.debug("Image opened successfully.")

        square_image = normalize.crop_to_square(image)
        logger.debug("Image cropped to square successfully.")

        vector = vectorize(square_image)
        logger.debug("Image vectorized successfully.")

        logger.debug("Vector: %s", vector)

        return {"message": "Image successfully converted", "vector": vector}
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# @router.get("/album")
# async def get_album(vector: List[float] = Query(...)):
#     """
#     Endpoint to receive a vector and return the most similar album.
#     """
#     logger.debug("Received vector: %s", vector)
#     # Check if the vector is valid
#     logger.warning("Vector length: %s, this API is not useable yet.", len(vector))
#     if False and len(vector) != 2048:
#         raise HTTPException(status_code=400, detail="Invalid vector length")

#     try:
#         # TODO: Implement the query.get_album function
#         album = query.get_album(vector)
#         return {"message": "Album found", "album": album}
#     except HTTPException as e:
#         raise HTTPException(status_code=400, detail=str(e)) from e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e


app.include_router(router, prefix="/api")
