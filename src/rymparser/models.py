"""Domain models for rymparser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ReleaseType(Enum):
    """Release type categories from RYM artist pages."""

    ALBUM = "album"
    LIVE_ALBUM = "live_album"
    EP = "ep"
    SINGLE = "single"
    COMPILATION = "compilation"
    MUSIC_VIDEO = "music_video"
    APPEARS_ON = "appears_on"
    VA_COMPILATION = "va_compilation"
    BOOTLEG = "bootleg"
    VIDEO = "video"
    ADDITIONAL = "additional"


@dataclass(frozen=True)
class Album:
    """A music album parsed from RYM."""

    artist: str
    title: str
    year: str
    release_type: ReleaseType | None = None

    def __str__(self) -> str:
        """Format as 'Artist - Title (Year)'."""
        if self.year:
            return f"{self.artist} - {self.title} ({self.year})"
        return f"{self.artist} - {self.title}"

    @classmethod
    def from_line(cls, line: str) -> Album:
        """Parse 'Artist - Title (Year)' format.

        Args:
            line: A line in the output format.

        Returns:
            Album instance.

        Raises:
            ValueError: If line cannot be parsed.
        """
        match = re.match(
            r"^(.+?)\s*-\s*(.+?)(?:\s*\((\d{4})\))?\s*$",
            line,
        )
        if not match:
            raise ValueError(f"Cannot parse album line: {line!r}")
        return cls(
            artist=match.group(1).strip(),
            title=match.group(2).strip(),
            year=match.group(3) or "",
        )
