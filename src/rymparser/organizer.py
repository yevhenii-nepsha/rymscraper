"""Post-download file organization into Artist/Album structure."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

from rymparser.models import Album

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
