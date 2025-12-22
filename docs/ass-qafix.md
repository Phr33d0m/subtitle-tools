# ass-qafix

Quality assurance and auto-fix tool for ASS subtitle files.

## Description

`ass-qafix` analyzes and fixes common issues in ASS subtitle files, with a focus on cleaning up OCR-generated subtitles. It provides comprehensive QA checks, duplicate removal, consecutive line merging, and OCR artifact detection.

## Features

- **Deduplication**: Removes duplicate dialogue lines (same Start/End/Style/Text)
- **Consecutive Merging**: Merges consecutive dialogues with identical text within 500ms gap
- **Alternating OCR Variant Merging**: Detects and merges alternating patterns (e.g., traditional/simplified Chinese)
- **Overlapping Timestamp Fixes**: Fixes overlapping timestamps between consecutive dialogues
- **OCR Artifact Removal**: Removes fake text patterns (single digits, single letters, underscores, etc.)
- **Style Validation**: Validates and normalizes Style names against defined styles
- **Empty Text Removal**: Removes lines with empty or artifact-only text (-, --, /)
- **Short Duration Removal**: Removes lines shorter than 50ms (likely OCR errors)
- **Half-Translation Detection**: Warns about files that may be only partially translated
- **Rich Output**: Beautiful table output with statistics

## Requirements

### Python Dependencies

```
rich
rapidfuzz
jieba3
pyenchant
```

### System Dependencies (Optional)

- **enchant** library for English dictionary validation

## Installation

1. Install Python dependencies:
   ```bash
   pip install rich rapidfuzz jieba3 pyenchant
   ```

2. (Optional) Install enchant for dictionary-based validation:
   ```bash
   # Arch Linux
   sudo pacman -S enchant

   # Ubuntu/Debian
   sudo apt install libenchant-2-2

   # macOS
   brew install enchant
   ```

3. Make the script executable:
   ```bash
   chmod +x ass-qafix.py
   ```

## Usage

```bash
# Process all .ass files in current directory (creates .fixed.ass files)
ass-qafix.py

# Overwrite original files
ass-qafix.py --inplace

# Process specific files
ass-qafix.py file1.ass file2.ass

# Keep empty text lines
ass-qafix.py --keep-empty-text

# Dry run (analyze without making changes)
ass-qafix.py --dry-run

# Combine options
ass-qafix.py --inplace --dry-run file1.ass
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--inplace` | Overwrite originals. Default: write *.fixed.ass |
| `--keep-empty-text` | Keep Dialogue lines with empty/artifact text |
| `--dry-run` | Analyze files and report issues without making any changes |
| `files` | Specific .ASS files to process. If not provided, processes all .ass files in current directory |

## QA Checks Performed

### Duplicate Removal
Lines with identical Start, End, Style, and Text are deduplicated.

### Consecutive Dialogue Merging
Dialogues within 500ms gap with matching text are merged into a single line spanning the entire duration.

### Alternating OCR Variant Detection
Detects patterns like:
```
Line 1: 沒本事就沒本事 (variant A)
Line 2: 没本事就没本事 (variant B)
Line 3: 沒本事就沒本事 (variant A)
```
And merges them into a single line.

### OCR Artifact Detection
Removes fake text patterns:
- Pure numbers (e.g., "1", "42")
- Single punctuation
- Underscores
- Single letters (except "I")
- Two-letter combinations that aren't valid English words
- Multi-dash patterns (e.g., "-", "--", "- -")
- Backticks
- Replacement characters (□)
- Invalid single CJK characters

### Style Validation
- Validates style names against defined styles in [V4+ Styles]
- Normalizes style case to match definition
- Falls back to "Default" for invalid styles

### Overlapping Timestamp Fixes
Fixes overlapping timestamps between consecutive dialogues when overlap is less than 0.02 seconds (2 centiseconds).

### Short Duration Removal
Removes dialogue lines with duration less than 50ms (5 centiseconds).

### Half-Translation Detection
Analyzes the last dialogue timestamp across files to detect files that may be only partially translated (e.g., stops early compared to other episodes).

## Output

The tool produces a rich table showing:

| Column | Description |
|--------|-------------|
| File Name | Name of the processed file |
| Dialogues | Number of dialogue lines |
| Fixed | Lines with field corrections |
| Style Fixes | Style name corrections |
| Empty Text Removed | Empty/artifact lines removed |
| Fake Text Removed | OCR artifact lines removed |
| Deduped | Duplicate lines removed |
| Consecutive Merged | Consecutive dialogues merged |
| Alternating Merged | Alternating patterns merged |
| Overlap Fixes | Overlapping timestamps fixed |
| Short Removed | Lines < 50ms removed |
| Warning | Half-translation warning |

## Rules Documentation

For detailed documentation of all QA checks and fixes, see **[ass-qafix/rules.md](ass-qafix/rules.md)**.
