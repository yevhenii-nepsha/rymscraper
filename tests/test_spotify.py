"""Tests for Spotify integration."""

from unittest.mock import MagicMock, patch

from rymscraper.models import Album
from rymscraper.spotify import (
    add_album_tracks,
    find_album,
    get_or_create_playlist,
    get_spotify_client,
    sync_albums_to_spotify,
)


class TestGetSpotifyClient:
    @patch("rymscraper.spotify.SpotifyOAuth")
    @patch("rymscraper.spotify.spotipy.Spotify")
    def test_creates_client_with_oauth(
        self,
        mock_spotify_cls: MagicMock,
        mock_oauth_cls: MagicMock,
    ) -> None:
        """Client uses correct scope, cache, browser."""
        mock_auth = MagicMock()
        mock_oauth_cls.return_value = mock_auth

        get_spotify_client()

        mock_oauth_cls.assert_called_once_with(
            scope=(
                "playlist-modify-public"
                " playlist-modify-private"
                " playlist-read-private"
            ),
            cache_path=".spotify_cache",
            open_browser=True,
        )
        mock_spotify_cls.assert_called_once_with(
            auth_manager=mock_auth,
        )

    @patch("rymscraper.spotify.SpotifyOAuth")
    @patch("rymscraper.spotify.spotipy.Spotify")
    @patch("dotenv.load_dotenv")
    def test_loads_dotenv(
        self,
        mock_load_dotenv: MagicMock,
        mock_spotify_cls: MagicMock,
        mock_oauth_cls: MagicMock,
    ) -> None:
        """Loads .env file before creating client."""
        get_spotify_client()
        mock_load_dotenv.assert_called_once()


class TestFindAlbum:
    def test_album_found(self) -> None:
        """Returns album ID when search has results."""
        sp = MagicMock()
        sp.search.return_value = {
            "albums": {
                "items": [{"id": "abc123"}],
            },
        }
        album = Album("Radiohead", "OK Computer", "1997")

        result = find_album(sp, album)

        assert result == "abc123"
        sp.search.assert_called_once_with(
            q="album:OK Computer artist:Radiohead",
            type="album",
            limit=1,
        )

    def test_album_not_found(self) -> None:
        """Returns None when search has no results."""
        sp = MagicMock()
        sp.search.return_value = {
            "albums": {"items": []},
        }
        album = Album("Unknown", "Nonexistent", "2000")

        result = find_album(sp, album)

        assert result is None


class TestGetOrCreatePlaylist:
    def test_finds_existing_playlist(self) -> None:
        """Returns existing playlist ID and updates desc."""
        sp = MagicMock()
        sp.current_user.return_value = {"id": "user1"}
        sp.current_user_playlists.return_value = {
            "items": [
                {"id": "pl1", "name": "My List"},
                {"id": "pl2", "name": "Other"},
            ],
            "next": None,
        }

        result = get_or_create_playlist(sp, "My List", "desc")

        assert result == "pl1"
        sp.playlist_change_details.assert_called_once_with(
            "pl1", description="desc"
        )
        sp.user_playlist_create.assert_not_called()

    def test_creates_new_playlist(self) -> None:
        """Creates playlist when not found."""
        sp = MagicMock()
        sp.current_user.return_value = {"id": "user1"}
        sp.current_user_playlists.return_value = {
            "items": [
                {"id": "pl2", "name": "Other"},
            ],
            "next": None,
        }
        sp.user_playlist_create.return_value = {
            "id": "new_pl",
        }

        result = get_or_create_playlist(sp, "My List", "desc")

        assert result == "new_pl"
        sp.user_playlist_create.assert_called_once_with(
            "user1", "My List", description="desc"
        )

    def test_paginates_through_playlists(self) -> None:
        """Finds playlist on second page."""
        sp = MagicMock()
        sp.current_user.return_value = {"id": "user1"}

        page1 = {
            "items": [
                {"id": "pl1", "name": "Other"},
            ],
            "next": "https://api.spotify.com/page2",
        }
        page2 = {
            "items": [
                {"id": "pl2", "name": "Target"},
            ],
            "next": None,
        }
        sp.current_user_playlists.return_value = page1
        sp.next.return_value = page2

        result = get_or_create_playlist(sp, "Target", "desc")

        assert result == "pl2"
        sp.next.assert_called_once_with(page1)
        sp.playlist_change_details.assert_called_once_with(
            "pl2", description="desc"
        )


class TestAddAlbumTracks:
    def test_adds_tracks(self) -> None:
        """Adds 3 tracks in a single batch."""
        sp = MagicMock()
        sp.album_tracks.return_value = {
            "items": [
                {"uri": "spotify:track:1"},
                {"uri": "spotify:track:2"},
                {"uri": "spotify:track:3"},
            ],
        }

        result = add_album_tracks(sp, "pl1", "alb1")

        assert result == 3
        sp.playlist_add_items.assert_called_once_with(
            "pl1",
            [
                "spotify:track:1",
                "spotify:track:2",
                "spotify:track:3",
            ],
        )

    def test_empty_album(self) -> None:
        """Does not call add when album has no tracks."""
        sp = MagicMock()
        sp.album_tracks.return_value = {"items": []}

        result = add_album_tracks(sp, "pl1", "alb1")

        assert result == 0
        sp.playlist_add_items.assert_not_called()

    def test_pagination_over_100_tracks(self) -> None:
        """Splits 150 tracks into batches of 100+50."""
        sp = MagicMock()
        tracks = [{"uri": f"spotify:track:{i}"} for i in range(150)]
        sp.album_tracks.return_value = {"items": tracks}

        result = add_album_tracks(sp, "pl1", "alb1")

        assert result == 150
        assert sp.playlist_add_items.call_count == 2
        first_call = sp.playlist_add_items.call_args_list[0]
        second_call = sp.playlist_add_items.call_args_list[1]
        assert len(first_call[0][1]) == 100
        assert len(second_call[0][1]) == 50


class TestSyncAlbumsToSpotify:
    @patch("rymscraper.spotify.get_spotify_client")
    def test_mixed_results(self, mock_get_client: MagicMock) -> None:
        """Returns not-found albums; adds found ones."""
        sp = MagicMock()
        mock_get_client.return_value = sp
        sp.current_user.return_value = {"id": "u1"}
        sp.current_user_playlists.return_value = {
            "items": [],
            "next": None,
        }
        sp.user_playlist_create.return_value = {
            "id": "pl1",
        }

        def search_side_effect(
            q: str,
            type: str,  # noqa: A002
            limit: int,
        ) -> dict[str, object]:
            if "OK Computer" in q:
                return {
                    "albums": {
                        "items": [{"id": "alb1"}],
                    },
                }
            return {"albums": {"items": []}}

        sp.search.side_effect = search_side_effect
        sp.album_tracks.return_value = {
            "items": [{"uri": "spotify:track:1"}],
        }

        albums = [
            Album("Radiohead", "OK Computer", "1997"),
            Album("Unknown", "Nope", "2000"),
        ]

        result = sync_albums_to_spotify(
            albums, "Test", "https://rym.com/list/x"
        )

        assert len(result) == 1
        assert result[0].artist == "Unknown"

    @patch("rymscraper.spotify.get_spotify_client")
    def test_all_found(self, mock_get_client: MagicMock) -> None:
        """Returns empty list when all albums found."""
        sp = MagicMock()
        mock_get_client.return_value = sp
        sp.current_user.return_value = {"id": "u1"}
        sp.current_user_playlists.return_value = {
            "items": [],
            "next": None,
        }
        sp.user_playlist_create.return_value = {
            "id": "pl1",
        }
        sp.search.return_value = {
            "albums": {
                "items": [{"id": "alb1"}],
            },
        }
        sp.album_tracks.return_value = {
            "items": [{"uri": "spotify:track:1"}],
        }

        albums = [
            Album("Radiohead", "OK Computer", "1997"),
        ]

        result = sync_albums_to_spotify(
            albums, "Test", "https://rym.com/list/x"
        )

        assert result == []

    @patch("rymscraper.spotify.get_spotify_client")
    def test_none_found(self, mock_get_client: MagicMock) -> None:
        """Returns all albums when none found."""
        sp = MagicMock()
        mock_get_client.return_value = sp
        sp.current_user.return_value = {"id": "u1"}
        sp.current_user_playlists.return_value = {
            "items": [],
            "next": None,
        }
        sp.user_playlist_create.return_value = {
            "id": "pl1",
        }
        sp.search.return_value = {
            "albums": {"items": []},
        }

        albums = [
            Album("Unknown", "Nope", "2000"),
        ]

        result = sync_albums_to_spotify(
            albums, "Test", "https://rym.com/list/x"
        )

        assert result == albums

    @patch("rymscraper.spotify.get_spotify_client")
    def test_playlist_description_has_rym_url(
        self, mock_get_client: MagicMock
    ) -> None:
        """Playlist description includes the RYM URL."""
        sp = MagicMock()
        mock_get_client.return_value = sp
        sp.current_user.return_value = {"id": "u1"}
        sp.current_user_playlists.return_value = {
            "items": [],
            "next": None,
        }
        sp.user_playlist_create.return_value = {
            "id": "pl1",
        }
        sp.search.return_value = {
            "albums": {"items": []},
        }

        url = "https://rateyourmusic.com/list/user/my-list"
        sync_albums_to_spotify([Album("A", "B", "2000")], "Test", url)

        create_call = sp.user_playlist_create.call_args
        desc = create_call[1]["description"]
        assert url in desc
