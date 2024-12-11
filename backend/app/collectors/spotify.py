"""
This module defines a SpotifyCollector class that fetches metadata from Spotify's API.
"""

import logging
import os
import spotipy  # https://github.com/spotipy-dev/spotipy?tab=readme-ov-file
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
from app.collectors.base import MetadataCollector


load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


class SpotifyCollector(MetadataCollector):
    """
    Fetch metadata from Spotify's API.

    https://developer.spotify.com/documentation/web-api
    """

    def __init__(self, name: str):
        super().__init__(name)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing SpotifyCollector")

        self.client = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=CLIENT_ID, client_secret=CLIENT_SECRET
            )
        )
        self.logger.info("Spotify client initialized")

    def fetch_artist_details(self, artist_name: str) -> dict:
        """
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
        """
        self.logger.info("Fetching Spotify details for artist: %s", artist_name)
        results = self.client.search(
            q=f'artist:"{artist_name}"', type="artist", limit=1
        )
        artists = results.get("artists", {}).get("items", [])

        if not artists:
            self.logger.warning("No artist found for name: %s", artist_name)
            return {}

        artist_data = artists[0]

        artist_details = {
            "name": artist_data["name"],
            "namevariations": None,  # Spotify does not provide name variations
            "genres": artist_data["genres"] if "genres" in artist_data else None,
            "image": artist_data["images"][0]["url"] if artist_data["images"] else None,
            "url": artist_data["external_urls"]["spotify"],
            "popularity": (
                artist_data["popularity"] if "popularity" in artist_data else None
            ),
            "profile": None,  # Spotify does not provide artist profile
        }

        return artist_details

    def fetch_album_details(self, artist_name: str, album_name: str) -> dict:
        """
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
        """
        self.logger.info(
            "Fetching Spotify album: '%s' by artist: '%s'", album_name, artist_name
        )
        results = self.client.search(
            q=f'album:"{album_name}" artist:"{artist_name}"', type="album", limit=1
        )
        albums = results.get("albums", {}).get("items", [])

        if not albums:
            self.logger.warning(
                "No album found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        album_data = albums[0]
        album_id = album_data["id"]

        # Fetch album tracks
        self.logger.info("Fetching tracks for album id: %s", album_id)
        tracks_data = self.client.album_tracks(album_id)
        tracks = [
            {
                "name": track["name"],
                "duration_seconds": track["duration_ms"] / 1000,
                "explicit": track["explicit"] if "explicit" in track else None,
            }
            for track in tracks_data.get("items", [])
        ]
        self.logger.info("Fetched %d tracks for album id: %s", len(tracks), album_id)

        album_details = {
            "name": album_data["name"],
            "genres": None,  # Spotify does not provide genres
            "image": album_data["images"][0]["url"] if album_data["images"] else None,
            "total_tracks": album_data["total_tracks"],
            "tracks": tracks,
            "url": (
                album_data["external_urls"]["spotify"]
                if "spotify" in album_data["external_urls"]
                else None
            ),
            "popularity": None,  # Spotify does not provide popularity for albums anymore
        }

        # Releast date should be in the format: "YYYY-MM"
        release_date = album_data["release_date"]
        release_date_precision = album_data["release_date_precision"]
        # Standardize release date format to "YYYY-MM"
        if release_date_precision == "day":
            release_date = release_date[:7]  # Extract "YYYY-MM" from "YYYY-MM-DD"
        elif release_date_precision == "month":
            release_date = release_date[:7]  # Already "YYYY-MM"
        elif release_date_precision == "year":
            release_date = f"{release_date}-01"  # Append "-01" for January
        album_details["release_date"] = release_date

        self.logger.info(
            "Fetched album details for '%s' by '%s'", album_name, artist_name
        )
        return album_details

    async def fetch_metadata(self, query: str) -> dict:
        """
        Fetch both artist and album metadata based on the query '{artist name} - {album name}'.
        """
        self.logger.info("Fetching metadata for query: %s", query)

        # Extract artist and album from the query
        try:
            artist_name, album_name = query.split(" - ", 1)
        except ValueError:
            self.logger.error(
                "Query format is invalid. Expected format: '{artist name} - {album name}'"
            )
            return {}

        artist_details = self.fetch_artist_details(artist_name)
        album_details = self.fetch_album_details(artist_name, album_name)

        metadata = {
            "artist": artist_details,
            "album": album_details,
        }
        self.logger.debug("Spotify metadata fetched: %s", metadata)
        return metadata
