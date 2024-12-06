"""
This module contains the DiscogsCollector class that fetches metadata from the Discogs API.
"""

import logging
import os
import discogs_client  # https://github.com/joalla/discogs_client
from app.collectors.base_collector import MetadataCollector
from dotenv import load_dotenv


load_dotenv()
USER_AGENT = os.getenv("DISCOGS_USER_AGENT")
TOKEN = os.getenv("DISCOGS_TOKEN")


class DiscogsCollector(MetadataCollector):
    """
    Fetch metadata from Discogs' API using the discogs_client library.

    https://www.discogs.com/developers/
    """

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing DiscogsCollector")

        self.client = discogs_client.Client(USER_AGENT, user_token=TOKEN)
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
