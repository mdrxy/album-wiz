"""
This module defines a SpotifyCollector class that fetches metadata from Spotify's API.
"""

import logging
import os
import spotipy  # https://github.com/spotipy-dev/spotipy?tab=readme-ov-file
from spotipy.oauth2 import SpotifyClientCredentials
from app.collectors.base_collector import MetadataCollector
from dotenv import load_dotenv


load_dotenv()
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


class SpotifyCollector(MetadataCollector):
    """
    Fetch metadata from Spotify's API.

    https://developer.spotify.com/documentation/web-api
    """

    def __init__(self):
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
        Fetch artist details including genres, images, and popularity score.
        """
        self.logger.info("Fetching details for artist: %s", artist_name)
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
            "genres": artist_data["genres"],
            "image": artist_data["images"][0]["url"] if artist_data["images"] else None,
            "popularity": artist_data["popularity"],
            # "related_artists": [],  # Related artists data is no longer available
        }

        return artist_details

    def fetch_album_details(self, artist_name: str, album_name: str) -> dict:
        """
        Fetch album details including image, tracks, genres, and popularity.
        """
        self.logger.info(
            "Fetching album: '%s' by artist: '%s'", album_name, artist_name
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
                "explicit": track["explicit"],
            }
            for track in tracks_data.get("items", [])
        ]
        self.logger.info("Fetched %d tracks for album id: %s", len(tracks), album_id)

        album_details = {
            # "album_type": album_data["album_type"], -- found incorrect data
            "total_tracks": album_data["total_tracks"],
            # "available_markets": album_data["available_markets"], -- too many to deal with
            "spotify_url": album_data["external_urls"]["spotify"],
            # "href": album_data["href"], -- this is the API url
            "id": album_data["id"],
            "image": album_data["images"][0]["url"] if album_data["images"] else None,
            "name": album_data["name"],
            "release_date": album_data["release_date"],
            "release_date_precision": album_data["release_date_precision"],
            "artists": [artist["name"] for artist in album_data["artists"]],
            "tracks": tracks,
        }

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

        # if album_details.get("artists") and artist_name not in album_details["artists"]:
        #     self.logger.warning(
        #         "Artist name mismatch. Expected: %s, Found: %s",
        #         artist_name,
        #         album_details["artists"],
        #     )
        # else:
        #     # Remove artist name from album artists list since it's redundant
        #     # We only want this field to contain other artists on the album
        #     album_details["artists"].remove(artist_name)

        metadata = {
            "artist": artist_details,
            "album": album_details,
        }

        return metadata
