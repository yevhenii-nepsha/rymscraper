"""Configuration loading from config.toml and env vars."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def _default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".config" / "rymparser" / "config.toml"


@dataclass(frozen=True)
class AppSettings:
    """Application-wide settings.

    Loaded from config.toml and overridden by env vars.
    """

    slskd_host: str = "http://localhost:5030"
    slskd_api_key: str = ""
    preferred_formats: list[str] = field(
        default_factory=lambda: ["flac", "mp3"],
    )
    min_bitrate: int = 320
    search_timeout: int = 30
    min_files: int = 1
    download_dir: Path = field(
        default_factory=lambda: Path("downloads"),
    )


def load_settings(
    config_path: Path | None = None,
) -> AppSettings:
    """Load settings from config file and env vars.

    Priority: env vars > config.toml > defaults.

    Args:
        config_path: Path to config.toml. Uses default
            (~/.config/rymparser/config.toml) if None.

    Returns:
        Frozen AppSettings instance.
    """
    if config_path is None:
        config_path = _default_config_path()

    file_cfg: dict[str, dict[str, object]] = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_cfg = tomllib.load(f)

    slskd_cfg = file_cfg.get("slskd", {})
    search_cfg = file_cfg.get("search", {})
    download_cfg = file_cfg.get("download", {})

    host = str(
        slskd_cfg.get("host", "http://localhost:5030"),
    )
    api_key = str(slskd_cfg.get("api_key", ""))

    host = os.environ.get("SLSKD_HOST", host)
    api_key = os.environ.get("SLSKD_API_KEY", api_key)

    formats_raw = search_cfg.get(
        "preferred_formats",
        ["flac", "mp3"],
    )
    preferred_formats = (
        list(formats_raw) if isinstance(formats_raw, list) else ["flac", "mp3"]
    )
    min_bitrate_raw = search_cfg.get("min_bitrate", 320)
    min_bitrate = min_bitrate_raw if isinstance(min_bitrate_raw, int) else 320
    timeout_raw = search_cfg.get("search_timeout", 30)
    search_timeout = timeout_raw if isinstance(timeout_raw, int) else 30
    min_files_raw = search_cfg.get("min_files", 1)
    min_files = min_files_raw if isinstance(min_files_raw, int) else 1

    output_dir_raw = download_cfg.get(
        "output_dir",
        "downloads",
    )
    download_dir = Path(
        os.path.expanduser(str(output_dir_raw)),
    )

    return AppSettings(
        slskd_host=host,
        slskd_api_key=api_key,
        preferred_formats=preferred_formats,
        min_bitrate=min_bitrate,
        search_timeout=search_timeout,
        min_files=min_files,
        download_dir=download_dir,
    )
