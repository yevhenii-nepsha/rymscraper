"""Post-download file organization into Artist/Album structure."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from rymparser.models import Album
from rymparser.slskd_client import (
    SlskdError,
    _completed_directories,
    enqueue_download,
)

if TYPE_CHECKING:
    import slskd_api

logger = logging.getLogger(__name__)


def _album_target_dir(
    album: Album,
    downloads_dir: Path,
) -> Path:
    """Build the target directory for an album.

    Structure: downloads_dir / Artist / Title (Year)

    Args:
        album: Parsed album metadata.
        downloads_dir: Root downloads directory.

    Returns:
        Target directory path.
    """
    folder = f"{album.title} ({album.year})" if album.year else album.title
    return downloads_dir / album.artist / folder


def _source_dir_name(directory: str) -> str:
    """Extract the folder name slskd uses from remote path.

    slskd saves downloads in the last path component of
    the remote directory. E.g.:
    ``@@fknkb\\Library\\Bowel Erosion\\Death Is ...``
    becomes ``Death Is ...``.

    Args:
        directory: Remote directory path from search result.

    Returns:
        Folder name as it appears in downloads/.
    """
    normalized = directory.replace("\\", "/")
    return PurePosixPath(normalized).name


def _normalize_path(directory: str) -> str:
    """Normalize remote path separators to forward slash.

    Args:
        directory: Remote directory path.

    Returns:
        Path with backslashes replaced by forward slashes.
    """
    return directory.replace("\\", "/")


def _build_dir_to_album_map(
    results: dict[str, Any],
) -> dict[str, tuple[str, str]]:
    """Build mapping from normalized remote path to album info.

    Args:
        results: Search results dict (album_str -> data).

    Returns:
        Dict mapping normalized path -> (album_str, remote_dir).
    """
    mapping: dict[str, tuple[str, str]] = {}
    for album_str, data in results.items():
        if data is None:
            continue
        assert isinstance(data, dict)
        # New format: alternatives list
        if "alternatives" in data:
            idx = data.get("selected", 0)
            alts = data["alternatives"]
            if idx < len(alts):
                remote_dir = str(alts[idx].get("directory", ""))
            else:
                continue
        else:
            # Legacy format
            remote_dir = str(data.get("directory", ""))
        if not remote_dir:
            continue
        key = _normalize_path(remote_dir)
        mapping[key] = (album_str, remote_dir)
    return mapping


def _organize_album(
    album_str: str,
    remote_dir: str,
    downloads_dir: Path,
) -> bool:
    """Move a single downloaded album into Artist/Album structure.

    Args:
        album_str: Album string in 'Artist - Title (Year)' format.
        remote_dir: Remote directory path from search result.
        downloads_dir: Root downloads directory.

    Returns:
        True if the album was moved successfully, False otherwise.
    """
    folder_name = _source_dir_name(remote_dir)
    source = downloads_dir / folder_name

    if not source.exists():
        logger.warning(
            "Source not found: %s (for %s)",
            source,
            album_str,
        )
        return False

    try:
        album = Album.from_line(album_str)
    except ValueError:
        logger.warning(
            "Cannot parse album: %s",
            album_str,
        )
        return False

    target = _album_target_dir(album, downloads_dir)

    if source == target:
        logger.debug(
            "Already organized: %s",
            album_str,
        )
        return True

    if target.exists():
        logger.warning(
            "Target already exists: %s",
            target,
        )
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(target))
    except OSError:
        logger.exception(
            "Failed to move: %s -> %s",
            source.name,
            target.relative_to(downloads_dir),
        )
        return False
    logger.info(
        "Moved: %s -> %s",
        source.name,
        target.relative_to(downloads_dir),
    )
    return True


def organize_downloads(
    results: dict[str, Any],
    downloads_dir: Path,
) -> tuple[int, int]:
    """Move downloaded albums into Artist/Album structure.

    Args:
        results: Search results dict (album_str -> data).
        downloads_dir: Path to slskd downloads directory.

    Returns:
        Tuple of (moved_count, skipped_count).
    """
    moved = 0
    skipped = 0

    for album_str, data in results.items():
        if data is None:
            skipped += 1
            continue

        assert isinstance(data, dict)
        remote_dir = str(data.get("directory", ""))
        if not remote_dir:
            logger.warning(
                "No directory in result for: %s",
                album_str,
            )
            skipped += 1
            continue

        if _organize_album(album_str, remote_dir, downloads_dir):
            moved += 1
        else:
            skipped += 1

    return moved, skipped


def wait_and_organize(
    client: slskd_api.SlskdClient,
    results: dict[str, Any],
    usernames: set[str],
    downloads_dir: Path,
    *,
    timeout: int = 1800,
    poll_interval: int = 10,
) -> tuple[int, int]:
    """Wait for downloads and organize each album as it completes.

    Polls slskd transfers, and each time a directory reaches
    a fully-completed state, moves it into Artist/Album (Year)/
    structure immediately.

    Args:
        client: Authenticated slskd client.
        results: Search results dict (album_str -> data).
        usernames: Set of peer usernames to monitor.
        downloads_dir: Root downloads directory.
        timeout: Max seconds to wait (default 30 min).
        poll_interval: Seconds between polls.

    Returns:
        Tuple of (organized_count, skipped_count).
    """
    dir_map = _build_dir_to_album_map(results)
    total_expected = len(dir_map)
    null_count = sum(1 for v in results.values() if v is None)
    organized: set[str] = set()
    moved = 0

    attempt_index: dict[str, int] = {}
    for album_str, data in results.items():
        if data and isinstance(data, dict):
            attempt_index[album_str] = data.get("selected", 0)

    if total_expected == 0:
        return 0, null_count

    deadline = time.time() + timeout
    while time.time() < deadline:
        transfers: list[dict[str, Any]] = client.transfers.get_all_downloads()
        newly_done, newly_failed = _completed_directories(
            transfers,
            usernames,
        )

        for dir_name in newly_done:
            if dir_name in organized:
                continue
            if dir_name not in dir_map:
                continue
            album_str, remote_dir = dir_map[dir_name]
            if _organize_album(
                album_str,
                remote_dir,
                downloads_dir,
            ):
                moved += 1
            organized.add(dir_name)

        for dir_name in newly_failed:
            if dir_name in organized:
                continue
            if dir_name not in dir_map:
                organized.add(dir_name)
                continue

            album_str, _remote_dir = dir_map[dir_name]
            data = results.get(album_str)
            if not data or not isinstance(data, dict):
                organized.add(dir_name)
                continue

            alts = data.get("alternatives", [])
            idx = attempt_index.get(album_str, 0) + 1

            if idx < len(alts):
                next_alt = alts[idx]
                attempt_index[album_str] = idx
                next_username = str(next_alt["username"])
                next_files = next_alt["files"]

                try:
                    enqueue_download(
                        client,
                        next_username,
                        next_files,
                    )
                except SlskdError as exc:
                    logger.error(
                        "Failed to enqueue retry for %s: %s",
                        album_str,
                        exc,
                    )
                    organized.add(dir_name)
                    continue

                # Update tracking for new download
                new_dir = _normalize_path(str(next_alt.get("directory", "")))
                dir_map[new_dir] = (
                    album_str,
                    str(next_alt.get("directory", "")),
                )
                usernames.add(next_username)
                total_expected += 1

                logger.info(
                    "Retry %d/%d: %s from @%s",
                    idx + 1,
                    len(alts),
                    album_str,
                    next_username,
                )
            else:
                logger.warning(
                    "All %d alternatives exhausted for: %s",
                    len(alts),
                    album_str,
                )

            organized.add(dir_name)

        if len(organized) >= total_expected:
            break

        logger.info(
            "Downloads: %d/%d albums done, waiting...",
            len(organized),
            total_expected,
        )
        time.sleep(poll_interval)
    else:
        logger.warning(
            "Timed out after %ds: %d/%d organized",
            timeout,
            len(organized),
            total_expected,
        )

    skipped = total_expected - moved + null_count
    return moved, skipped
