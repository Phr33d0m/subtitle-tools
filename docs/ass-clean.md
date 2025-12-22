# ass-clean

Find and remove dialogue lines from ASS files based on regex patterns.

## Description

`ass-clean` uses grep to find dialogue lines matching a pattern and removes them along with related lines (either before or after the match). It's useful for removing opening/ending credits, disclaimers, or other recurring content.

## Features

- Regex-based pattern matching using `egrep`
- Two modes: remove lines BEFORE or AFTER the match
- Processes multiple files (single file, directory, or recursive)
- Dry-run mode for preview
- Removes the matched line plus all Dialogue lines in the specified direction

## Requirements

### System Dependencies

- **egrep** (standard on Linux/macOS)

### Python Dependencies

None (uses only standard library).

## Installation

Make the script executable:

```bash
chmod +x ass-clean.py
```

## Usage

```bash
# Remove matched line and all Dialogue lines BEFORE it
ass-clean.py --before 'Dialogue.*Credits Start'

# Remove matched line and all Dialogue lines AFTER it
ass-clean.py --after 'Dialogue.*Credits Start'

# Process a specific file
ass-clean.py --after 'Dialogue.*THE END' episode.ass

# Process a directory
ass-clean.py --after 'Dialogue.*Ending' /path/to/subtitles/

# Preview changes without modifying files
ass-clean.py --after 'pattern' --dry-run
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--before` | Remove the matched line and all preceding Dialogue lines |
| `--after` | Remove the matched line and all following Dialogue lines |
| `pattern` | egrep regex pattern to search for (e.g., 'Dialogue.*Credits') |
| `target_path` | File or directory to search (default: current directory) |
| `--dry-run` | Show which lines would be removed, without changing files |

## How It Works

1. **Search**: Uses `egrep` to find lines matching the pattern
2. **Identify**: Records the first matching line number in each file
3. **Remove**: Based on mode:
   - `--before`: Removes the match and all Dialogue lines before it
   - `--after`: Removes the match and all Dialogue lines after it

## Examples

### Remove Opening Credits

```bash
# Pattern matches the start of opening credits
ass-clean.py --before 'Dialogue.*0:01:30.*Opening Theme'
```

### Remove Ending Credits

```bash
# Pattern matches the start of ending credits
ass-clean.py --after 'Dialogue.*0:22:00.*Translation:'
```

### Remove Specific Recurring Line

```bash
# Find and remove a specific disclaimer
ass-clean.py --after 'Dialogue.*Please support the official release'
```

### Preview Mode

```bash
# See what would be removed without making changes
ass-clean.py --after 'Dialogue.*THE END' --dry-run
```

Output:

```
- [DRY RUN] episode01.ass will remove:
  - Dialogue: 0,0:22:15.00,0:22:18.00,Default,,0,0,0,,THE END
  - Dialogue: 0,0:22:20.00,0:22:25.00,Default,,0,0,0,,Credits line 1
  - Dialogue: 0,0:22:25.00,0:22:30.00,Default,,0,0,0,,Credits line 2
```

## Pattern Tips

- Use `Dialogue.*` prefix to match only dialogue lines
- Include timestamp patterns for precision: `Dialogue.*0:22:`
- Escape special regex characters: `\.`, `\(`, etc.
- Use `.*` for flexible matching between parts

## Notes

- Only the FIRST match in each file is used as the cutoff point
- Non-Dialogue lines (Format, Comments, etc.) are NOT removed
- The matched line itself is always removed
