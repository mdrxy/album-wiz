"""
This module contains the MusicBrainzCollector class that fetches metadata from the MusicBrainz API.
"""

import logging
import os
from dotenv import load_dotenv
import musicbrainzngs  # https://python-musicbrainzngs.readthedocs.io/en/v0.7.1/
from app.collectors.base import MetadataCollector
from app.collectors.wikimedia import fetch_wikimedia_image


load_dotenv()
USER_AGENT = os.getenv("MUSICBRAINZ_USER_AGENT_NAME")
VERSION = os.getenv("MUSICBRAINZ_USER_AGENT_VERSION")
CONTACT = os.getenv("MUSICBRAINZ_USER_AGENT_CONTACT")

# Initialize the MusicBrainz client
musicbrainzngs.set_useragent(USER_AGENT, VERSION, CONTACT)


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

    def get_genre_list(self) -> set:
        """
        Retrieve the official list of genres from MusicBrainz.
        Returns:
            A set of genre names in lowercase.
        """
        try:
            with open("/app/app/collectors/genres.txt", "r", encoding="utf-8") as file:
                genres = {line.strip().lower() for line in file if line.strip()}
            return genres
        except FileNotFoundError as exc:
            raise FileNotFoundError("The genres.txt file was not found.") from exc

    def fetch_artist_image(self, artist_data) -> str:
        """
        Fetch the artist's image from Wikimedia Commons via MusicBrainz relationships.

        Parameters:
        - artist_name (str): The name of the artist to fetch the image for.

        Returns:
        - str: URL to the artist's image if available, None otherwise.
        """
        try:
            # Fetch detailed artist information, including URL relationships
            artist_info = musicbrainzngs.get_artist_by_id(
                artist_data["id"], includes=["url-rels"]
            )
            # Find Wikimedia Commons URL
            commons_url = None
            for rel in artist_info["artist"].get("url-relation-list", []):
                self.logger.debug("Found URL: %s", rel["target"])
                if "wikimedia.org" in rel["target"]:
                    self.logger.debug("Found Wikimedia Commons URL: %s", rel["target"])
                    commons_url = rel["target"]
                    break
            if not commons_url:
                return None

            # Fetch image from Wikimedia Commons
            # TODO: this should probably not be here, but instead a new method elsewhere
            image_url = fetch_wikimedia_image(commons_url)
            return image_url

        except musicbrainzngs.WebServiceError as e:
            print(f"Error fetching relationships: {e}")
            return None

    def get_english_aliases(self, artist_data) -> list:
        """
        Extract English aliases from the artist data.
        """
        self.logger.debug(
            "Extracting English aliases from artist data: %s", artist_data
        )
        try:
            english_aliases = [
                alias["alias"]
                for alias in artist_data.get("alias-list", [])
                if alias.get("locale") == "en"
            ]
            self.logger.debug("Extracted English aliases: %s", english_aliases)
            return english_aliases
        except KeyError as e:
            self.logger.error("KeyError while extracting aliases: %s", e, exc_info=True)
            return []

    def fetch_artist_details(self, artist_name: str) -> dict:
        """
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

        try:
            # Get detailed artist information
            artist_info = musicbrainzngs.get_artist_by_id(
                artist_data["id"], includes=["tags", "aliases"]
            )

            # Get genres
            genre_list = self.get_genre_list()
            # Filter tags to include only those that are recognized as genres
            genres = [
                tag["name"]
                for tag in artist_info["artist"].get("tag-list", [])
                if tag["name"].lower() in genre_list
            ]

            # Filter to first (top) 5 genres
            genres = genres[:5]
            if not genres:
                genres = None

            # Get image
            image_url = self.fetch_artist_image(artist_data)

            aliases = self.get_english_aliases(artist_data)
        except musicbrainzngs.WebServiceError as e:
            self.logger.error("Error fetching genres: %s", str(e))

        artist_details = {
            "name": artist_data["name"],
            "namevariations": aliases if aliases else None,
            "genres": genres,
            "image": image_url if image_url else None,
            "url": f"https://musicbrainz.org/artist/{artist_data['id']}",
            "popularity": None,  # NOTE: MusicBrainz does not provide popularity info
            "profile": artist_data.get("disambiguation", None),
        }

        return artist_details

    def fetch_album_cover_art(self, release_data) -> str:
        """
        Fetch the cover art URL for a given album using the Cover Art Archive.

        Args:
        - release_data (dict): The release data from the MusicBrainz API.

        Returns:
        - str: URL to the album's cover art image if available, None otherwise.
        """
        try:
            release_mbid = release_data["id"]

            # Fetch cover art using the release MBID
            cover_art = musicbrainzngs.get_image_list(release_mbid)
            images = cover_art.get("images", [])
            for image in images:
                if "Front" in image.get("types", []) and image.get("approved", False):
                    image_url = image["image"]
                    self.logger.info("Found cover art URL: %s", image_url)
                    return image_url
            return None

        except musicbrainzngs.WebServiceError as e:
            self.logger.error("Error fetching cover art: %s", str(e))
            return None

    def fetch_album_details(self, artist_name: str, album_name: str) -> dict:
        """
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
            "genres": release_data.get("tag-list", None) or None,
            "image": self.fetch_album_cover_art(release_data),
            "total_tracks": None,  # Requires additional query for tracklist
            "tracks": None,  # Requires additional query for tracklist
            "url": f"https://musicbrainz.org/release/{release_data['id']}",
            "popularity": None,  # NOTE: MusicBrainz does not provide popularity info
        }

        # Releast date should be in the format: "YYYY-MM"
        release_date = release_data.get("date", None)
        release_date = release_date[:7]  # Extract "YYYY-MM" from "YYYY-MM-DD"
        album_details["release_date"] = release_date

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
            "album": album_details if album_details else None,
        }
        self.logger.debug("MusicBrainz metadata fetched: %s", metadata)
        return metadata
