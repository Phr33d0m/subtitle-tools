# subs-collection

Build a mirrored directory structure with only subtitles and attachments.

## Description

`subs-collection` walks a TV series collection, extracts subtitles and attachments from MKV files, and creates a mirrored directory structure in the output directory. Directories containing only hardsubbed content (no extractable subtitles) are automatically removed.

## Features

- Mirrors directory structure from source to destination
- Extracts subtitles and attachments using `sub-extract` and `sub-attachment-extract`
- Creates `.nosubs` markers for hardsubbed files
- Removes orphaned subtitle files when source MKVs are deleted
- Creates ZIP archives of extracted content
- BGPP tagging support for releases with version numbers
- Ignore patterns for directories and files
- Rich progress display

## Requirements

### System Dependencies

- **sub-extract** - Must be in PATH (from this toolset)
- **sub-attachment-extract** - Must be in PATH (from this toolset)
- **MKVToolNix** - Required by sub-extract and sub-attachment-extract

### Python Dependencies

```
rich
```

## Installation

1. Ensure `sub-extract` and `sub-attachment-extract` are installed and in your PATH:

   ```bash
   # Add to PATH or create symlinks
   ln -s /path/to/sub-extract.py ~/.local/bin/sub-extract
   ln -s /path/to/sub-attachment-extract.py ~/.local/bin/sub-attachment-extract
   ```

2. Install Python dependencies:

   ```bash
   pip install rich
   ```

3. Make the script executable:

   ```bash
   chmod +x subs-collection.py
   ```

## Usage

```bash
# Basic usage
subs-collection.py /path/to/tv-shows /path/to/subs-output

# Preview without extracting
subs-collection.py /path/to/tv-shows /path/to/subs-output --dry-run

# Verbose output
subs-collection.py /path/to/tv-shows /path/to/subs-output -v

# Ignore specific directories
subs-collection.py /path/to/tv-shows /path/to/subs-output -D "Extras" -D "Specials"

# Ignore files containing pattern
subs-collection.py /path/to/tv-shows /path/to/subs-output -F "NCOP" -F "NCED"
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `input_dir` | Source directory containing TV shows |
| `output_dir` | Destination for subs collection |
| `--dry-run` | Preview what would be done without extracting |
| `-v, --verbose` | Show detailed progress |
| `-D, --ignore-dir NAME` | Ignore directories with exact NAME match (case-sensitive, repeatable) |
| `-F, --ignore-file PATTERN` | Ignore files containing PATTERN (case-insensitive, repeatable) |

## Directory Structure

### Input Structure

```
/tv-shows/
├── Show A/
│   ├── Season 1/
│   │   ├── Show A - S01E01.mkv
│   │   └── Show A - S01E02.mkv
│   └── Season 2/
│       └── Show A - S02E01.mkv
└── Show B/
    └── Show B - 001.mkv
```

### Output Structure

```
/subs-output/
├── Show A/
│   ├── Season 1/
│   │   ├── Fonts/
│   │   ├── Show A - S01E01.eng.ass
│   │   └── Show A - S01E02.eng.ass
│   └── Season 2/
│       └── Show A - S02E01.eng.ass
├── Show B/
│   └── Show B - 001.eng.ass
└── _zips/
    ├── Show A.zip
    ├── Show A/
    │   ├── Season 1.zip
    │   └── Season 2.zip
    └── Show B.zip
```

## Special Features

### Orphan Cleanup

When source MKV files are deleted, corresponding subtitle files in the output are automatically removed on the next run.

### Nosubs Markers

For MKV files with no extractable subtitles (hardsubbed), a `.nosubs` marker file is created:

```
Show A - S01E03.nosubs
```

### BGPP Tagging

If a `_work.zip` file exists in the source directory, ZIP files are tagged with version information:

- `Show.zip` → `Show [BGPP].zip` (no version number found)
- `Show.zip` → `Show [BGPPv3].zip` (version 3 found in filenames)

Version numbers are extracted from filenames like: `Show - 009v3 [1080p].mkv`

### ZIP Archives

The `_zips/` directory contains:

- Individual ZIP files for each season/directory
- Parent ZIP files for each show (containing all seasons)
