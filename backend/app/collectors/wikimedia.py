"""
Fetch information from Wikimedia Commons.
"""

import logging
import requests


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.info("Wikimedia collector initialized")


def fetch_wikimedia_image(commons_url: str) -> str:
    """
    Fetch the primary image URL from a Wikimedia Commons page.

    Parameters:
    - commons_url (str): The URL to the Wikimedia Commons page.

    Returns:
    - str: URL to the image if available, None otherwise.
    """
    try:
        # Wikimedia Commons API endpoint
        api_url = "https://commons.wikimedia.org/w/api.php"

        # Extract page title from the URL
        page_title = commons_url.split("/")[-1]

        # Make a request to the Wikimedia Commons API to get the file information
        response = requests.get(
            api_url,
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
