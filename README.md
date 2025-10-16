# Subtitle and MKV Processing Tools

A collection of highly opinionated Python scripts for parallel processing video files, extracting subtitles, managing attachments, and performing OCR on hardcoded subtitles. These tools are designed to work with MKV containers and various subtitle formats.

## Table of Contents

- [Subtitle and MKV Processing Tools](#subtitle-and-mkv-processing-tools)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
    - [Installing External Dependencies](#installing-external-dependencies)
  - [Installation](#installation)
  - [Tools](#tools)
    - [ocrp.py - Video OCR Processing](#ocrppy---video-ocr-processing)
    - [submerge.py - Subtitle Merging](#submergepy---subtitle-merging)
    - [subextract.py - Subtitle Extraction](#subextractpy---subtitle-extraction)
    - [subattachextract.py - Attachment Extraction](#subattachextractpy---attachment-extraction)
  - [File Naming Conventions](#file-naming-conventions)
    - [Video Files](#video-files)
    - [Subtitle Files](#subtitle-files)
    - [Font Directory](#font-directory)
  - [License](#license)
  - [Contributing](#contributing)

## Requirements

- **Python 3.8+** (tested with Python 3.13, should work with prior versions)
- **MKVToolNix** - Required for mkvmerge and mkvextract commands
- **VideOCR CLI** - Required for OCR processing (only for ocrp.py)

### Installing External Dependencies

**On Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install mkvtoolnix
```

**On Fedora/CentOS:**

```bash
sudo dnf install mkvtoolnix
```

**On macOS (using Homebrew):**

```bash
brew install mkvtoolnix
```

**VideOCR CLI:**

- Download from [VideOCR Releases](https://github.com/timminator/VideOCR/releases)
- Update the `BINARY_PATH` constant in `ocrp.py` to point to your videocr-cli binary

## Installation

1. Clone this repository:

```bash
git clone https://github.com/Phr33d0m/subtitle-tools.git
cd subs-tools
```

2. Make the scripts executable:

```bash
chmod +x *.py
```

3. (Optional) Add to your PATH for easier access:

```bash
export PATH="$(pwd):$PATH"
```

## Tools

### ocrp.py - Video OCR Processing

**Note:** This script is a wrapper around the [VideOCR CLI tool](https://github.com/timminator/VideOCR). The CLI tool must be installed on your system and the `BINARY_PATH` constant inside `ocrp.py` must be updated to point to your videocr-cli binary.

Transforms video files with hardcoded subtitles into SRT subtitle files using VideOCR CLI with parallel processing support.

**Features:**

- Parallel processing of multiple video files
- Configurable OCR parameters and crop regions
- GPU acceleration support
- Progress tracking and detailed logging

**Usage:**

```bash
# Basic usage with crop region
python3 ocrp.py --crops '1156,1383,1546,178'

# Process single video with custom settings
python3 ocrp.py --crops '1156,1383,1546,178' video.mp4

# Start from specific time with custom brightness
python3 ocrp.py --crops '1156,1383,1546,178' -ts '02:30' -b 180

# Use 4 parallel workers
python3 ocrp.py --crops '1156,1383,1546,178' --max 4
```

**Arguments:**

- `--crops`: Crop region as "x,y,width,height" (required). 
  - You can obtain these values by using the [VideOCR GUI](https://github.com/timminator/VideOCR) - select a single video file, then select the subtitle area and copy the crop values from there. Crop values rarely change between episodes of the same series so it's safe to use the same crop values for multiple episodes.
- `-ts, --time-start`: Start time for OCR (default: 01:50)
- `-b, --brightness`: Brightness threshold (default: 165)
- `--max`: Maximum parallel workers (default: auto-detect)
- `-v, --verbose`: Enable verbose output
- `-q, --quiet`: Suppress non-error output

### submerge.py - Subtitle Merging

Merges subtitle files into video containers using mkvmerge with proper language metadata and font attachments.

**Features:**

- Automatic matching of video and subtitle files
- Support for IETF language tags (zh-Hans, pt-BR) and 3-letter codes (eng, chi)
- Priority system: ASS subtitles > SRT subtitles
- Optional font embedding for ASS subtitles
- Parallel processing support

**File Naming Convention:**

- Video: `Movie.mp4`
- Subtitles: `Movie.eng.srt`, `Movie.zh-Hans.ass`, etc.
- Fonts directory: `Fonts/` (optional)

**Usage:**

```bash
# Process current directory
python3 submerge.py

# Process specific directory
python3 submerge.py /path/to/videos

# Use 4 parallel workers
python3 submerge.py -p 4

# Preview operations without executing
python3 submerge.py --dry-run

# Verbose output
python3 submerge.py -v
```

**Arguments:**

- `path`: Directory containing video files (default: current directory)
- `-p, --parallel`: Number of parallel workers (default: 1)
- `--dry-run`: Preview operations without executing
- `-v, --verbose`: Enable verbose logging

### subextract.py - Subtitle Extraction

Extracts all subtitle tracks from MKV files using mkvextract with intelligent naming and parallel processing.

**Features:**

- Extracts all subtitle tracks from MKV files
- Intelligent language code handling (IETF tags and 3-letter codes)
- Automatic file naming to avoid conflicts
- Parallel processing support
- Supports all subtitle formats (SRT, ASS, SSA, VOB, PGS)

**Usage:**

```bash
# Process all MKVs in current directory
python3 subextract.py

# Process specific directory
python3 subextract.py /path/to/mkv/files

# Process single MKV file
python3 subextract.py video.mkv

# Use 4 parallel workers
python3 subextract.py -p 4 /path/to/mkv/files
```

**Arguments:**

- `path`: Directory containing MKVs, single MKV file, or omitted for current directory
- `-p, --parallel`: Number of parallel workers (default: 1)

**Output Naming:**

- `video.zh-Hans.srt` - Chinese Simplified subtitles
- `video.eng.ass` - English ASS subtitles
- `video.en.default-2.srt` - Second English track when multiple exist

### subattachextract.py - Attachment Extraction

Extracts attachments from MKV files and organizes them into Covers/Fonts/Others directories with parallel processing.

**Features:**

- Categorizes attachments by MIME type and filename
- Organizes files into appropriate directories
- Duplicate file detection and skipping
- Parallel processing for batch operations
- Cross-platform filename sanitization

**Directory Structure:**

```
output/
├── Covers/     # Images and cover art
├── Fonts/      # Font files (TTF, OTF, WOFF, etc.)
└── Others/     # All other attachments
```

**Usage:**

```bash
# Process current directory
python3 subattachextract.py

# Process specific MKV file
python3 subattachextract.py video.mkv

# Process directory containing MKVs
python3 subattachextract.py /path/to/mkv/files

# Preview operations
python3 subattachextract.py --dry-run

# Quiet mode with 8 workers
python3 subattachextract.py -q -p 8
```

**Arguments:**

- `path`: MKV file, directory containing MKVs, or current directory if omitted
- `--dry-run`: Show what would be extracted without actually extracting files
- `-q, --quiet`: Suppress verbose output
- `-p, --parallel`: Number of parallel workers (default: 4)

## File Naming Conventions

### Video Files

Supported extensions: `.mp4` , `.mkv` (case-insensitive)

### Subtitle Files

Format: `BaseName.LanguageCode.extension`

**Examples:**

- `Movie.eng.srt` - English SRT subtitles
- `Movie.zh-Hans.ass` - Chinese Simplified ASS subtitles
- `Movie.pt-BR.srt` - Brazilian Portuguese SRT subtitles

**Language Codes:**

- **IETF tags preferred:** `zh-Hans`, `zh-Hant`, `pt-BR`, `en-US`
- **3-letter codes supported:** `eng`, `chi`, `por`, `fre`

### Font Directory

Place fonts in a `Fonts/` subdirectory for automatic embedding:

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
