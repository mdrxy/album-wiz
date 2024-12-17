"""
Abstract base class for metadata collectors.
"""

import logging
from abc import ABC, abstractmethod


class MetadataCollector(ABC):
    """
    Abstract base class for metadata collectors.

    A metadata collector retrieves metadata for a given album or artist query.
    The metadata is returned as a dictionary.
    """

    def __init__(self, name: str):
        self.name = name

        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing %s", self.__class__.__name__)

    def get_name(self) -> str:
        """
        Get the name or identifier of the metadata collector.

        Returns:
        - str: A string that identifies this metadata collector
        """
        return self.name

    @abstractmethod
    async def fetch_artist_details(self, artist_name: str) -> dict:
        """
        Fetch artist details. To be implemented by subclasses.
        """

    @abstractmethod
    async def fetch_album_details(self, artist_name: str, album_name: str) -> dict:
        """
        Fetch album details. To be implemented by subclasses.
        """

    async def fetch_metadata(self, query: str) -> dict:
        """
        Fetch metadata for a given record.

        Parameters:
        - query (str): The query to search for. This should probably be in the format:
            "{artist} - {album}".

        Returns:
        - dict: A dictionary containing the metadata for the given query.

        The dictionary should contain the following keys:
        - "artist": The name of the artist
        - "album": The name of the album

        If a value is not available, it should be set to None.

        Subkeys for artist metadata:
        - "name": The name of the artist
        - "namevariations": A list of name variations for the artist
            - Example: ["The Beatles", "Beatles"]
        - "genres": A list of genres associated with the artist
            - Returns the top 5
            - Example: ["pop", "rock"]
        - "image": URL to an image of the artist
            - Should be the highest quality image available
        - "url": URL to the artist's page on the source website
        - "popularity": A popularity score for the artist
            - Should be a number between 0 and 100
        - "profile": A brief description of the artist (HTML)

        Subkeys for album metadata:
        - "name": The name of the album
        - "genres": A list of genres associated with the album
            - Returns the top 5
            - Example: ["pop", "rock"]
        - "image": URL to an image of the album
            - Should be the highest quality image available
        - "release_date": The release date of the album
            - Should be in the format: "YYYY-MM"
        - "total_tracks": The total number of tracks on the album
        - "tracks": A list of tracks
            - Each track should be a dictionary with the following keys:
                - "name": The name of the track
                - "duration": The duration of the track in seconds
                - "explicit": True if the track is explicit, False otherwise
                    - None if the information is not available
        - "url": URL to the album's page on the source website

        TODO: some albums have multiple artists, how should we handle this?

        Examples:
        - fetch_metadata("The Beatles - Abbey Road")
        """
        self.logger.info("Fetching metadata for query: '%s'", query)

        # Parse the query
        try:
            artist_name, album_name = query.split(" - ", 1)
            artist_name = artist_name.strip()
            album_name = album_name.strip()
            self.logger.debug(
                "Parsed query into artist: '%s', album: '%s'", artist_name, album_name
            )
        except ValueError:
            error_message = (
                "Invalid query format. Expected format: '{artist name} - {album name}'"
            )
            self.logger.error("%s Query: '%s'", error_message, query)
            return {"error": error_message}

        # Fetch artist details
        artist_details = await self.fetch_artist_details(artist_name)
        if "error" in artist_details:
            self.logger.error(
                "Error fetching artist details: %s", artist_details["error"]
            )
            return {"error": artist_details["error"]}

        # Fetch album details
        album_details = await self.fetch_album_details(artist_name, album_name)
        if "error" in album_details:
            self.logger.error(
                "Error fetching album details: %s", album_details["error"]
            )
            return {"error": album_details["error"]}

        # Compile metadata
        metadata = {
            "artist": artist_details,
            "album": album_details,
        }

        self.logger.info("Successfully fetched metadata for query: '%s'", query)
        return metadata
