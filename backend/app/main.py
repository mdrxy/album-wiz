"""
Contains the main FastAPI application and defines the API routes.

Each route has /api as a prefix, so the full path to the route is /api/{route}.
"""

import io
import os
import logging
import traceback
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter, Query
from fastapi.staticfiles import StaticFiles
import asyncpg
import torch
from torchvision import transforms
from PIL import Image
from pgvector.asyncpg import register_vector

from app.metadata_orchestrator import MetadataOrchestrator
from app.import_albums import import_albums
from app.process.utils import validate_image, get_image
from app.process.cover_extractor import extract_album_cover
from app.process.logic import vectorize_image, match_vector


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing backend")

# Torch setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

EMBEDDING_SIZE = 256  # TODO: put this in .env
model = torch.hub.load("pytorch/vision:v0.10.0", "resnet18", weights=None)
num_features = model.fc.in_features
model.fc = torch.nn.Linear(num_features, EMBEDDING_SIZE)
model.load_state_dict(torch.load("tuned.pth", map_location=device))
model.to(device)
model.eval()

img_transform = transforms.Compose(
    [
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),  # Random crop
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # From docker-compose.yml
MEDIA_DIR = os.getenv("MEDIA_DIR")  # /media


async def lifespan(application: FastAPI) -> AsyncGenerator:
    """
    Database connection pool setup and teardown.

    A connection pool is a cache of database connections maintained so that the
    connections can be reused when needed.

    Function creates a connection pool when the application starts and closes
    the pool when the application stops.

    Parameters:
    - application (FastAPI): The FastAPI application instance.

    Returns:
    - AsyncGenerator: Asynchronous generator to manage the database connection pool.
    """
    # Create the connection pool using DATABASE_URL
    pool = await asyncpg.create_pool(DATABASE_URL, init=register_vector)
    application.state.pool = pool
    yield  # Yield control to the application
    await application.state.pool.close()


# Initialize app and router
app = FastAPI(lifespan=lifespan)
router = APIRouter()
orchestrator = MetadataOrchestrator()

# Mount the /media directory for serving static files (album covers)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


@router.get("/")
async def read_root():
    """
    Default route to test if the API is running.
    """
    return {"message": "Backend is online."}


@router.post("/upload")
async def upload_image(image: UploadFile = File(...)) -> dict:
    """
    Detect the album cover in an image and return the closest matching record from the database.

    Parameters:
    - image (UploadFile): The image file to save.

    Returns:
    - dict: The matched record from the database, or a message if no matches are found.

    Raises:
    - HTTPException: If the image is invalid or an error occurs during processing.

    Example:
    - upload_image(image) -> {"artist": "Artist Name", "album": "Album Name", ...}
    """
    logger.info("Received upload request for file: %s", image.filename)

    if not await validate_image(image):
        raise HTTPException(status_code=400, detail="Invalid image file.")

    try:
        # Step 1: Extract album cover
        image_pil = Image.open(image.file)
        album_cover_bytes = await extract_album_cover(image_pil)

        # Step 2: Fallback to entire image if cover extraction fails
        if album_cover_bytes is None:
            logger.warning("Album cover not extracted. Falling back to full image.")
            image.file.seek(0)  # Reset file pointer
            album_cover_bytes = image.file.read()  # Read raw bytes
            try:
                # Validate raw bytes with PIL
                Image.open(io.BytesIO(album_cover_bytes)).verify()
            except Exception as e:
                logger.error("Fallback image validation failed: %s", e)
                raise HTTPException(
                    status_code=500, detail="Fallback image is invalid or corrupt."
                ) from e

        # Step 3: Vectorize the image
        image_vector = await vectorize_image(album_cover_bytes, model, img_transform)
        if not image_vector or len(image_vector) != EMBEDDING_SIZE:
            raise HTTPException(
                status_code=500,
                detail="Failed to vectorize the image or invalid vector size.",
            )
        logger.debug("Image vector: %s", image_vector)

        # Step 4: Query the database for similar records
        async with app.state.pool.acquire() as connection:
            matched_records = await match_vector(image_vector, 3, connection)

        return (
            matched_records[0] if matched_records else {"message": "No matches found."}
        )

    except Exception as e:
        logger.error("Error processing image: %s", exc_info=e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the image.",
        ) from e


@router.post("/album")
async def upload_album(data: dict) -> dict:
    """
    Endpoint to receive album metadata and store it in the database.

    # TODO: refactor into artist, album keys and subkeys
    Parameters:
    - data (dict): Album metadata to store in the database.
        - artist_name (str): Name of the artist.
        - artist_image (str): URL to the artist image.
        - artist_url (str): URL to the artist's page.
        - album_name (str): Name of the album.
        - album_image (str): URL to the album image.
        - album_url (str): URL to the album
        - release_date (str): Release date of the album.
        - genres (list): List of genres.
        - total_tracks (int): Total number of tracks.
        - tracks (list): List of track metadata dictionaries.
            - name (str): Name of the track.
            - duration (str): Duration of the track.
            - explicit (bool): True if the track is explicit, False if not, None if unknown.

    Returns:
    - dict: Success message if the upload completes and the image is vectorized.

    Raises:
    - HTTPException: If an error occurs during processing.

    Example:
    - upload_album(data) -> {"message": "Uploaded successfully."}
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
            album_id = await connection.fetchval(
                """
                INSERT INTO albums 
                (title, artist_id, image, url, release_date, genres, total_tracks)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (title, artist_id) DO NOTHING
                RETURNING id;
                """,
                data["album_name"],
                artist_id,
                data["album_image"],
                data["album_url"],
                data["release_date"],
                data["genres"],
                data["total_tracks"],
            )

            # If album already exists, fetch its ID
            if not album_id:
                album_id = await connection.fetchval(
                    """
                    SELECT id FROM albums WHERE title = $1 AND artist_id = $2;
                    """,
                    data["album_name"],
                    artist_id,
                )

            # Insert tracks
            for track in data["tracks"]:
                await connection.execute(
                    """
                    INSERT INTO tracks (album_id, title, duration, explicit)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (title, album_id) DO NOTHING;
                    """,
                    album_id,
                    track["name"],
                    track["duration"],
                    track["explicit"],
                )

            # Vectorize the provided album cover
            album_cover = await get_image(data["album_image"])
            if not album_cover:
                logger.error(
                    "Failed to retrieve local image for album ID %d.", album_id
                )
                raise HTTPException(
                    status_code=400, detail="Album image retrieval failed."
                )
            try:
                await validate_image(album_cover)
                image_vector = await vectorize_image(album_cover, model, img_transform)
                if not image_vector:
                    raise ValueError(
                        f"Invalid vector format for album ID {album_id}: {image_vector}"
                    )

                if not isinstance(image_vector, list) or not all(
                    isinstance(x, (float, int)) for x in image_vector
                ):
                    raise ValueError(
                        f"Invalid vector format returned for album ID {album_id}: {image_vector}"
                    )

                # Add the embedding to the album record
                sql_query = "UPDATE albums SET embedding = $1 WHERE id = $2;"
                await connection.execute(sql_query, image_vector, album_id)
            except (ValueError, TypeError) as vectorization_error:
                logger.error(
                    "Error processing album ID %d: %s",
                    album_id,
                    str(vectorization_error),
                )
                raise HTTPException(
                    status_code=500, detail="Vectorization failed."
                ) from vectorization_error

            return {"message": "Uploaded successfully."}
        except Exception as e:
            logger.error("Error uploading album: %s", traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/album/{album_id}")
async def delete_album(album_id: int) -> dict:
    """
    Endpoint to delete an album record from the database.
    If the album is the only one by the artist, the artist will be deleted as well.

    Parameters:
    - album_id (int): ID of the album to delete.

    Returns:
    - dict: Success message if the deletion completes.

    Raises:
    - HTTPException: If the album is not found or an error occurs during deletion.
    """
    async with app.state.pool.acquire() as connection:
        try:
            async with connection.transaction():
                # Get the artist ID of the album
                artist_id = await connection.fetchval(
                    "SELECT artist_id FROM albums WHERE id = $1;", album_id
                )
                if not artist_id:
                    raise HTTPException(
                        status_code=404, detail=f"Album with ID {album_id} not found."
                    )

                # Delete the album
                await connection.execute("DELETE FROM albums WHERE id = $1;", album_id)

                # Check if the artist has any other albums
                remaining_albums = await connection.fetchval(
                    "SELECT COUNT(*) FROM albums WHERE artist_id = $1;", artist_id
                )

                # If no albums remain, delete the artist
                if remaining_albums == 0:
                    await connection.execute(
                        "DELETE FROM artists WHERE id = $1;", artist_id
                    )
            return {"message": "Album deleted successfully."}

        except Exception as e:
            logger.error("Error deleting album: %s", traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/albums")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    """
    Endpoint to upload a CSV file and import album data into the database.

    Temporary files are saved to /tmp and deleted after processing.

    Parameters:
    - file (UploadFile): CSV file containing album data.

    Returns:
    - dict: Success message if the import completes.

    Raises:
    - HTTPException: If the file is not a CSV or an error occurs during import.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    try:
        # Save the file temporarily
        temp_file_path = f"/tmp/{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            contents = await file.read()
            temp_file.write(contents)

        await import_albums(app, temp_file_path)
        os.remove(temp_file_path)

        # Vectorize the album covers
        await vectorize_albums()
        return {"message": "Albums imported successfully and covers vectorized."}
    except Exception as e:
        logger.error("Error uploading CSV: %s", traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Failed to import albums: {str(e)}"
        ) from e


@router.get("/vectorize")
async def vectorize_albums() -> dict:
    """
    Endpoint to vectorize all album covers in the database.

    Returns:
    - dict: Success message if the vectorization completes.

    Raises:
    - HTTPException: If an error occurs during vectorization.
    - ValueError: If the vector format is invalid.
    - TypeError: If the vector format is invalid.
    """
    logger.debug("Starting vectorization of album covers without vectors.")
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

                image = await get_image(image_path)  # UploadFile
                if not image:
                    logger.critical(
                        "Failed to retrieve image for album ID %d.", album_id
                    )
                    continue  # Skip this album and process the next one

                try:
                    await validate_image(image)
                    logger.debug(
                        "Image retrieved successfully for album ID %d.", album_id
                    )

                    image_vector = await vectorize_image(image, model, img_transform)
                    if not isinstance(image_vector, list) or not all(
                        isinstance(x, (float, int)) for x in image_vector
                    ):
                        raise ValueError(
                            f"Invalid vector format for album ID {album_id}: {image_vector}"
                        )

                    # Log the vector for debugging
                    logger.debug(
                        "Flattened vector for album ID %d: %s", album_id, image_vector
                    )

                    # Update the database
                    sql_query = "UPDATE albums SET embedding = $1 WHERE id = $2;"
                    await connection.execute(sql_query, image_vector, album_id)
                    logger.debug(
                        "Vector updated successfully for album ID %d.", album_id
                    )
                except (ValueError, TypeError) as vectorization_error:
                    logger.critical(
                        "Error processing album ID %d: %s",
                        album_id,
                        str(vectorization_error),
                    )
                    continue  # Proceed with the next album

            return {"message": "Albums vectorized successfully."}
    except Exception as e:
        logger.error("Error during vectorization: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/db/{table_name}")
async def get_table_data(table_name: str) -> list:
    """
    Retrieve all data from the specified table in the database, excluding non-serializable
    fields like 'embedding'.

    Parameters:
    - table_name (str): Name of the table to retrieve data from.

    Returns:
    - list: List of entries the specified table.

    Raises:
    - HTTPException: If the table name is invalid or an error occurs during retrieval.

    Example:
    - get_table_data("albums") -> [{"id": 1, "title": "Album Name", ...}, ...]
    """
    # TODO: Put in .env or config
    allowed_tables = {"artists", "albums", "tracks"}

    if table_name not in allowed_tables:
        raise HTTPException(status_code=400, detail="Invalid table name.")

    # Define fields to exclude per table
    # TODO: Put in .env or config
    excluded_fields = {
        "albums": {"embedding"},
    }

    try:
        async with app.state.pool.acquire() as connection:
            # Retrieve column names for the specified table
            columns = await connection.fetch(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1;
                """,
                table_name,
            )

            # Extract column names into a list
            column_names = [record["column_name"] for record in columns]

            excluded = excluded_fields.get(table_name, set())
            included_columns = [col for col in column_names if col not in excluded]

            columns_str = ", ".join(included_columns)
            sql_query = f"SELECT {columns_str} FROM {table_name};"
            rows = await connection.fetch(sql_query)

            # Convert rows to list of dictionaries
            data = [dict(row) for row in rows]

            return data

    except Exception as e:
        if "does not exist" in str(e).lower():
            logger.debug("Table %s does not exist.", table_name)
            return {"message": f"The table `{table_name}` does not exist."}
        logger.error("Error fetching table data: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


# @router.post("/db/resolve")
# async def upload_resolution(data: dict):
#     """
#     Accept resolved metadata and store it in the database.
#     """

#     try:
#         async with app.state.pool.acquire() as connection:
#             sql_query = """
#                 INSERT INTO resolved_metadata (search_query, resolution)
#                 VALUES ($1, $2)
#                 ON CONFLICT (search_query) DO UPDATE
#                 SET resolution = EXCLUDED.resolution
#             """
#             await connection.execute(sql_query, data["query"], data["resolution"])
#         return {"message": "Resolution uploaded successfully."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e


def hashify(value) -> tuple:
    """
    Recursively convert dictionaries and lists into tuples so that the value is hashable.
    - dict -> tuple of (key, value) pairs sorted by key
    - list -> tuple of hashified elements

    Needed for comparison of metadata fields.

    Parameters:
    - value: The value to hashify.

    Returns:
    - tuple: Hashed value.

    Example:
    - hashify({"a": 1, "b": 2}) -> (("a", 1), ("b", 2))
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

    Parameters:
    - d (dict): The dictionary to flatten.
    - parent_key (str): The parent key for nested dictionaries.
    - sep (str): The separator to use between keys.

    Returns:
    - dict: Flattened dictionary.

    Example:
    - _flatten_dict({"a": {"b": 1, "c": 2}}) -> {"a.b": 1, "a.c": 2}
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

    Parameters:
    - metadata (dict): Metadata from multiple sources.

    Returns:
    - dict: Merged metadata.

    Example:
    - _merge_metadata({"source1": {"a": 1}, "source2": {"b": 2}})
        -> {"a": 1, "b": 2}
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

    Parameters:
    - metadata (dict): Merged metadata from multiple sources.

    Returns:
    - dict: Grouped metadata fields.
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

    Parameters:
    - search_query (str): The query to search for, in the format "{artist} - {album}".
    - source (str, optional): Comma-separated list of sources to collect metadata from.
        If None, collect from all sources.
    - compare (bool, optional): If True and multiple sources are queried, highlight differences
        between sources.
    - include_all (bool, optional): If True, include all fields in the comparison.

    Returns:
    - dict: Metadata from the specified source(s), or a comparison highlighting differences
        if applicable.

    Raises:
    - HTTPException: If the search query is invalid or an error occurs during metadata collection.
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
        logger.error("Error fetching metadata: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/meta-sources")
async def get_sources() -> dict:
    """
    Retrieve the list of available metadata sources.

    Returns:
    - dict: List of available metadata sources.
    """
    sources = [collector.get_name() for collector in orchestrator.collectors]
    return {"sources": sources}


# Prefix all routes with /api
app.include_router(router, prefix="/api")
