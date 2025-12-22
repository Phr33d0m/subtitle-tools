# ass-compare

Compare timestamps between Chinese and English ASS subtitle files.

## Description

`ass-compare` compares dialogue timestamps between paired Chinese (.ass) and English (.eng.ass) subtitle files. It detects mismatches, identifies merged/split lines, and reports any discrepancies.

## Features

- Compares timestamps between language pairs
- Detects merged lines (e.g., 2 CHI lines → 1 ENG line)
- Detects split lines (e.g., 1 CHI line → 2 ENG lines)
- Adjusts line count for legitimate merges
- Color-coded output (optional)
- Returns appropriate exit code for scripting

## Requirements

### Python Dependencies

None (uses only standard library).

## Installation

Make the script executable:

```bash
chmod +x ass-compare.py
```

## Usage

```bash
# Compare files in current directory
ass-compare.py

# Specify directories for each language
ass-compare.py -c /path/to/chinese -e /path/to/english

# Disable colored output
ass-compare.py --no-color
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-c, --chi DIR` | Directory containing Chinese (.ass) files (default: current directory) |
| `-e, --eng DIR` | Directory containing English (.eng.ass) files (default: current directory) |
| `-nc, --no-color` | Disable colored output |

## File Naming Convention

The tool expects files to be named as:

- Chinese: `basename.ass`
- English: `basename.eng.ass`

Example:

```
Episode01.ass       # Chinese
Episode01.eng.ass   # English
```

## Output

### No Errors

```
OK
```

Exit code: 0

### Errors Found

```
Episode01
  - Line count mismatch: CHI has 150, ENG has 148
  - CHI-only: 0:15:30.00 - 0:15:32.00
  - ENG-only: 0:20:15.00 - 0:20:18.00

Episode03
  - Missing CHI file
```

Exit code: 1

## Merge Detection

The tool intelligently detects line merges:

### ENG Merge (2 CHI → 1 ENG)

When an English line spans the exact time range of multiple Chinese lines:

```
CHI: 0:01:00.00 - 0:01:02.00  "Line 1"
CHI: 0:01:02.00 - 0:01:04.00  "Line 2"
ENG: 0:01:00.00 - 0:01:04.00  "Line 1 Line 2"
```

This is detected and not reported as an error.

### CHI Merge (2 ENG → 1 CHI)

Similarly, Chinese lines spanning multiple English lines are detected.

## Use Cases

- QA check before muxing bilingual releases
- Verify translation completeness
- Detect timing synchronization issues
- Automated CI/CD pipeline checks
