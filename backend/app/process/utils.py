"""
Module with common functions to validate image files sent by the user.
"""

from io import BytesIO
import io
import os
from PIL import Image
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

from app import normalize

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


async def get_image(path: str) -> UploadFile:
    """
    Returns the image file from the specified path in the MEDIA_DIR as an UploadFile object.

    Args:
    - path (str): The path to the image file.

    Returns:
    - bytes: The image file.
    """
    # Match the provided path to the image in MEDIA_DIR
    image_path = os.path.join(MEDIA_DIR, path)
    with open(image_path, "rb") as image_file:
        # Read the file contents into memory
        contents = image_file.read()
        # Wrap the contents in a BytesIO object and return as UploadFile
        # Done to simulate an UploadFile object
        # Which is needed for the validate_image function
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

    Returns:
    - torch.Tensor: The transformed image tensor.
    """
    # Load the image from bytes
    image = Image.open(io.BytesIO(image)).convert("RGB")  # Ensure 3-channel RGB
    # Preprocess the image (e.g., cropping to square)
    square_image = normalize.crop_to_square(image)
    # Apply the transformations
    tensor_image = img_transform(square_image)
    # Add a batch dimension
    tensor_image = tensor_image.unsqueeze(0)  # Shape: [1, C, H, W]
    return tensor_image


async def uploadfile_to_bytes(file: UploadFile) -> bytes:
    """
    Converts an UploadFile object to bytes.

    Args:
    - file (UploadFile): The file to convert.

    Returns:
    - bytes: The file contents.
    """
    return file.file.read()