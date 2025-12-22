# ass-credits

Detect and remove repeating sequences (openings/endings) across multiple ASS subtitle files.

## Description

`ass-credits` uses a data-driven algorithm to detect repeating content (like opening/ending credits) across multiple episode subtitle files and optionally removes them. It learns detection parameters from the actual data distribution rather than using hardcoded time windows.

## Features

- **Three-pass data-driven algorithm**:
  1. **Discovery**: Casts a wide net to find all repeating content (30% of episode length)
  2. **Cluster Analysis**: Finds where matches naturally cluster and derives tolerance from data
  3. **Boundary Detection**: Uses learned tolerance to find precise section boundaries
- Fuzzy text matching (75% similarity threshold)
- Confidence levels (HIGH, MEDIUM, REJECTED)
- Interactive cleanup or auto-clean with `--yes`
- No hardcoded time tolerances

## Requirements

### Python Dependencies

```
rapidfuzz
```

## Installation

1. Install Python dependencies:

   ```bash
   pip install rapidfuzz
   ```

2. Make the script executable:

   ```bash
   chmod +x ass-credits.py
   ```

## Usage

```bash
# Navigate to directory with multiple .ass files
cd /path/to/subtitles

# Analyze and interactively clean
ass-credits.py

# Auto-clean HIGH confidence detections only
ass-credits.py --yes
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-y, --yes` | Auto-clean HIGH confidence detections only (skip MEDIUM/REJECTED) |

## How It Works

### Pass 1: Discovery

- Scans the last 30% of each episode for text that appears in 50%+ of files
- Uses fuzzy matching (RapidFuzz) with 75% similarity threshold
- Collects all potential credits content without filtering by time

### Pass 2: Cluster Analysis

- Groups matches by their position relative to episode end
- Derives bin width from the data itself (2x median gap, minimum 5 seconds)
- Identifies the most consistent cluster across files
- Calculates derived tolerance = 2x the cluster spread (IQR)

### Pass 3: Boundary Detection

- Uses learned tolerance to find precise credits boundaries
- Verifies matches appear in minimum required files
- Reports confidence based on cluster consistency

## Confidence Levels

| Level | Criteria | Action |
|-------|----------|--------|
| HIGH | 80%+ files agree on cluster position | Auto-cleaned with `--yes` |
| MEDIUM | 50-79% files agree | Requires confirmation |
| REJECTED | Outside learned tolerance | Not cleaned |

## Output

```
Loading 12 subtitle files...
Analyzing 12 files for credits sections...

  Pass 1: Discovering repeating content... found 15 candidates
  Pass 2: Analyzing clusters... cluster at ~87 sec from end
           spread: 3 sec, derived tolerance: 10 sec
           consensus boundary: "翻译: xxx"
  Pass 3: Detecting boundaries...

Results:
  HIGH confidence: 10 files
  MEDIUM confidence: 1 files
  REJECTED: 1 files

HIGH confidence detections (will be cleaned with --yes):

Episode01.ass [HIGH]
  CREDITS: 0:21:33.00 → end (15 lines)
    Start: "翻译: xxx"
    10/12 files agree, boundary match: 100%
```

## Requirements for Detection

- **Minimum 2 files**: At least 2 .ass files are required in the current directory
- **50% match ratio**: Text must appear in at least 50% of files to be considered repeating
- **30% cluster density**: Cluster must have matches from at least 30% of files to be valid

## Limitations

- Only detects credits at the END of episodes (not openings at the start)
- Requires multiple files with similar content structure
- Text-based detection may miss purely styled credits without dialogue
