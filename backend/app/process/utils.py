"""
Module with common functions to validate image files sent by the user.
"""

from io import BytesIO
import io
import os
import logging
from PIL import Image
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

load_dotenv()
MEDIA_DIR = os.getenv("MEDIA_DIR")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Initializing utils module")


async def validate_image(image: UploadFile) -> bool:
    """
    Validates the uploaded image file.

    Parameters:
    - image (UploadFile): The image file to validate.

    Returns:
    - bool: True if the image is valid.

    Raises:
    - HTTPException: If the file type is not supported.
    """
    allowed_extensions = (".jpg", ".jpeg", ".png")
    if not image.filename.lower().endswith(allowed_extensions):
        logger.warning("Unsupported file extension: %s", image.filename)
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(allowed_extensions)} files are supported.",
        )

    logger.info("File %s passed validation.", image.filename)
    return True


async def get_image(path: str) -> UploadFile:
    """
    Returns the image file from the specified path in the MEDIA_DIR as an UploadFile object.

    Parameters:
    - path (str): The path to the image file.

    Returns:
    - UploadFile: The image file.
    """
    image_path = os.path.join(MEDIA_DIR, path)
    with open(image_path, "rb") as image_file:
        contents = image_file.read()
        # Wrap the contents in a BytesIO object and return as UploadFile
        # An UploadFile object is needed for the validate_image function
        # TODO: refactor validate_image?
        return UploadFile(
            filename=os.path.basename(image_path),
            file=BytesIO(contents),
        )


def transform_image(image: bytes, img_transform):
    """
    Transforms an image file into a tensor for vectorization.

    Parameters:
    - file: The image file in bytes to vectorize.
    - img_transform: The image transformation to apply before vectorization.
    """
    # Load the image from bytes
    image = Image.open(io.BytesIO(image)).convert("RGB")  # Ensure 3-channel RGB
    # Apply the transformations
    tensor_image = img_transform(image)
    # Add a batch dimension
    tensor_image = tensor_image.unsqueeze(0)  # Shape: [1, C, H, W]
    return tensor_image
