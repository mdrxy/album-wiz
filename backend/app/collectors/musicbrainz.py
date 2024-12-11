"""
This module contains the MusicBrainzCollector class that fetches metadata from the MusicBrainz API.
"""

import logging
import os
import re
from dotenv import load_dotenv
import musicbrainzngs  # https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/
from app.collectors.base import MetadataCollector


load_dotenv()
USER_AGENT = os.getenv("MUSICBRAINZ_USER_AGENT_NAME")
VERSION = os.getenv("MUSICBRAINZ_USER_AGENT_VERSION")
CONTACT = os.getenv("MUSICBRAINZ_USER_AGENT_CONTACT")

# Initialize the MusicBrainz client
musicbrainzngs.set_useragent(USER_AGENT, VERSION, CONTACT)


# def convert_text_to_html(text):
#     """
#     Convert text to HTML.
#     """
#     # Wrap sections like "Band members:" in <strong> tags
#     text = re.sub(
#         r"^(Band members:|Current live members:|Former members:|Previous names:)",
#         r"<strong>\1</strong>",
#         text,
#         flags=re.MULTILINE,
#     )

#     # Standardize hyphens
#     text = text.replace("–", "-")

#     return text


class MusicBrainzCollector(MetadataCollector):
    """
    Fetch metadata from MusicBrainz' API using the musicbrainzngs library.

    NOTE: MusicBrainz has rate limits for unauthenticated and authenticated requests.
    Refer to https://musicbrainz.org/doc/XML_Web_Service/Rate_Limiting
    """

    def __init__(self, name: str):
        super().__init__(name)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("MusicBrainzCollector initialized")

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
        self.logger.info("Fetching MusicBrainz details for artist: %s", artist_name)

        try:
            result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
            artist_data = result["artist-list"][0] if result["artist-list"] else None
        except musicbrainzngs.WebServiceError as e:
            error_message = f"An error occurred: {str(e)}"
            self.logger.error(error_message)
            return {"error": error_message}

        if not artist_data:
            self.logger.warning("No artist found for name: %s", artist_name)
            return {}

        artist_details = {
            "name": artist_data["name"],
            "genres": artist_data.get("tag-list", []),
            "image": None,  # MusicBrainz does not directly provide images
            "url": f"https://musicbrainz.org/artist/{artist_data['id']}",
            # "profile": convert_text_to_html(artist_data.get("disambiguation", "")),
            "profile": artist_data.get("disambiguation", ""),
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
            "Fetching MusicBrainz album: '%s' by artist: '%s'", album_name, artist_name
        )
        try:
            result = musicbrainzngs.search_releases(
                artist=artist_name, release=album_name, limit=1
            )
            release_data = result["release-list"][0] if result["release-list"] else None
        except musicbrainzngs.WebServiceError as e:
            error_message = f"An error occurred: {str(e)}"
            self.logger.error(error_message)
            return {"error": error_message}

        if not release_data:
            self.logger.warning(
                "No album found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        album_details = {
            "name": release_data["title"],
            "genres": release_data.get("tag-list", []),
            "image": None,  # MusicBrainz does not directly provide images
            "release_date": release_data.get("date", None),
            "total_tracks": None,  # Requires additional query for tracklist
            "tracks": None,  # Requires additional query for tracklist
            "url": f"https://musicbrainz.org/release/{release_data['id']}",
        }

        # Fetch detailed release information to get tracklist
        try:
            release_info = musicbrainzngs.get_release_by_id(
                release_data["id"], includes=["recordings"]
            )
            track_list = release_info["release"]["medium-list"][0]["track-list"]
            tracks = [
                {
                    "name": track["recording"]["title"],
                    "duration": (
                        int(track["recording"]["length"]) // 1000
                        if "length" in track["recording"]
                        else None
                    ),
                    "explicit": None,  # MusicBrainz does not provide explicit info
                }
                for track in track_list
            ]
            album_details["total_tracks"] = len(tracks)
            album_details["tracks"] = tracks
        except musicbrainzngs.WebServiceError as e:
            self.logger.error("Error fetching tracklist: %s", str(e))

        return album_details

    async def fetch_metadata(self, query: str) -> dict:
        """
        Retrieve metadata for a given album or artist query from the MusicBrainz API.
        """
        self.logger.debug("Fetching MusicBrainz metadata for query: %s", query)

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
        self.logger.debug("MusicBrainz metadata fetched: %s", metadata)
        return metadata
