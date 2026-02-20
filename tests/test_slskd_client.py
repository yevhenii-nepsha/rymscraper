"""Tests for slskd client wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rymparser.settings import AppSettings
from rymparser.slskd_client import (
    SlskdError,
    _completed_directories,
    create_client,
    search_albums,
)


@pytest.fixture
def settings() -> AppSettings:
    """Settings with test values."""
    return AppSettings(
        slskd_host="http://test:5030",
        slskd_api_key="test-key-1234567890",
        search_timeout=5,
    )


class TestCreateClient:
    def test_missing_api_key(self) -> None:
        """Raises SlskdError when API key is empty."""
        s = AppSettings(slskd_api_key="")
        with pytest.raises(SlskdError, match="API key"):
            create_client(s)

    @patch("rymparser.slskd_client.slskd_api")
    def test_creates_client(
        self,
        mock_api: MagicMock,
        settings: AppSettings,
    ) -> None:
        """Creates SlskdClient with correct params."""
        create_client(settings)
        mock_api.SlskdClient.assert_called_once_with(
            host="http://test:5030",
            api_key="test-key-1234567890",
        )


class TestSearchAlbums:
    @patch("rymparser.slskd_client.slskd_api")
    def test_returns_responses(
        self,
        mock_api: MagicMock,
        settings: AppSettings,
    ) -> None:
        """Returns search responses for a query."""
        mock_client = MagicMock()
        mock_api.SlskdClient.return_value = mock_client
        mock_client.searches.search_text.return_value = {
            "id": "abc-123",
        }
        mock_client.searches.state.return_value = {
            "isComplete": True,
        }
        mock_client.searches.search_responses.return_value = [
            {
                "username": "user1",
                "files": [
                    {
                        "filename": "track.flac",
                        "size": 1000,
                        "extension": "flac",
                    },
                ],
                "hasFreeUploadSlot": True,
                "uploadSpeed": 1000000,
                "queueLength": 0,
                "fileCount": 1,
                "lockedFileCount": 0,
                "lockedFiles": [],
                "token": 1,
            },
        ]

        client = create_client(settings)
        results = search_albums(
            client,
            "Radiohead OK Computer",
            timeout=5,
        )
        assert len(results) == 1
        assert results[0]["username"] == "user1"


class TestCompletedDirectories:
    def test_finds_completed_dirs(self) -> None:
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "Album A",
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": "Completed, Succeeded",
                            },
                            {
                                "filename": "02.flac",
                                "state": "Completed, Succeeded",
                            },
                        ],
                    },
                    {
                        "directory": "Album B",
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": "Completed, Succeeded",
                            },
                            {
                                "filename": "02.flac",
                                "state": "InProgress",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert succeeded == {"Album A"}
        assert len(failed) == 0

    def test_ignores_other_users(self) -> None:
        transfers = [
            {
                "username": "other",
                "directories": [
                    {
                        "directory": "Album C",
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": "Completed, Succeeded",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert succeeded == set()
        assert failed == set()

    def test_empty_dir_is_not_complete(self) -> None:
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "Empty",
                        "files": [],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert succeeded == set()
        assert failed == set()

    def test_normalizes_backslashes(self) -> None:
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": ("Music\\Artist\\Album"),
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": ("Completed, Succeeded"),
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert succeeded == {"Music/Artist/Album"}
        assert len(failed) == 0

    def test_errored_counts_as_complete(self) -> None:
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "Album D",
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": "Completed, Errored",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert len(succeeded) == 0
        assert failed == {"Album D"}

    def test_completed_directories_returns_succeeded(
        self,
    ) -> None:
        """All-Succeeded dir goes into succeeded set."""
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "music\\Artist\\Album",
                        "files": [
                            {
                                "state": "Completed, Succeeded",
                            },
                            {
                                "state": "Completed, Succeeded",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert "music/Artist/Album" in succeeded
        assert len(failed) == 0

    def test_completed_directories_returns_failed(
        self,
    ) -> None:
        """All-Rejected dir goes into failed set."""
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "music\\Artist\\Album",
                        "files": [
                            {
                                "state": "Completed, Rejected",
                            },
                            {
                                "state": "Completed, Rejected",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert len(succeeded) == 0
        assert "music/Artist/Album" in failed

    def test_completed_directories_mixed_dirs(
        self,
    ) -> None:
        """One succeeded dir, one rejected dir."""
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "music\\Artist\\Album1",
                        "files": [
                            {
                                "state": "Completed, Succeeded",
                            },
                        ],
                    },
                    {
                        "directory": "music\\Artist\\Album2",
                        "files": [
                            {
                                "state": "Completed, Rejected",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert "music/Artist/Album1" in succeeded
        assert "music/Artist/Album2" in failed

    def test_completed_directories_partial_reject(
        self,
    ) -> None:
        """Dir with mix of Succeeded and Rejected → failed."""
        transfers = [
            {
                "username": "user1",
                "directories": [
                    {
                        "directory": "music\\Artist\\Album",
                        "files": [
                            {
                                "state": "Completed, Succeeded",
                            },
                            {
                                "state": "Completed, Rejected",
                            },
                        ],
                    },
                ],
            },
        ]
        succeeded, failed = _completed_directories(
            transfers,
            {"user1"},
        )
        assert len(succeeded) == 0
        assert "music/Artist/Album" in failed
