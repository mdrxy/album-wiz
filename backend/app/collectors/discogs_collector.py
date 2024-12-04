"""
This module contains the DiscogsCollector class that fetches metadata from the Discogs API.
"""

import logging
import discogs_client
from app.collectors.base_collector import MetadataCollector


class DiscogsCollector(MetadataCollector):
    """
    Fetch metadata from Discogs' API using the discogs_client library.
    """

    USER_AGENT = "album-wiz/1.0 +https://github.com/mdrxy/album-wiz"
    TOKEN = ""

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing DiscogsCollector")

        self.client = discogs_client.Client(self.USER_AGENT, user_token=self.TOKEN)
        self.logger.info("Discogs client initialized")

    async def fetch_metadata(self, query: str) -> dict:
        """
        Retrieve metadata for a given album or artist query from the Discogs API.
        """
        self.logger.debug("Fetching Discogs metadata for query: %s", query)
        try:
            release = self.client.release(query)
            if not release:
                self.logger.warning("No results found for query: %s", query)
                return {"error": "No results found"}
            metadata = {
                "title": release.title,
                "artist": release.artists[0].name,
                "release_date": release.year,
                "genres": release.genres,
            }
            self.logger.debug("Discogs metadata fetched: %s", metadata)
            return metadata
        except discogs_client.exceptions.HTTPError as e:
            error_message = f"An error occurred: {str(e)}"
            self.logger.error(error_message)
            return {"error": error_message}
