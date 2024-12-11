"""
This module contains the DiscogsCollector class that fetches metadata from the Discogs API.
"""

import logging
import os
import re
import discogs_client  # https://github.com/joalla/discogs_client
from dotenv import load_dotenv
from app.collectors.base import MetadataCollector


load_dotenv()
USER_AGENT = os.getenv("DISCOGS_USER_AGENT")
TOKEN = os.getenv("DISCOGS_TOKEN")


def discogs_to_html(text):
    """
    Convert Discogs-style text to HTML.
    """
    # Convert newlines
    text = text.replace("\r\n", "<br>")

    # Convert [url=...]...[/url] to <a href="...">...</a>
    text = re.sub(r"\[url=([^\]]+)\](.*?)\[/url\]", r'<a href="\1">\2</a>', text)

    # Convert [a=...] to <a href="https://www.discogs.com/artist/...">...</a>
    text = re.sub(
        r"\[a=([^\]]+)\]", r'<a href="https://www.discogs.com/artist/\1">\1</a>', text
    )

    # Convert [r=...] to <a href="https://www.discogs.com/release/...">...</a>
    text = re.sub(
        r"\[r=([^\]]+)\]", r'<a href="https://www.discogs.com/release/\1">\1</a>', text
    )

    # Wrap sections like "Band members:" in <strong> tags
    text = re.sub(
        r"^(Band members:|Current live members:|Former members:|Previous names:)",
        r"<strong>\1</strong>",
        text,
        flags=re.MULTILINE,
    )

    # Standardize hyphens
    text = text.replace("–", "-")

    return text


class DiscogsCollector(MetadataCollector):
    """
    Fetch metadata from Discogs' API using the discogs_client library.

    NOTE: Requests are throttled by the server by source IP to 60 per minute for authenticated
    requests

    Backing off and auto retry when API rate limit is hit is enabled by default and can be disabled
    by:
    ```
    self.client.backoff_enabled = False
    ```

    https://www.discogs.com/developers/
    """

    def __init__(self, name: str):
        super().__init__(name)
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Initializing DiscogsCollector")

        self.client = discogs_client.Client(USER_AGENT, user_token=TOKEN)
        self.logger.info("Discogs client initialized")

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
        self.logger.info("Fetching Discogs details for artist: %s", artist_name)

        try:
            results = self.client.search(artist_name, type="artist")
        except discogs_client.exceptions.HTTPError as e:
            error_message = f"An error occurred: {str(e)}"
            self.logger.error(error_message)
            return {"error": error_message}
        artists = results.page(1)

        if not artists:
            self.logger.warning("No artist found for name: %s", artist_name)
            return {}

        artist = artists[0]
        # TODO: ensure this is an artist?
        artist_details = {
            "name": artist.name,
            "namevariations": (
                artist.name_variations if artist.name_variations else None
            ),
            "genres": None,  # Discogs does not provide genres
            "image": (
                artist.images[0]["uri"] if artist.images else None
            ),  # Primary image
            "url": artist.url,
            "popularity": None,  # Discogs does not provide popularity
            "profile": artist.profile if artist.profile else None,
        }
        # Convert profile to HTML if available
        if artist_details["profile"]:
            artist_details["profile"] = discogs_to_html(artist_details["profile"])

        return artist_details

    def find_release_date(self, releases: list) -> str:
        """
        Find the release date of the earliest release in a list of releases.
        """
        release_dates = []
        for release in releases:
            release_date = release.year
            if release_date != "0" and release_date is not None:
                release_date = str(release_date) + "-01"
                release_dates.append(release_date)
        if release_dates:
            # Delete all `0-01` entries
            release_dates = [date for date in release_dates if date != "0-01"]
            return min(release_dates)
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
        """
        self.logger.info(
            "Fetching Discogs album: '%s' by artist: '%s'", album_name, artist_name
        )
        try:
            results = self.client.search(album_name, type="release", artist=artist_name)
        except discogs_client.exceptions.HTTPError as e:
            error_message = f"An error occurred: {str(e)}"
            self.logger.error(error_message)
            return {"error": error_message}
        releases = results.page(1)

        if not releases:
            self.logger.warning(
                "No album found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        # Filter releases to find the first CD release
        cd_releases = [
            release
            for release in releases
            if any(fmt["name"].lower() == "cd" for fmt in release.formats)
        ]

        if not cd_releases:
            self.logger.warning(
                "No CD release found for '%s' by '%s'", album_name, artist_name
            )
            return {}

        # Sort CD releases by year to find the earliest one
        def get_release_year(release):
            try:
                return int(release.year)
            except (TypeError, ValueError):
                return float("inf")  # Assign infinity if year is invalid or None

        first_cd_release = min(cd_releases, key=get_release_year)

        release = first_cd_release
        album_title = release.title

        # Check if the album title starts with the artist's name followed by a delimiter
        pattern = re.compile(rf"^{re.escape(artist_name)}\s*[-:]\s*(.*)", re.IGNORECASE)
        match = pattern.match(album_title)
        if match:
            self.logger.critical(
                "Found artist name prepended to album name, stripping: %s",
                match.group(1),
            )
            album_title = match.group(1).strip()

        album_details = {
            "name": album_title,
            "genres": release.genres if release.genres else None,
            "image": release.images[0]["uri"] if release.images else None,
            "url": release.url,
        }

        # Get release date in the format "YYYY-MM"
        release_date = str(release.year)
        if release_date != "0" and release_date is not None:
            release_date += "-01"
            album_details["release_date"] = release_date
        else:
            album_details["release_date"] = None

        if not album_details["release_date"]:
            self.logger.warning(
                "Falling back to finding release date from all releases"
            )
            album_details["release_date"] = self.find_release_date(releases)

        # Get total number of tracks
        album_details["total_tracks"] = len(release.tracklist)
        tracks = []
        for track in release.tracklist:
            tracks.append(
                {
                    "name": track.title,
                    "duration": track.duration,
                    "explicit": None,  # Discogs does not provide explicit info
                }
            )
        # Convert duration to seconds
        for track in tracks:
            duration = track["duration"]
            if duration:
                minutes, seconds = duration.split(":")
                duration_seconds = int(minutes) * 60 + int(seconds)
                track["duration"] = duration_seconds
        album_details["tracks"] = tracks

        return album_details

    async def fetch_metadata(self, query: str) -> dict:
        """
        Retrieve metadata for a given album or artist query from the Discogs API.
        """
        self.logger.debug("Fetching Discogs metadata for query: %s", query)

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
        self.logger.debug("Discogs metadata fetched: %s", metadata)
        return metadata
