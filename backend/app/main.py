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

from app import normalize, query
from app.metadata_orchestrator import MetadataOrchestrator


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
):
    """
    Collect metadata for a record, either from all sources or specific sources.

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
                "source": sources[0],
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


@router.post("/query")
async def vectorize(file: UploadFile = File(...)):
    """
    Endpoint to receive an image file and convert it to a PIL image.
    """
    logger.debug("Received file: %s", file.filename)
    try:
        contents = await file.read()
        logger.debug("File contents read successfully.")

        image = Image.open(io.BytesIO(contents))
        logger.debug("Image opened successfully.")

        square_image = normalize.crop_to_square(image)
        logger.debug("Image cropped to square successfully.")

        vector = query.vectorize(square_image)
        logger.debug("Image vectorized successfully.")

        logger.debug("Vector: %s", vector)

        return {"message": "Image successfully converted", "vector": vector.tolist()}
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
