# rymparser

Parse [RateYourMusic](https://rateyourmusic.com) list pages into
`Artist - Album (Year)` format, then search and download from
[Soulseek](http://www.slsknet.org/) via
[slskd](https://github.com/slskd/slskd).

Handles Cloudflare Turnstile anti-bot challenges using a headed
Chromium browser with stealth plugins and a persistent browser
profile.

## Installation

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run playwright install chromium
```

## Quick Start

```bash
# 1. Parse a RYM list
uv run rymparser parse https://rateyourmusic.com/list/user/best-albums/

# 2. Search Soulseek (auto-select best result per album)
uv run rymparser search --auto best-albums.txt

# 3. Download and organize into Artist/Album (Year)/
uv run rymparser download best-albums.json

# Or do it all at once
uv run rymparser go --auto https://rateyourmusic.com/list/user/best-albums/
```

## Subcommands

### `parse` -- scrape RYM list

```bash
uv run rymparser parse https://rateyourmusic.com/list/user/test/
uv run rymparser parse -o albums.txt https://rateyourmusic.com/list/user/test/
uv run rymparser parse --headless https://rateyourmusic.com/list/user/test/
```

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output filename (default: `{slug}.txt`) |
| `--headless` | Run browser headless (may be blocked by Cloudflare) |

Output format:

```
Radiohead - OK Computer (1997)
Bjork - Homogenic (1997)
Boards of Canada - Music Has the Right to Children (1998)
```

### `search` -- find albums on Soulseek

```bash
uv run rymparser search albums.txt              # interactive mode
uv run rymparser search --auto albums.txt       # auto-select best
uv run rymparser search --auto --format flac --min-bitrate 256 albums.txt
uv run rymparser search --auto --min-files 3 albums.txt
```

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output results file (default: `{input}.json`) |
| `--auto` | Auto-select best result (skip interactive prompts) |
| `--format` | Override preferred format (`flac`, `mp3`) |
| `--min-bitrate` | Override minimum bitrate |
| `--min-files` | Minimum audio files per result |

In interactive mode, shows top 5 results per album with format,
bitrate, file count, upload speed, and queue status.

### `download` -- download and organize

```bash
uv run rymparser download results.json
uv run rymparser download --downloads-dir /path/to/downloads results.json
```

| Flag | Description |
|------|-------------|
| `--downloads-dir` | Path to slskd downloads directory |

Downloads are enqueued via slskd. Each album is organized into
`Artist/Album (Year)/` structure as soon as its download completes
(no waiting for all albums to finish). If the 30-minute timeout
is reached, already-organized albums are kept:

```
downloads/
  Bowel Erosion/
    Death Is the Orgasm of Life (2023)/
      01 - Coughing Up Your Intestines.flac
      02 - Found in Pieces.flac
  Organ Failure/
    Demo (2021)/
    Neurologic Determination of Death (2022)/
```

### `go` -- all-in-one pipeline

```bash
uv run rymparser go https://rateyourmusic.com/list/user/test/
uv run rymparser go --auto https://rateyourmusic.com/list/user/test/
uv run rymparser go --auto --headless https://rateyourmusic.com/list/user/test/
```

Runs parse, search, and download in sequence.

### Global flags

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Enable debug logging |
| `--config` | Path to config.toml |

## Docker

1. Copy `.env.example` to `.env` and fill in credentials:

   ```bash
   cp .env.example .env
   ```

   Required variables:

   | Variable | Description |
   |----------|-------------|
   | `SLSK_USERNAME` | Soulseek login |
   | `SLSK_PASSWORD` | Soulseek password |
   | `SLSKD_API_KEY` | slskd API key (min 16 chars) |

2. Start slskd:

   ```bash
   docker compose up -d slskd
   ```

3. Run rymparser:

   ```bash
   # Full pipeline
   docker compose run rymparser go --auto \
     https://rateyourmusic.com/list/user/best-albums/

   # Or step by step
   docker compose run rymparser parse https://rateyourmusic.com/list/user/test/
   docker compose run rymparser search --auto test.txt
   docker compose run rymparser download test.json
   ```

Downloads appear in `./downloads/` on the host.

## Configuration

Create `~/.config/rymparser/config.toml`:

```toml
[slskd]
host = "http://localhost:5030"
api_key = "your-api-key"

[search]
preferred_formats = ["flac", "mp3"]
min_bitrate = 320
search_timeout = 30
min_files = 1

[download]
output_dir = "downloads"
```

Environment variables `SLSKD_HOST` and `SLSKD_API_KEY` override
config file values. Priority: env vars > config.toml > defaults.

## Development

```bash
uv run pytest          # run tests (63 tests)
uv run mypy src/       # type checking (strict)
uv run ruff check .    # linting
```
