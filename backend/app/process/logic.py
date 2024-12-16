"""
Business logic for the matching process.
"""

import logging

from typing import Dict, List
from torch import no_grad
from fastapi import File, UploadFile, HTTPException
from app.process.utils import validate_image, transform_image


logger = logging.getLogger(__name__)


async def extract_album_cover(image: UploadFile = File(...)) -> bytes:
    """
    Extracts the album cover from an image file.

    Args:
    - image (UploadFile): The image file to extract the album cover from.

    Returns:
    - bytes: The extracted album cover image.

    Raises:
    - HTTPException: If the image file is not valid.
    """
    # Validate the image file
    await validate_image(image)

    # Extract the album cover
    # This is a placeholder implementation
    # The actual implementation would use a machine learning model to extract the album cover
    # For now, we will return the image as is
    return await image.read()


async def vectorize_image(image: bytes, model, img_transform) -> list:
    """
    Given an image file, vectorizes it using a pre-trained model (following the specified transformation).

    Parameters:
    - image (bytes): The image file to vectorize.
    - model: The pre-trained model to use for vectorization.
    - img_transform: The image transformation to apply before vectorization.

    Returns:
    - list: The vectorized image representation.
    """
    tensor_image = transform_image(image, img_transform)
    # Ensure the tensor is on the same device as the model
    tensor_image = tensor_image.to(next(model.parameters()).device)

    # Perform vectorization
    with no_grad():  # Disable gradient computation for inference
        vector = (
            model(tensor_image).squeeze(0).cpu().numpy()
        )  # Flatten the tensor to 1D

    return vector.tolist()  # Convert to a flat Python list


async def match_vector(image_vector: List[float], n: int, connection) -> List[Dict]:
    """
    Finds the top-n most similar album records based on the provided image vector.

    Args:
        image_vector (List[float]): The vector representation of the uploaded image.
        n (int): The number of similar records to retrieve.
        connection: An active asyncpg database connection.

    Returns:
        List[Dict]: A list of dictionaries containing album metadata and similarity scores.

    Raises:
        HTTPException: If the database query fails.
    """
    query = """
    SELECT 
        albums.id,
        albums.title,
        albums.artist_id,
        artists.name AS artist_name,
        albums.cover_image,
        1 - (albums.embedding <#> $1) AS similarity
    FROM albums
    JOIN artists ON albums.artist_id = artists.id
    WHERE albums.embedding IS NOT NULL
    ORDER BY albums.embedding <#> $1 ASC
    LIMIT $2;
    """

    try:
        # Execute the similarity search query
        records = await connection.fetch(query, image_vector, n)

        # Process and format the results
        matched_records = []
        for record in records:
            matched_record = {
                "artist_name": record["artist_name"],
                "album_name": record["title"],
                "album_image": record["cover_image"],
                "similarity": record["similarity"],
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
