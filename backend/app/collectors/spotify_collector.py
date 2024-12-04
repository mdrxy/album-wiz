"""
This module defines a SpotifyCollector class that fetches metadata from Spotify's API.
"""

import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.collectors.base_collector import MetadataCollector


class SpotifyCollector(MetadataCollector):
    """
    Fetch metadata from Spotify's API.
    """

    CLIENT_ID = ""
    CLIENT_SECRET = ""

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing SpotifyCollector")

        self.client = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=self.CLIENT_ID, client_secret=self.CLIENT_SECRET
            )
        )
        self.logger.info("Spotify client initialized")

    async def fetch_metadata(self, query: str) -> dict:
        self.logger.info("Fetching Spotify metadata for query: %s", query)

        s_results = self.client.search(q=f"{query}", limit=20)
        for i, t in enumerate(s_results["tracks"]["items"]):
            print(" ", i, t["name"])

        result = {"hello": "world"}
        self.logger.info("Spotify metadata fetched: %s", result)
        return result
