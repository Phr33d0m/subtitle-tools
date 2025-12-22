# sub-merge

Merge subtitle files into video containers using mkvmerge.

## Description

`sub-merge` finds video files and their matching subtitle files, then merges them into MKV containers with proper language metadata and font attachments.

## Features

- Automatic subtitle detection based on filename matching
- Support for both IETF language tags (zh-Hans, pt-BR) and traditional 3-letter codes (eng, chi)
- Priority handling: ASS subtitles take priority over SRT
- Optional font embedding from a `Fonts/` directory for ASS subtitles
- Parallel processing support for batch operations
- Replace or append mode for existing subtitles
- Rich progress display with real-time status

## Requirements

### System Dependencies

- **mkvmerge** (from MKVToolNix) - for merging video and subtitle files
- **file** command - for MIME type detection

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
   chmod +x sub-merge.py
   ```

## Usage

```bash
# Process all videos in current directory (replace mode)
sub-merge.py

# Process a specific directory
sub-merge.py /path/to/videos

# Process a single video file
sub-merge.py Movie.mkv

# Use 4 parallel workers
sub-merge.py -p 4

# Append subtitles instead of replacing existing ones
sub-merge.py --mode append

# Preview operations without executing
sub-merge.py --dry-run

# Verbose output
sub-merge.py -v

# Process directory recursively
sub-merge.py -r /path/to/videos
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `path` | Directory containing video files, or a single video file (default: current directory) |
| `-p, --parallel N` | Number of parallel workers (default: 1) |
| `--mode {append,replace}` | Subtitle merge mode: replace (default) removes existing subtitles, append preserves existing subtitles |
| `--dry-run` | Preview operations without executing |
| `-v, --verbose` | Enable verbose logging |
| `-r, --recursive` | Search for video files recursively in subdirectories |

## File Naming Convention

Subtitle files must follow this naming pattern:

```
VideoName.lang.ext
```

Where:

- `VideoName` matches the video file name (without extension)
- `lang` is a language code (e.g., `eng`, `chi`, `zh-Hans`, `pt-BR`)
- `ext` is the subtitle extension (`.ass`, `.srt`)

### Examples

```
Movie.mp4
Movie.eng.ass      # English subtitles
Movie.zh-Hans.ass  # Simplified Chinese subtitles
Movie.chi.srt      # Chinese SRT subtitles
```

## Fonts Directory

If a `Fonts/` directory exists in the same location as the video files, all fonts (TTF, OTF, TTC, WOFF, WOFF2) will be embedded into the MKV container when ASS subtitles are merged.

## Modes

### Replace Mode (default)

- Removes all existing subtitle tracks from the video
- Adds new subtitle files
- In replace mode with external fonts: replaces embedded fonts
- In replace mode without external fonts: preserves existing embedded fonts

### Append Mode

- Preserves all existing subtitle tracks
- Adds new subtitle files as additional tracks
- Avoids duplicate font attachments
