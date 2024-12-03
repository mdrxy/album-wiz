import os
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
import asyncpg
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io

from . import normalize, query

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

# Configure CORS
origins = [
    "http://localhost:3000",
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    print("I am here!!")
    try:
        print("Reading file contents...")
        contents = await file.read()
        print("File contents read successfully.")
        
        print("Opening image...")
        image = Image.open(io.BytesIO(contents))
        print("Image opened successfully.")
        
        print("Cropping image to square...")
        square_image = normalize.crop_to_square(image)
        print("Image cropped to square successfully.")
        
        print("Vectorizing image...")
        vector = query.vectorize(square_image)
        print("Image vectorized successfully.")
        
        print(f"Vector: {vector}")
        
        # TODO: Stop serialized with the stupid fucking python list.
        return {"message": "Image successfully converted", 
                "vector": vector.tolist()}
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e