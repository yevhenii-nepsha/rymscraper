"""Domain models for rymparser."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Album:
    """A music album parsed from RYM."""

    artist: str
    title: str
    year: str

    def __str__(self) -> str:
        """Format as 'Artist - Title (Year)' for Soulseek search."""
        if self.year:
            return f"{self.artist} - {self.title} ({self.year})"
        return f"{self.artist} - {self.title}"
