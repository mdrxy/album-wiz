import os
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
import asyncpg
import query
import backend.app.square as square
from fastapi import UploadFile, File
from PIL import Image
import io

DATABASE_URL = os.getenv("DATABASE_URL") # From docker-compose.yml

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

app = FastAPI(lifespan=lifespan)

# API endpoint to fetch all artists
@app.get("/api/artists")
async def get_artists():
    """
    Retrieve all artists from the database.
    """
    query = "SELECT * FROM artists;"
    try:
        async with app.state.pool.acquire() as connection:
            rows = await connection.fetch(query)
            artists = [dict(row) for row in rows]
            return artists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/query")
async def vectorize(file: UploadFile = File(...)):
    """
    Endpoint to receive an image file and convert it to a PIL image.
    """
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        vector = query.vectorize(image)
        return {"message": "Image successfully converted", 
                "vector": vector}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e