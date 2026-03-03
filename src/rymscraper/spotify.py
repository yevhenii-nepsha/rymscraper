"""Spotify integration for syncing RYM albums to playlists."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import spotipy
from spotipy.oauth2 import SpotifyOAuth

if TYPE_CHECKING:
    from rymscraper.models import Album

logger = logging.getLogger(__name__)

SCOPES = "playlist-modify-public playlist-modify-private playlist-read-private"
CACHE_PATH = ".spotify_cache"


def get_spotify_client() -> spotipy.Spotify:
    """Create an authenticated Spotify client.

    Uses SpotifyOAuth with environment variables
    SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and
    SPOTIPY_REDIRECT_URI.

    Returns:
        Authenticated spotipy.Spotify client.
    """
    auth_manager = SpotifyOAuth(
        scope=SCOPES,
        cache_path=CACHE_PATH,
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def find_album(
    sp: spotipy.Spotify,
    album: Album,
) -> str | None:
    """Search Spotify for an album.

    Args:
        sp: Authenticated Spotify client.
        album: Album to search for.

    Returns:
        Spotify album ID if found, None otherwise.
    """
    query = f"album:{album.title} artist:{album.artist}"
    results = sp.search(q=query, type="album", limit=1)
    items = results["albums"]["items"]
    if items:
        return items[0]["id"]  # type: ignore[no-any-return]
    return None


def get_or_create_playlist(
    sp: spotipy.Spotify,
    name: str,
    description: str,
) -> str:
    """Find an existing playlist or create a new one.

    Args:
        sp: Authenticated Spotify client.
        name: Playlist name to find or create.
        description: Playlist description.

    Returns:
        Spotify playlist ID.
    """
    user_id: str = sp.current_user()["id"]

    playlists = sp.current_user_playlists(limit=50)
    while playlists:
        for item in playlists["items"]:
            if item["name"] == name:
                playlist_id: str = item["id"]
                sp.playlist_change_details(
                    playlist_id,
                    description=description,
                )
                return playlist_id
        if playlists["next"]:
            playlists = sp.next(playlists)
        else:
            break

    result = sp.user_playlist_create(
        user_id,
        name,
        description=description,
    )
    return result["id"]  # type: ignore[no-any-return]


def add_album_tracks(
    sp: spotipy.Spotify,
    playlist_id: str,
    album_id: str,
) -> int:
    """Add all tracks from an album to a playlist.

    Args:
        sp: Authenticated Spotify client.
        playlist_id: Spotify playlist ID.
        album_id: Spotify album ID.

    Returns:
        Number of tracks added.
    """
    results = sp.album_tracks(album_id)
    uris: list[str] = [t["uri"] for t in results["items"]]

    if not uris:
        return 0

    for i in range(0, len(uris), 100):
        batch = uris[i : i + 100]
        sp.playlist_add_items(playlist_id, batch)

    return len(uris)


def sync_albums_to_spotify(
    albums: list[Album],
    playlist_name: str,
    rym_url: str,
) -> list[Album]:
    """Sync a list of albums to a Spotify playlist.

    Args:
        albums: Albums to sync.
        playlist_name: Name for the Spotify playlist.
        rym_url: Source RYM URL for the description.

    Returns:
        List of albums not found on Spotify.
    """
    sp = get_spotify_client()
    description = f"Imported from RYM: {rym_url}"
    playlist_id = get_or_create_playlist(sp, playlist_name, description)

    not_found: list[Album] = []
    added = 0

    for album in albums:
        album_id = find_album(sp, album)
        if album_id:
            add_album_tracks(sp, playlist_id, album_id)
            added += 1
            logger.info("Added: %s", album)
        else:
            not_found.append(album)
            logger.warning("Not found: %s", album)

    logger.info(
        "Spotify sync: %d/%d albums added to '%s'",
        added,
        len(albums),
        playlist_name,
    )

    return not_found
