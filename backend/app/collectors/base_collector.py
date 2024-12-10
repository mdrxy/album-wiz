"""
This module defines the abstract base class for metadata collectors.
"""
from abc import ABC, abstractmethod


class MetadataCollector(ABC):
    """
    Abstract base class for metadata collectors.

    A metadata collector retrieves some metadata for a given album or artist query, depending on the
    implementation. The metadata is returned as a dictionary.
    """
    @abstractmethod
    async def fetch_metadata(self, query: str) -> dict:
        """
        Fetch metadata for a given record.

        Args:
        - query (str): The query to search for. This should probably be in the format:
            "{artist} - {album}".
        """
