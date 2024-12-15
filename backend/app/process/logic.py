"""
Business logic for the matching process.
"""

import io
from fastapi import File, UploadFile, HTTPException
from PIL import Image
import numpy as np
from app import normalize
from app.process.utils import validate_image


async def extract_album_cover(image: UploadFile):
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


async def vectorize_image(image: UploadFile = File(...)):
    """
    Vectorizes the image file.

    From a PIL Image object, extract a vector representation of the image.

    Args:
    - image (UploadFile): The image file to vectorize.

    Returns:
    - list: A list of floats representing the image vector.

    Raises:
    - HTTPException: If the image file is not valid.
    """
    # Validate the image file
    await validate_image(image)

    try:
        contents = await image.read()
        image = Image.open(io.BytesIO(contents))
        square_image = normalize.crop_to_square(image)
        pixels = np.array(square_image)
        vector = pixels[:3, :, 1].flatten()

        return vector.tolist()
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def match_vector(image_vector):
    """
    Finds the most similar records for a given image vector.

    Args:
    - image_vector (list): A list of floats representing the image vector.

    Returns:
    - dict: A dictionary containing the metadata for the most similar album.

    Raises:
    - HTTPException: If the image vector is not valid.
    """
    try:
        # Find the most similar album
        # album = find_similar_album(image_vector)

        return None
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
