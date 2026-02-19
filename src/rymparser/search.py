"""Search filtering and ranking for Soulseek results."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rymparser.models import Album
    from rymparser.settings import AppSettings

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


def _dominant_format(
    files: list[dict[str, Any]],
) -> str:
    """Determine the dominant audio format in files."""
    counts: dict[str, int] = {}
    for f in files:
        ext = str(f.get("extension", "")).lower()
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


def filter_responses(
    responses: list[dict[str, Any]],
    settings: AppSettings,
) -> list[AlbumSearchResult]:
    """Filter raw slskd responses into valid results.

    Args:
        responses: Raw search responses from slskd.
        settings: App settings with filter criteria.

    Returns:
        List of AlbumSearchResult passing all filters.
    """
    results: list[AlbumSearchResult] = []

    for resp in responses:
        files = resp.get("files", [])
        audio_files = [
            f
            for f in files
            if str(f.get("extension", "")).lower() in settings.preferred_formats
        ]

        if len(audio_files) < settings.min_files:
            continue

        fmt = _dominant_format(audio_files)
        bitrate = _avg_bitrate(audio_files)

        if fmt not in LOSSLESS_FORMATS and bitrate < settings.min_bitrate:
            continue

        first_file = str(audio_files[0].get("filename", ""))
        directory = str(PurePosixPath(first_file.replace("\\", "/")).parent)

        results.append(
            AlbumSearchResult(
                username=str(resp.get("username", "")),
                directory=directory,
                files=audio_files,
                format=fmt,
                bitrate=bitrate,
                upload_speed=int(resp.get("uploadSpeed", 0)),
                has_free_slot=bool(resp.get("hasFreeUploadSlot", False)),
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
