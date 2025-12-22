# Subtitle and MKV Processing Tools

A collection of highly opinionated Python scripts for parallel processing video files, extracting subtitles, managing attachments, and performing OCR on hardcoded subtitles. These tools are designed to work with MKV containers and various subtitle formats.

## Tools Overview

### Core Subtitle Processing

| Tool | Description | Documentation |
|------|-------------|---------------|
| [sub-merge](docs/sub-merge.md) | Merge subtitle files into video containers with language metadata and fonts | [docs/sub-merge.md](docs/sub-merge.md) |
| [sub-extract](docs/sub-extract.md) | Extract all subtitle tracks from MKV files with intelligent naming | [docs/sub-extract.md](docs/sub-extract.md) |
| [sub-attachment-extract](docs/sub-attachment-extract.md) | Extract attachments from MKV files into organized directories | [docs/sub-attachment-extract.md](docs/sub-attachment-extract.md) |
| [sub-time-fix](docs/sub-time-fix.md) | Shift ASS subtitle timestamps by milliseconds | [docs/sub-time-fix.md](docs/sub-time-fix.md) |

### ASS Subtitle Utilities

| Tool | Description | Documentation |
|------|-------------|---------------|
| [ass-qafix](docs/ass-qafix.md) | Quality assurance and auto-fix for OCR-generated ASS files | [docs/ass-qafix.md](docs/ass-qafix.md) |
| [ass-credits](docs/ass-credits.md) | Detect and remove repeating sequences (openings/endings) | [docs/ass-credits.md](docs/ass-credits.md) |
| [ass-header](docs/ass-header.md) | Replace ASS file headers across multiple files | [docs/ass-header.md](docs/ass-header.md) |
| [ass-compare](docs/ass-compare.md) | Compare timestamps between Chinese and English ASS files | [docs/ass-compare.md](docs/ass-compare.md) |
| [ass-clean](docs/ass-clean.md) | Find and remove dialogue lines based on regex patterns | [docs/ass-clean.md](docs/ass-clean.md) |

### Video OCR & Analysis

| Tool | Description | Documentation |
|------|-------------|---------------|
| [ocrp](docs/ocrp.md) | Video OCR processing wrapper for VideOCR with parallel processing | [docs/ocrp.md](docs/ocrp.md) |
| [sub-visualize](docs/sub-visualize.md) | Estimate brightness thresholds for OCR subtitle extraction | [docs/sub-visualize.md](docs/sub-visualize.md) |

### Collection Management

| Tool | Description | Documentation |
|------|-------------|---------------|
| [subs-collection](docs/subs-collection.md) | Build mirrored directory structures with subtitles and attachments | [docs/subs-collection.md](docs/subs-collection.md) |
| [vids-info](docs/vids-info.md) | Display video file information in a formatted table | [docs/vids-info.md](docs/vids-info.md) |

## Quick Start

### Requirements

- **Python 3.8+** (tested with Python 3.13)
- **MKVToolNix** - Required for most tools (mkvmerge, mkvextract)
- **FFmpeg/FFprobe** - Required for vids-info and sub-visualize

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Phr33d0m/subtitle-tools.git
   cd subtitle-tools
   ```

2. Install Python dependencies:
   ```bash
   pip install rich rapidfuzz jieba3 pyenchant opencv-python numpy
   ```

3. Install MKVToolNix:
   ```bash
   # Arch Linux
   sudo pacman -S mkvtoolnix-cli

   # Ubuntu/Debian
   sudo apt install mkvtoolnix

   # Fedora/CentOS
   sudo dnf install mkvtoolnix

   # macOS
   brew install mkvtoolnix
   ```

4. Make scripts executable:
   ```bash
   chmod +x *.py
   ```

5. (Optional) Add to PATH or create symlinks:
   ```bash
   ln -s /path/to/subtitle-tools/sub-merge.py ~/.local/bin/sub-merge
   ```

### Python Dependencies by Tool

Not all tools require all dependencies. Here's what each tool needs:

| Tool | Dependencies |
|------|--------------|
| sub-merge | rich |
| sub-extract | rich |
| sub-attachment-extract | (none) |
| sub-time-fix | (none) |
| ass-qafix | rich, rapidfuzz, jieba3, pyenchant |
| ass-credits | rapidfuzz |
| ass-header | (none) |
| ass-compare | (none) |
| ass-clean | (none) |
| ocrp | rich |
| sub-visualize | opencv-python, numpy |
| subs-collection | rich |
| vids-info | rich |

## File Naming Conventions

### Subtitle Files

Format: `VideoName.LanguageCode.extension`

Examples:
- `Movie.eng.srt` - English SRT subtitles
- `Movie.zh-Hans.ass` - Chinese Simplified ASS subtitles
- `Movie.pt-BR.srt` - Brazilian Portuguese SRT subtitles

**Supported Language Codes:**
- IETF tags (preferred): `zh-Hans`, `zh-Hant`, `pt-BR`, `en-US`
- 3-letter codes: `eng`, `chi`, `por`, `fre`

### Font Directory

Place fonts in a `Fonts/` subdirectory for automatic embedding with sub-merge:

```
Videos/
├── Movie.mp4
├── Movie.eng.srt
└── Fonts/
    ├── OpenSans-Regular.ttf
    └── NotoSansSC-Regular.otf
```

## License

This project is released under the MIT License.

## Contributing

Contributions are welcome, support is not offered. Please feel free to send pull requests.
