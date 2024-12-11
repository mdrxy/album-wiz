"""
This module contains the MetadataOrchestrator class that is responsible for
orchestrating the metadata collection process by delegating the metadata
collection to the respective collectors.
"""

import logging
from app.collectors.spotify import SpotifyCollector
from app.collectors.discogs import DiscogsCollector
from app.collectors.musicbrainz import MusicBrainzCollector


class MetadataOrchestrator:
    """
    Orchestrates the metadata collection process by delegating the metadata
    collection to the respective collectors.
    """

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("MetadataOrchestrator initialized")

        self.collectors = [
            SpotifyCollector("spotify"),
            DiscogsCollector("discogs"),
            MusicBrainzCollector("musicbrainz"),
        ]

    async def collect_metadata(self, query: str) -> dict:
        """
        Collect metadata for a given album or artist query using all available
        collectors.

        Args:
        - query (str): The query to search for. This should probably be in the
            format: "{artist} - {album}".

        Returns:
        - dict: A dictionary containing the metadata from all available
            collectors. Each key is the name of the collector, and the value
            is the metadata returned by that collector.
        """
        metadata = {}
        for collector in self.collectors:
            try:
                self.logger.info(
                    "Collecting metadata using %s", collector.__class__.__name__
                )

                data = {f"{collector.get_name()}": {}}
                source_metadata = await collector.fetch_metadata(query)
                if "error" not in source_metadata:
                    data[f"{collector.get_name()}"].update(source_metadata)
                    self.logger.info(
                        "Successfully collected metadata from %s",
                        collector.__class__.__name__,
                    )
                    metadata.update(data)
                else:
                    self.logger.warning(
                        "Error in metadata from %s: %s",
                        collector.__class__.__name__,
                        source_metadata["error"],
                    )
            except (ConnectionError, TimeoutError, ValueError) as e:
                error_message = str(e)
                metadata[f"error_{collector.__class__.__name__}"] = error_message
                self.logger.error(
                    "Failed to collect metadata from %s: %s",
                    collector.__class__.__name__,
                    error_message,
                )
        return metadata
