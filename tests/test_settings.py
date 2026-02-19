"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from rymparser.settings import AppSettings, load_settings


@pytest.fixture
def config_toml(tmp_path: Path) -> Path:
    """Create a minimal config.toml file."""
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        "[slskd]\n"
        'host = "http://myhost:5030"\n'
        'api_key = "test-key-1234567890"\n'
        "\n"
        "[search]\n"
        'preferred_formats = ["flac"]\n'
        "min_bitrate = 256\n"
        "search_timeout = 20\n"
        "\n"
        "[download]\n"
        'output_dir = "/tmp/music"\n'
    )
    return cfg


@pytest.fixture
def empty_config(tmp_path: Path) -> Path:
    """Create an empty config.toml file."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("")
    return cfg


class TestAppSettings:
    def test_defaults(self) -> None:
        settings = AppSettings()
        assert settings.slskd_host == "http://localhost:5030"
        assert settings.slskd_api_key == ""
        assert settings.preferred_formats == ["flac", "mp3"]
        assert settings.min_bitrate == 320
        assert settings.search_timeout == 30
        assert settings.min_files == 3

    def test_frozen(self) -> None:
        settings = AppSettings()
        with pytest.raises(AttributeError):
            settings.slskd_host = "x"  # type: ignore[misc]


class TestLoadSettings:
    def test_from_config_file(
        self,
        config_toml: Path,
    ) -> None:
        settings = load_settings(config_path=config_toml)
        assert settings.slskd_host == "http://myhost:5030"
        assert settings.slskd_api_key == "test-key-1234567890"
        assert settings.preferred_formats == ["flac"]
        assert settings.min_bitrate == 256
        assert settings.search_timeout == 20
        assert settings.download_dir == Path("/tmp/music")

    def test_env_vars_override(
        self,
        config_toml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SLSKD_HOST", "http://env:9999")
        monkeypatch.setenv(
            "SLSKD_API_KEY",
            "env-key-abcdef1234",
        )
        settings = load_settings(config_path=config_toml)
        assert settings.slskd_host == "http://env:9999"
        assert settings.slskd_api_key == "env-key-abcdef1234"

    def test_defaults_when_no_config(
        self,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "nonexistent.toml"
        settings = load_settings(config_path=missing)
        assert settings.slskd_host == "http://localhost:5030"

    def test_empty_config_uses_defaults(
        self,
        empty_config: Path,
    ) -> None:
        settings = load_settings(config_path=empty_config)
        assert settings.min_bitrate == 320
