"""
Main FastAPI application.

This module contains the main FastAPI application and defines the API routes.

Each route has /api as a prefix, so the full path to the route is /api/{route}.
"""

import os
import io
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, UploadFile, File, APIRouter
import asyncpg
from PIL import Image

from app import normalize, query
from app.metadata_orchestrator import MetadataOrchestrator


# Configure logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing DiscogsCollector")


# Config database connection

DATABASE_URL = os.getenv("DATABASE_URL")  # From docker-compose.yml


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

orchestrator = MetadataOrchestrator()
router = APIRouter()


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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metadata/{search_query}")
async def get_metadata(search_query: str):
    """
    Collect metadata for a record from multiple sources.
    """
    try:
        metadata = await orchestrator.collect_metadata(search_query)
        return {"query": search_query, "metadata": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/query")
async def vectorize(file: UploadFile = File(...)):
    """
    Endpoint to receive an image file and convert it to a PIL image.
    """
    logger.debug("Received file: %s", file.filename)
    try:
        logger.debug("Reading file contents...")
        contents = await file.read()
        logger.debug("File contents read successfully.")

        logger.debug("Opening image...")
        image = Image.open(io.BytesIO(contents))
        logger.debug("Image opened successfully.")

        logger.debug("Cropping image to square...")
        square_image = normalize.crop_to_square(image)
        logger.debug("Image cropped to square successfully.")

        logger.debug("Vectorizing image...")
        vector = query.vectorize(square_image)
        logger.debug("Image vectorized successfully.")

        logger.debug("Vector: %s", vector)

        return {"message": "Image successfully converted", "vector": vector.tolist()}
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


app.include_router(router, prefix="/api")
