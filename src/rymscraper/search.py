"""Search filtering and ranking for Soulseek results."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from rymscraper.models import Album  # noqa: TC001 (runtime usage)

if TYPE_CHECKING:
    from rymscraper.settings import AppSettings

logger = logging.getLogger(__name__)

LOSSLESS_FORMATS = frozenset({"flac", "wav", "alac", "ape", "wv"})


@dataclass(frozen=True)
class AlbumSearchResult:
    """A filtered, ranked search result for one album."""

    username: str
    directory: str
    files: list[dict[str, Any]]
    format: str
    bitrate: int
    upload_speed: int
    has_free_slot: bool
    queue_length: int


def build_query(album: Album) -> str:
    """Build a Soulseek search query from an Album.

    Args:
        album: The album to search for.

    Returns:
        Search query string (artist + title, no year).
    """
    return f"{album.artist} {album.title}"


def _normalize_ext(raw: str) -> str:
    """Normalize a file extension to lowercase without dot."""
    return raw.lower().lstrip(".")


def _file_ext(f: dict[str, Any]) -> str:
    """Extract normalized extension from a file dict.

    Uses the 'extension' field if non-empty, otherwise
    falls back to extracting from 'filename'.

    Args:
        f: slskd file dict with extension/filename.

    Returns:
        Lowercase extension without dot, or "".
    """
    ext = _normalize_ext(str(f.get("extension", "")))
    if ext:
        return ext
    filename = str(f.get("filename", ""))
    if "." in filename:
        return _normalize_ext(
            filename.rsplit(".", maxsplit=1)[-1],
        )
    return ""


def _dominant_format(
    files: list[dict[str, Any]],
) -> str:
    """Determine the dominant audio format in files."""
    counts: dict[str, int] = {}
    for f in files:
        ext = _file_ext(f)
        if ext:
            counts[ext] = counts.get(ext, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda k: counts[k])


def _avg_bitrate(
    files: list[dict[str, Any]],
) -> int:
    """Calculate average bitrate of audio files."""
    rates = [int(f["bitRate"]) for f in files if f.get("bitRate")]
    return int(sum(rates) / len(rates)) if rates else 0


_SKIP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "and",
        "or",
        "for",
        "by",
        "is",
        "it",
        "no",
    }
)


def _matches_album(directory: str, album: Album) -> bool:
    """Check if directory path contains album title keywords.

    Splits the album title into words and checks that each
    significant word (length > 2, not a stop word) appears
    in the lowercased directory path.

    Args:
        directory: Normalized directory path from search result.
        album: The album being searched for.

    Returns:
        True if all significant title words found in path.
    """
    path_lower = directory.lower()
    words = album.title.lower().split()
    significant = [w for w in words if len(w) > 2 and w not in _SKIP_WORDS]
    if not significant:
        return True
    return all(w in path_lower for w in significant)


def filter_responses(
    responses: list[dict[str, Any]],
    settings: AppSettings,
    album: Album | None = None,
) -> list[AlbumSearchResult]:
    """Filter raw slskd responses into valid results.

    Args:
        responses: Raw search responses from slskd.
        settings: App settings with filter criteria.
        album: Optional album to check directory relevance.

    Returns:
        List of AlbumSearchResult passing all filters.
    """
    results: list[AlbumSearchResult] = []

    for resp in responses:
        username = str(resp.get("username", ""))
        files = resp.get("files", [])
        all_exts = [ext for f in files if (ext := _file_ext(f))]
        logger.debug(
            "Response from %s: %d files, extensions: %s, keys: %s",
            username,
            len(files),
            sorted(set(all_exts)),
            sorted(files[0].keys()) if files else "N/A",
        )
        audio_files = [
            f for f in files if _file_ext(f) in settings.preferred_formats
        ]

        if len(audio_files) < settings.min_files:
            logger.debug(
                "Rejected %s: %d/%d files match "
                "formats %s (need %d). "
                "Extensions found: %s",
                username,
                len(audio_files),
                len(files),
                settings.preferred_formats,
                settings.min_files,
                sorted(set(all_exts)),
            )
            continue

        fmt = _dominant_format(audio_files)
        bitrate = _avg_bitrate(audio_files)

        if fmt not in LOSSLESS_FORMATS and bitrate < settings.min_bitrate:
            logger.debug(
                "Rejected %s: %s %dkbps < min %dkbps",
                username,
                fmt,
                bitrate,
                settings.min_bitrate,
            )
            continue

        first_file = str(audio_files[0].get("filename", ""))
        directory = str(
            PurePosixPath(first_file.replace("\\", "/")).parent,
        )

        if album and not _matches_album(directory, album):
            logger.debug(
                "Rejected %s: directory %r does not match album %r",
                username,
                directory,
                album.title,
            )
            continue

        results.append(
            AlbumSearchResult(
                username=str(resp.get("username", "")),
                directory=directory,
                files=audio_files,
                format=fmt,
                bitrate=bitrate,
                upload_speed=int(resp.get("uploadSpeed", 0)),
                has_free_slot=bool(
                    resp.get("hasFreeUploadSlot", False),
                ),
                queue_length=int(resp.get("queueLength", 0)),
            )
        )

    return results


def rank_results(
    results: list[AlbumSearchResult],
    settings: AppSettings,
) -> list[AlbumSearchResult]:
    """Rank filtered results from best to worst.

    Ranking (descending priority):
    1. Format preference order
    2. Free upload slot
    3. Higher bitrate
    4. Faster upload speed
    5. Shorter queue

    Args:
        results: Filtered search results.
        settings: App settings with format preferences.

    Returns:
        Results sorted best to worst.
    """
    format_order = {
        fmt: idx for idx, fmt in enumerate(settings.preferred_formats)
    }
    max_idx = len(settings.preferred_formats)

    def sort_key(
        r: AlbumSearchResult,
    ) -> tuple[int, int, int, int, int]:
        return (
            format_order.get(r.format, max_idx),
            0 if r.has_free_slot else 1,
            -r.bitrate,
            -r.upload_speed,
            r.queue_length,
        )

    return sorted(results, key=sort_key)
