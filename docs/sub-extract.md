# sub-extract

Extract all subtitle tracks from MKV files.

## Description

`sub-extract` extracts all subtitle tracks from MKV files with intelligent naming based on language codes and track names. It supports parallel processing and provides a rich progress display.

## Features

- Extracts all subtitle formats (SRT, ASS, SSA, VobSub, PGS, WebVTT)
- Intelligent output naming using IETF language tags when available
- Handles multiple tracks with the same language using track names
- Parallel processing support
- Real-time progress display with extraction percentage
- Automatic codec-to-extension mapping

## Requirements

### System Dependencies

- **mkvmerge** (from MKVToolNix) - for identifying tracks
- **mkvextract** (from MKVToolNix) - for extracting tracks

### Python Dependencies

```
rich
```

## Installation

1. Install MKVToolNix:

   ```bash
   # Arch Linux
   sudo pacman -S mkvtoolnix-cli

   # Ubuntu/Debian
   sudo apt install mkvtoolnix

   # macOS
   brew install mkvtoolnix
   ```

2. Install Python dependencies:

   ```bash
   pip install rich
   ```

3. Make the script executable:

   ```bash
   chmod +x sub-extract.py
   ```

## Usage

```bash
# Extract from all MKVs in current directory
sub-extract.py

# Extract from a specific directory
sub-extract.py /path/to/videos

# Extract from a single MKV file
sub-extract.py Movie.mkv

# Use 4 parallel workers
sub-extract.py -p 4

# Specify output directory
sub-extract.py -o /path/to/output
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `path` | Directory containing MKVs, a single .mkv file, or omitted for current directory |
| `-p, --parallel N` | Number of parallel workers (default: 1) |
| `-o, --output DIR` | Output directory for extracted subtitles (must exist) |

## Output Naming

Extracted subtitles follow this naming pattern:

```
VideoName.lang.ext
```

For multiple tracks with the same language:

- Uses IETF tags when available (e.g., `zh-Hans`, `zh-Hant`)
- Falls back to slugified track name as variant
- Appends numbers for disambiguation if needed

### Examples

```
Movie.eng.ass          # Single English track
Movie.jpn.ass          # Single Japanese track
Movie.zh-Hans.ass      # Simplified Chinese (via IETF tag)
Movie.zh-Hant.ass      # Traditional Chinese (via IETF tag)
Movie.chi.signs.ass    # Chinese with "Signs" track name
Movie.chi-2.ass        # Second Chinese track (disambiguation)
```

## Supported Subtitle Formats

| Codec ID | Extension |
|----------|-----------|
| S_TEXT/UTF8, S_TEXT/ASCII | .srt |
| S_TEXT/ASS, S_ASS | .ass |
| S_TEXT/SSA, S_SSA | .ssa |
| S_VOBSUB | .sub |
| S_HDMV/PGS | .sup |
| S_TEXT/WEBVTT | .vtt |
