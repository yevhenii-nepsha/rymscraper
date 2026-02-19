"""Tests for CLI subcommands."""

from __future__ import annotations

from rymparser.cli import build_parser, validate_url


class TestValidateUrl:
    def test_valid_rym_url(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        assert validate_url(url) is True

    def test_invalid_domain(self) -> None:
        assert validate_url("https://example.com/") is False

    def test_empty_url(self) -> None:
        assert validate_url("") is False


class TestBuildParser:
    def test_parse_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.command == "parse"
        assert args.url == ("https://rateyourmusic.com/list/u/test/")

    def test_parse_with_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "parse",
                "-o",
                "out.txt",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.output == "out.txt"

    def test_search_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "search",
                "albums.txt",
            ]
        )
        assert args.command == "search"
        assert args.file == "albums.txt"

    def test_search_auto_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "search",
                "--auto",
                "albums.txt",
            ]
        )
        assert args.auto is True

    def test_download_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "download",
                "results.json",
            ]
        )
        assert args.command == "download"
        assert args.file == "results.json"

    def test_go_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "go",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.command == "go"
        assert args.url == ("https://rateyourmusic.com/list/u/test/")

    def test_verbose_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "-v",
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.verbose is True

    def test_config_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--config",
                "/tmp/cfg.toml",
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.config == "/tmp/cfg.toml"
