"""
This module defines the abstract base class for metadata collectors.
"""

from abc import ABC, abstractmethod


class MetadataCollector(ABC):
    """
    Abstract base class for metadata collectors.

    A metadata collector retrieves metadata for a given album or artist query.
    The metadata is returned as a dictionary.
    """

    def __init__(self, name: str):
        """
        Initialize the metadata collector with a name.

        Args:
        - name (str): The name of the metadata collector.
        """
        self.name = name

    def get_name(self) -> str:
        """
        Get the name or identifier of the metadata collector.

        Returns:
        - str: A string that identifies this metadata collector
        """
        return self.name

    @abstractmethod
    async def fetch_metadata(self, query: str) -> dict:
        """
        Fetch metadata for a given record.

        Args:
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
            - Example: ["pop", "rock"]
        - "image": URL to an image of the artist
            - Should be the highest quality image available
        - "url": URL to the artist's page on the source website
        - "popularity": A popularity score for the artist
            - Should be a number between 0 and 100
        - "profile": A brief description of the artist

        Subkeys for album metadata:
        - "name": The name of the album
        - "genres": A list of genres associated with the album
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
        - "popularity": A popularity score for the album
            - Should be a number between 0 and 100

        TODO: some albums have multiple artists, how should we handle this?
        """
