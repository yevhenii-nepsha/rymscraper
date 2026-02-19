"""Thin wrapper around slskd-api for rymparser."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import slskd_api

if TYPE_CHECKING:
    from rymparser.settings import AppSettings

logger = logging.getLogger(__name__)

SearchResponse = dict[str, Any]


class SlskdError(Exception):
    """Raised when slskd communication fails."""


def create_client(
    settings: AppSettings,
) -> slskd_api.SlskdClient:
    """Create an authenticated slskd API client.

    Args:
        settings: Application settings with slskd
            host and API key.

    Returns:
        Configured SlskdClient instance.

    Raises:
        SlskdError: If API key is not configured.
    """
    if not settings.slskd_api_key:
        raise SlskdError(
            "slskd API key is required. Set it in "
            "config.toml or SLSKD_API_KEY env var."
        )
    return slskd_api.SlskdClient(
        host=settings.slskd_host,
        api_key=settings.slskd_api_key,
    )


def search_albums(
    client: slskd_api.SlskdClient,
    query: str,
    *,
    timeout: int = 30,
) -> list[SearchResponse]:
    """Search Soulseek for a query via slskd.

    Args:
        client: Authenticated slskd client.
        query: Search query string.
        timeout: Max seconds to wait for results.

    Returns:
        List of response dicts from slskd API.

    Raises:
        SlskdError: If the search fails.
    """
    try:
        search = client.searches.search_text(
            searchText=query,
            searchTimeout=timeout * 1000,
        )
    except Exception as exc:
        raise SlskdError(f"Failed to start search: {exc}") from exc

    search_id: str = search["id"]
    logger.info(
        "Search started (id=%s): %s",
        search_id,
        query,
    )

    deadline = time.time() + timeout + 5
    while time.time() < deadline:
        state = client.searches.state(search_id)
        if state.get("isComplete", False):
            break
        time.sleep(1)
    else:
        logger.warning("Search timed out: %s", query)

    try:
        responses: list[SearchResponse] = client.searches.search_responses(
            search_id
        )
    except Exception as exc:
        raise SlskdError(f"Failed to get search results: {exc}") from exc

    logger.info(
        "Search returned %d responses for: %s",
        len(responses),
        query,
    )
    return responses


def enqueue_download(
    client: slskd_api.SlskdClient,
    username: str,
    files: list[dict[str, Any]],
) -> bool:
    """Queue files for download from a peer.

    Args:
        client: Authenticated slskd client.
        username: Soulseek username to download from.
        files: List of file dicts from search results.

    Returns:
        True if enqueue succeeded.

    Raises:
        SlskdError: If enqueue fails.
    """
    try:
        client.transfers.enqueue(
            username=username,
            files=files,
        )
    except Exception as exc:
        raise SlskdError(
            f"Failed to enqueue download from {username}: {exc}"
        ) from exc

    logger.info(
        "Enqueued %d files from %s",
        len(files),
        username,
    )
    return True


def get_downloads(
    client: slskd_api.SlskdClient,
) -> list[dict[str, Any]]:
    """Get all current downloads.

    Args:
        client: Authenticated slskd client.

    Returns:
        List of transfer dicts grouped by user.
    """
    return client.transfers.get_all_downloads()  # type: ignore[no-any-return]
