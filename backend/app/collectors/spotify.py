"""
Fetch metadata from Spotify's API.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
import spotipy  # https://github.com/spotipy-dev/spotipy?tab=readme-ov-file
from spotipy.oauth2 import SpotifyClientCredentials
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
        self.logger.info("Initializing SpotifyCollector")

        self.client = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=CLIENT_ID, client_secret=CLIENT_SECRET
            )
        )
        self.logger.info("Spotify client initialized")
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def fetch_artist_details(self, artist_name: str) -> dict:
        """
        Fetch artist details from Spotify's API.

        Parameters:
        - artist_name (str): The name of the artist to search for.

        Returns:
        - dict: A dictionary containing the artist details:
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

        If a value is not available, it should be set to None.

        Raises:
        - SpotifyException: If there is an error fetching the artist details.
        - CancelledError: If the coroutine is cancelled.
        """
        self.logger.info("Fetching Spotify details for artist: %s", artist_name)

        loop = asyncio.get_event_loop()
        try:
            # Run the blocking Spotipy call in an executor to prevent blocking the event loop
            results = await loop.run_in_executor(
                self.executor,
                lambda: self.client.search(
                    q=f'artist:"{artist_name}"', type="artist", limit=1
                ),
            )
            artists = results.get("artists", {}).get("items", [])
        except spotipy.exceptions.SpotifyException as e:
            self.logger.error("Spotify API error fetching artist details: %s", e)
            return {"error": str(e)}
        except asyncio.CancelledError as e:
            self.logger.error("Error fetching artist details: %s", e)
            return {"error": str(e)}

        if not artists:
            self.logger.warning("No artist found for name: %s", artist_name)
            return {}

        artist_data = artists[0]
        genres = artist_data.get("genres", None)
        if genres:
            genres = genres[:5]  # Top 5 genres

        artist_details = {
            "name": artist_data.get("name"),
            "namevariations": None,  # Spotify does not provide name variations
            "genres": genres if genres else None,
            "image": (
                artist_data["images"][0]["url"] if artist_data.get("images") else None
            ),
            "url": artist_data["external_urls"].get("spotify"),
            "popularity": artist_data.get("popularity"),
            "profile": None,  # Spotify does not provide artist profile text
        }

        return artist_details

    async def fetch_album_details(self, artist_name: str, album_name: str) -> dict:
        """
        Fetch album details fromthe Spotify API.

        Parameters:
        - artist_name (str): The name of the artist who released the album.
        - album_name (str): The name of the album to fetch details for.

        Returns:
        - dict: A dictionary containing the album details:
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

        If a value is not available, it should be set to None.
        """
        self.logger.info(
            "Fetching Spotify album: '%s' by artist: '%s'", album_name, artist_name
        )

        loop = asyncio.get_event_loop()
        try:
            # Run the blocking Spotipy call in an executor
            albums = await loop.run_in_executor(
                self.executor,
                lambda: self.client.search(
                    q=f'album:"{album_name}" artist:"{artist_name}"',
                    type="album",
                    limit=1,
                ),
            )
        except spotipy.exceptions.SpotifyException as e:
            self.logger.error("Spotify API error fetching album details: %s", e)
            return {"error": str(e)}
        except asyncio.CancelledError as e:
            self.logger.error("Error fetching album details: %s", e)
            return {"error": str(e)}

        if not albums or not albums.get("albums", {}).get("items"):
            self.logger.warning(
                "No album found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        album_data = albums["albums"]["items"][0]
        album_id = album_data.get("id")

        if not album_id:
            self.logger.warning(
                "No album ID found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        # Fetch album tracks
        self.logger.info("Fetching tracks for album id: %s", album_id)
        try:
            tracks_data = await loop.run_in_executor(
                self.executor, lambda: self.client.album_tracks(album_id)
            )
            tracks = [
                {
                    "name": track.get("name"),
                    "duration": int(track.get("duration_ms", 0) / 1000),
                    "explicit": track.get("explicit", None),
                }
                for track in tracks_data.get("items", [])
            ]
            self.logger.info(
                "Fetched %d tracks for album id: %s", len(tracks), album_id
            )
        except spotipy.exceptions.SpotifyException as e:
            self.logger.error("Spotify API error fetching tracks: %s", e)
            return {"error": str(e)}
        except asyncio.CancelledError as e:
            self.logger.error("Error fetching tracks: %s", e)
            return {"error": str(e)}

        # Standardize release date
        release_date = album_data.get("release_date")
        release_date_precision = album_data.get("release_date_precision")
        if release_date and release_date_precision:
            if release_date_precision == "day":
                release_date = release_date[:7]  # "YYYY-MM"
            elif release_date_precision == "year":
                release_date = f"{release_date}-01"  # "YYYY-MM"
            # If precision is "month", it's already "YYYY-MM"

        album_details = {
            "name": album_data.get("name"),
            "genres": None,  # Spotify does not provide album genres
            "image": (
                album_data["images"][0]["url"] if album_data.get("images") else None
            ),
            "release_date": release_date,
            "total_tracks": album_data.get("total_tracks"),
            "tracks": tracks,
            "url": album_data["external_urls"].get("spotify"),
        }

        self.logger.info(
            "Fetched album details for '%s' by '%s'", album_name, artist_name
        )
        return album_details
