"""
Business logic for the matching process.
"""

from torch import no_grad
from fastapi import File, UploadFile, HTTPException
from app.process.utils import validate_image, transform_image


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
