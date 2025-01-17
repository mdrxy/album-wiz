"""
Responsible for orchestrating the metadata collection process by delegating the metadata collection 
to the respective collectors.
"""

import logging
from app.collectors.spotify import SpotifyCollector
from app.collectors.discogs import DiscogsCollector
from app.collectors.musicbrainz import MusicBrainzCollector


class MetadataOrchestrator:
    """
    Parent class for the MetadataOrchestrator.
    """

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.collectors = [
            SpotifyCollector("spotify"),
            DiscogsCollector("discogs"),
            MusicBrainzCollector("musicbrainz"),
        ]

    async def collect_metadata(self, source: str, query: str) -> dict:
        """
        Collect metadata for a given album or artist query using a specific collector.

        Parameters:
        - source (str): The name of the collector to use.
        - query (str): The query to search for, in the format: "{artist} - {album}".

        Returns:
        - dict: A dictionary containing the metadata from the specified collector.

        Raises:
        - ConnectionError: If there is an error connecting to the collector API.
        - TimeoutError: If there is a timeout connecting to the collector API.
        - ValueError: If the collector is not found.

        Example:
        - collect_metadata("spotify", "The Beatles - Abbey Road")
        """
        metadata = {}
        collector = next((c for c in self.collectors if c.get_name() == source), None)
        if collector is None:
            self.logger.error("Collector %s not found", source)
            return {"error": f"Collector {source} not found"}

        try:
            self.logger.info(
                "Collecting metadata using %s", collector.__class__.__name__
            )
            source_metadata = await collector.fetch_metadata(query)
            self.logger.debug(
                "Metadata from %s: %s", collector.__class__.__name__, source_metadata
            )
            if source_metadata and "error" not in source_metadata:
                metadata[collector.get_name()] = source_metadata
                self.logger.info(
                    "Successfully collected metadata from %s",
                    collector.__class__.__name__,
                )
            else:
                error = source_metadata.get("error", "Unknown error occurred")
                self.logger.warning(
                    "Error in metadata from %s: %s",
                    collector.__class__.__name__,
                    error,
                )
                metadata["error"] = error
        except (ConnectionError, TimeoutError, ValueError) as e:
            error_message = str(e)
            metadata["error"] = error_message
            self.logger.error(
                "Failed to collect metadata from %s: %s",
                collector.__class__.__name__,
                error_message,
            )

        return metadata
