"""
Module with common functions to validate image files sent by the user.
"""

import os
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

load_dotenv()
MEDIA_DIR = os.getenv("MEDIA_DIR")


async def validate_image(image: UploadFile):
    """
    Validates the uploaded image file.

    Args:
    - image (UploadFile): The image file to validate.

    Returns:
    - True if the image is valid.

    Raises:
    - HTTPException: If the file type is not supported.
    """
    allowed_extensions = (".jpg", ".jpeg", ".png")
    if not image.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(allowed_extensions)} files are supported.",
        )

    return True

    # Additional validations can be added here (e.g., file size, image integrity, etc.)


async def get_image(path: str):
    """
    Returns the image file from the specified path in the MEDIA_DIR.

    Args:
    - path (str): The path to the image file.

    Returns:
    - bytes: The image file.
    """
    # Match the provided path to the image in MEDIA_DIR
    image_path = os.path.join(MEDIA_DIR, path)
    with open(image_path, "rb") as image_file:
        return image_file.read()
