"""Tests for CLI argument parsing and validation."""

from rymparser.cli import parse_args, validate_url


class TestValidateUrl:
    def test_valid_rym_url(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        assert validate_url(url) is True

    def test_invalid_domain(self) -> None:
        assert validate_url("https://example.com/") is False

    def test_empty_url(self) -> None:
        assert validate_url("") is False


class TestParseArgs:
    def test_minimal_args(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args([url])
        assert args.url == url
        assert args.output is None
        assert args.headless is False
        assert args.verbose is False

    def test_output_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["-o", "out.txt", url])
        assert args.output == "out.txt"

    def test_headless_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["--headless", url])
        assert args.headless is True

    def test_verbose_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["-v", url])
        assert args.verbose is True
