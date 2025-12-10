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
    - [subtimefix.py - Subtitle Timestamp Shifting](#subtimefixpy---subtitle-timestamp-shifting)
    - [ass\_qafix.py - ASS Quality Assurance and Auto-Fixer](#ass_qafixpy---ass-quality-assurance-and-auto-fixer)
    - [ass-header.py - ASS Header Replacement](#ass-headerpy---ass-header-replacement)
    - [ass-credits.py - Opening/Ending Detection and Removal](#ass-creditspy---openingending-detection-and-removal)
    - [ass-compare.py - ASS Timestamp Comparison](#ass-comparepy---ass-timestamp-comparison)
    - [ass-clean.py - ASS File Issue Detection](#ass-cleanpy---ass-file-issue-detection)
    - [sub-visualize.py - Brightness Threshold Estimation](#sub-visualizepy---brightness-threshold-estimation)
    - [subs-collection.py - Subtitle Collection Builder](#subs-collectionpy---subtitle-collection-builder)
    - [vids-info.py - Video Information Display](#vids-infopy---video-information-display)
  - [File Naming Conventions](#file-naming-conventions)
    - [Video Files](#video-files)
    - [Subtitle Files](#subtitle-files)
    - [Font Directory](#font-directory)
  - [License](#license)
  - [Contributing](#contributing)

## Requirements

- **Python 3.8+** (tested with Python 3.13, should work with prior versions)
- **MKVToolNix** - Required for mkvmerge and mkvextract commands
- **VideOCR** - Required for OCR processing (only for ocrp.py)
- **FFmpeg/FFprobe** - Required for vids-info.py and sub-visualize.py

**Python Dependencies:**

```bash
pip install rich rapidfuzz jieba3 pyenchant opencv-python numpy
```

- `rich` - Rich text formatting and progress displays
- `rapidfuzz` - Fuzzy string matching for OCR variants
- `jieba3` - Chinese word segmentation (for single character validation)
- `pyenchant` - English dictionary (for short word validation)
- `opencv-python` - Image processing (for sub-visualize.py)
- `numpy` - Numerical operations (for sub-visualize.py)

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
cd subtitle-tools
```

2. Make the scripts executable:

```bash
chmod +x *.py
```

3. (Optional) Add to your PATH for easier access:

```bash
export PATH="$(pwd):$PATH"
```

OR, symlink what you need to somewhere in your PATH:

```bash
ln -s /path/to/subtitle-tools/submerge.py /usr/local/bin/submerge
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

### subtimefix.py - Subtitle Timestamp Shifting

Shifts all timestamps in ASS subtitle files by a specified number of milliseconds with support for recursive directory processing.

**Features:**

- Supports both Dialogue: and Comment: timestamps
- Respects the Format: mapping inside [Events] sections
- Handles multiple [Events] blocks in a single file
- Symmetric rounding to centisecond precision (ASS accuracy)
- Clamps timestamps below zero to prevent negative times
- Multiple encoding support (UTF-8-sig, UTF-8, CP1252, Latin-1 fallback)
- Recursive processing of directories containing .ass files

**Usage:**

```bash
# Shift timestamps forward by 6032 milliseconds
python3 subtimefix.py -t '6032'

# Shift timestamps backward by 6032 milliseconds
python3 subtimefix.py -t '-6032'

# Process specific file
python3 subtimefix.py -t '6032' myfile.ass

# Process all .ass files in directory recursively
python3 subtimefix.py -t '6032' ./folder
```

**Arguments:**

- `-t, --time`: Time shift in milliseconds (required). Positive values move timestamps forward, negative values move them backward.
- `path`: Optional path to a .ass file or directory (default: current directory). If a directory is provided, processes all .ass files recursively.

### ass_qafix.py - ASS Quality Assurance and Auto-Fixer

Analyzes and automatically fixes common quality issues in ASS subtitle files. Designed for OCR-generated subtitles with comprehensive artifact detection.

**Features:**

- Removes duplicate dialogue lines
- Merges consecutive dialogues with identical text (within 500ms gap)
- Merges alternating OCR variant patterns (traditional/simplified Chinese)
- Fixes overlapping timestamps between consecutive dialogues
- Removes OCR artifacts (fake text, single digits, invalid characters)
- Validates and normalizes style names against defined styles
- Dictionary-based validation for single Chinese characters (jieba3) and short English words (enchant)
- Rich table output with detailed per-file statistics

**Usage:**

```bash
# Process all .ass files in current directory (creates .fixed.ass files)
python3 ass_qafix.py

# Process specific files
python3 ass_qafix.py episode01.ass episode02.ass

# Overwrite original files
python3 ass_qafix.py --inplace

# Preview changes without modifying files
python3 ass_qafix.py --dry-run

# Keep empty text lines (normally removed)
python3 ass_qafix.py --keep-empty-text
```

**Arguments:**

- `files`: Specific .ASS files to process (default: all .ass files in current directory)
- `--inplace`: Overwrite originals instead of creating .fixed.ass files
- `--keep-empty-text`: Keep dialogue lines with empty/artifact text
- `--dry-run`: Analyze and report without making changes

See `ass_qafix.rules.txt` for detailed documentation of all checks and fixes.

### ass-header.py - ASS Header Replacement

Replaces the header section (Script Info and V4+ Styles) of ASS files with a template header while preserving the Events section.

**Features:**

- Batch processing of all .ass files in current directory
- Preserves all dialogue and event data
- Ensures consistent styling across multiple files

**Usage:**

```bash
# Replace headers in all .ass files using template
python3 ass-header.py template_header.ass
```

**Arguments:**

- `header_path`: Path to template file containing desired ASS header (Script Info + V4+ Styles)

### ass-credits.py - Opening/Ending Detection and Removal

Detects and removes repeating sequences (openings/endings) across multiple ASS subtitle files using a data-driven algorithm.

**Features:**

- Three-pass algorithm: Discovery, Cluster Analysis, Boundary Detection
- Automatically learns time tolerances from data distribution
- Fuzzy text matching for OCR variants (75% similarity threshold)
- Requires content to appear in 50%+ of files to be considered "repeating"

**Usage:**

```bash
# Analyze files for repeating sequences
python3 ass-credits.py *.ass

# Remove detected credits (modifies files)
python3 ass-credits.py --remove *.ass
```

### ass-compare.py - ASS Timestamp Comparison

Compares timestamps between ASS files to identify merged or split dialogue lines.

**Features:**

- Detects single timestamps that span multiple timestamps in another file
- Color-coded output for easy identification
- Useful for comparing OCR results with reference subtitles

**Usage:**

```bash
# Compare two ASS files
python3 ass-compare.py file1.ass file2.ass
```

### ass-clean.py - ASS File Issue Detection

Finds ASS files with specific issues using regex pattern matching. Can remove dialogue lines before or after matched patterns.

**Features:**

- Regex-based pattern search across files
- Remove dialogue lines before or after matches
- Recursive directory processing
- Dry-run mode for preview

**Usage:**

```bash
# Find files matching a pattern
python3 ass-clean.py "pattern" /path/to/files

# Remove lines before the match
python3 ass-clean.py --mode before "Opening Song" /path/to/files

# Remove lines after the match
python3 ass-clean.py --mode after "Ending Credits" /path/to/files

# Preview without changes
python3 ass-clean.py --dry-run --mode before "pattern" /path/to/files
```

### sub-visualize.py - Brightness Threshold Estimation

Estimates optimal videocr brightness threshold for subtitle OCR and generates preview images for visual comparison.

**Features:**

- Uses Otsu's method on min-channel for threshold estimation
- Generates preview images for a range of threshold values
- Helps tune OCR parameters for different video sources

**Usage:**

```bash
# Suggest brightness and generate previews
python3 sub-visualize.py screenshot.png

# Only print suggested value
python3 sub-visualize.py screenshot.png --no-visualize

# Custom span for preview range
python3 sub-visualize.py screenshot.png --span 8

# Custom base brightness
python3 sub-visualize.py screenshot.png -b 130

# Output to specific directory
python3 sub-visualize.py screenshot.png --output-dir previews/
```

### subs-collection.py - Subtitle Collection Builder

Builds a mirrored directory structure containing only subtitles and attachments extracted from MKV files.

**Features:**

- Extracts subtitles and attachments from MKV files
- Creates mirrored directory structure
- Removes directories with only hardsubbed content (no extractable subs)
- Rich progress display and summary statistics
- Optional ZIP creation for extracted content

**Usage:**

```bash
# Build subtitle collection
python3 subs-collection.py /path/to/videos /path/to/output

# Preview without changes
python3 subs-collection.py /path/to/videos /path/to/output --dry-run

# Verbose output
python3 subs-collection.py /path/to/videos /path/to/output --verbose
```

### vids-info.py - Video Information Display

Displays video file information in a formatted table using ffprobe.

**Features:**

- Shows duration, resolution, and frame rate
- Rich table output
- Batch processing of multiple files

**Usage:**

```bash
# Show info for all videos in current directory
python3 vids-info.py

# Show info for specific files
python3 vids-info.py video1.mp4 video2.mkv

# Show info for directory
python3 vids-info.py /path/to/videos
```

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
