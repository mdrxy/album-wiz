"""
Business logic for the matching process.
"""

import logging
import json
from typing import Dict, List
from torch import no_grad
from fastapi import HTTPException, UploadFile
from app.process.utils import transform_image

logger = logging.getLogger(__name__)


async def vectorize_image(image: UploadFile, model, img_transform) -> list:
    """
    Given an image file, vectorizes it using a pre-trained model
    (following the specified transformation).

    Parameters:
    - image (UploadFile): The image file to vectorize.
    - model: The pre-trained model to use for vectorization.
    - img_transform: The image transformation to apply before vectorization.

    Returns:
    - list: The vectorized image representation.
    """
    # image = image.file.read()
    tensor_image = transform_image(image, img_transform)
    # Ensure the tensor is on the same device as the model
    tensor_image = tensor_image.to(next(model.parameters()).device)

    with no_grad():  # Disable gradient computation for inference
        vector = (
            model(tensor_image).squeeze(0).cpu().numpy()
        )  # Flatten the tensor to 1D

    return vector.tolist()  # Convert to a flat Python list


async def match_vector(image_vector: List[float], n: int, connection) -> List[Dict]:
    """
    Finds the top-n most similar album records based on the provided image vector.

    Parameters:
    - image_vector (List[float]): The vector representation of the uploaded image.
    - n (int): The number of similar records to retrieve.
    - connection: An active asyncpg database connection.

    Returns:
    - List[Dict]: A list of dictionaries containing album metadata and similarity scores.

    Raises:
    - HTTPException: If the database query fails.
    """

    query = """
    SELECT 
        albums.id,
        albums.title AS name,
        albums.release_date,
        albums.album_url AS album_url,
        albums.genres,
        albums.duration_seconds AS total_duration,
        albums.cover_image,
        artists.name AS artist_name,
        1 - (albums.embedding <#> $1) AS similarity,
        COALESCE(
            json_agg(
                json_build_object(
                    'name', tracks.title,
                    'duration', tracks.duration_seconds,
                    'explicit', tracks.explicit
                )
            ) FILTER (WHERE tracks.id IS NOT NULL),
            '[]'
        ) AS tracks
    FROM albums
    JOIN artists ON albums.artist_id = artists.id
    LEFT JOIN tracks ON tracks.album_id = albums.id
    WHERE albums.embedding IS NOT NULL
    GROUP BY albums.id, artists.name
    ORDER BY albums.embedding <#> $1 ASC
    LIMIT $2;
    """

    try:
        # Execute the similarity search query
        records = await connection.fetch(query, image_vector, n)

        # Process and format the results
        matched_records = []
        for record in records:
            # Convert genres "CSV" string to a list
            genres_list = record["genres"].split(",") if record["genres"] else []

            # Ensure tracks is parsed as a proper list
            tracks_list = (
                json.loads(record["tracks"])
                if isinstance(record["tracks"], str)
                else []
            )

            matched_record = {
                "album_name": record["name"],
                "artist_name": record["artist_name"],
                "album_url": record["album_url"],
                "release_date": record["release_date"],
                "genres": genres_list,
                "total_duration": record["total_duration"],
                "album_image": record["cover_image"],
                "similarity": record["similarity"],
                "tracks": tracks_list,
            }

            matched_records.append(matched_record)

        logger.debug("Found %d similar albums.", len(matched_records))
        logger.debug("Similar albums: %s", matched_records)
        return matched_records

    except Exception as e:
        logger.error("Error during similarity search: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to perform similarity search."
        ) from e
