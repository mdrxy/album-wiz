"""
Fetch information from Wikimedia Commons.
"""

import logging
import requests


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Wikimedia Commons API endpoint
API = "https://commons.wikimedia.org/w/api.php"


def fetch_wikimedia_image(commons_url: str) -> str:
    """
    Fetch the primary image URL from a Wikimedia Commons page.

    Parameters:
    - commons_url (str): The URL to the Wikimedia Commons page.

    Returns:
    - str: URL to the image if available, None otherwise.

    Raises:
    - requests.RequestException: If an error occurs while fetching the image.

    Example:
    - Input: "https://commons.wikimedia.org/wiki/File:Example.jpg"
        -> "https://upload.wikimedia.org/wikipedia/commons/0/0c/Example.jpg"
    """
    try:
        # Extract page title from the URL
        page_title = commons_url.split("/")[-1]

        # Make a request to the Wikimedia Commons API to get the file information
        response = requests.get(
            API,
            params={
                "action": "query",
                "titles": page_title,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        # Extract the image URL from the response
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "imageinfo" in page:
                return page["imageinfo"][0]["url"]

        return None
    except requests.RequestException as e:
        print(f"Error fetching image from Wikimedia Commons: {e}")
        return None
