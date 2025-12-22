# sub-time-fix

Shift all ASS subtitle timestamps by a given number of milliseconds.

## Description

`sub-time-fix` adjusts timestamps in ASS subtitle files by shifting them forward or backward. It handles both Dialogue and Comment lines, respects the Format mapping in the [Events] section, and supports recursive directory processing.

## Features

- Shift timestamps forward (positive values) or backward (negative values)
- Process single files or entire directories recursively
- Handles multiple [Events] blocks
- Symmetric rounding for centisecond precision
- Automatic encoding detection (UTF-8-BOM, UTF-8, CP1252, Latin-1)
- Clamps negative results to zero (prevents invalid timestamps)

## Requirements

### Python Dependencies

None (uses only standard library).

## Installation

Make the script executable:

```bash
chmod +x sub-time-fix.py
```

## Usage

```bash
# Shift all .ass files in current directory forward by 6032ms
sub-time-fix.py -t 6032

# Shift a single file backward by 6032ms
sub-time-fix.py -t -6032 myfile.ass

# Shift all .ass files in a directory recursively
sub-time-fix.py -t 6032 ./folder
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-t, --time MS` | Time shift in milliseconds (required). Positive = forward, negative = backward |
| `path` | Optional path to a .ass file or directory (default: current directory) |

## How It Works

1. **Milliseconds to Centiseconds**: ASS files use centisecond precision (H:MM:SS.cc). The tool converts milliseconds to centiseconds with symmetric rounding:
   - `6032 ms` → `603 cs`
   - `-6032 ms` → `-603 cs`

2. **Format Awareness**: Respects the Format line in [Events] to correctly identify Start and End column positions.

3. **Timestamp Shifting**: Adds the delta to both Start and End timestamps for all Dialogue and Comment lines.

4. **Clamping**: Results below zero are clamped to `0:00:00.00`.

## Examples

### Shift Forward

```bash
# Delay subtitles by 5 seconds
sub-time-fix.py -t 5000
```

### Shift Backward

```bash
# Advance subtitles by 2.5 seconds
sub-time-fix.py -t -2500
```

### Process Directory

```bash
# Recursively process all .ass files in a folder
sub-time-fix.py -t 3000 ./subtitles/
```

## Output

The tool reports:

- Number of files processed
- Lines changed per file
- Timestamps updated per file
- Total summary with direction (forward/backward)

```
[OK] episode01.ass: lines changed=150, timestamps updated=300
[OK] episode02.ass: lines changed=148, timestamps updated=296

Processed 2 file(s). Shifted 5000 ms forward. Lines changed: 298. Timestamps updated: 596.
```
