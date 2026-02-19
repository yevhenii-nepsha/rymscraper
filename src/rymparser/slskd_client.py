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

    # Poll until complete or responses stabilize.
    # slskd only returns responses after a search is
    # Completed. We stop the search early once response
    # count stabilizes to avoid waiting for the full
    # searchTimeout.
    stable_rounds = 0
    prev_count = 0
    resp_count = 0
    deadline = time.time() + timeout + 10
    while time.time() < deadline:
        state = client.searches.state(search_id)
        resp_count = int(
            state.get("responseCount", 0),
        )
        if state.get("isComplete", False):
            break
        if resp_count > 0 and resp_count == prev_count:
            stable_rounds += 1
            if stable_rounds >= 5:
                logger.debug(
                    "Responses stabilized at %d, stopping search early",
                    resp_count,
                )
                client.searches.stop(search_id)
                # Wait briefly for state to update
                time.sleep(1)
                break
        else:
            stable_rounds = 0
        prev_count = resp_count
        time.sleep(1)
    else:
        logger.warning(
            "Search timed out for: %s (%d responses so far)",
            query,
            resp_count,
        )

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


_COMPLETED_STATES = frozenset(
    {
        "Completed, Succeeded",
        "Completed, Cancelled",
        "Completed, TimedOut",
        "Completed, Errored",
    }
)


def _completed_directories(
    transfers: list[dict[str, Any]],
    usernames: set[str],
) -> set[str]:
    """Find directories where all files are done.

    Directory paths are normalized (backslashes to forward
    slashes) to match across different data sources.

    Args:
        transfers: Raw transfer list from slskd API.
        usernames: Set of usernames to check.

    Returns:
        Set of normalized directory paths that are complete.
    """
    completed: set[str] = set()
    for t in transfers:
        if t.get("username") not in usernames:
            continue
        for d in t.get("directories", []):
            files = d.get("files", [])
            if not files:
                continue
            all_done = all(
                str(f.get("state", "")) in _COMPLETED_STATES for f in files
            )
            if all_done:
                raw_dir = str(d.get("directory", ""))
                completed.add(
                    raw_dir.replace("\\", "/"),
                )
    return completed
