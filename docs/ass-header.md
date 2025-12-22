# ass-header

Replace ASS file headers across multiple files.

## Description

`ass-header` replaces the [Script Info] and [V4+ Styles] sections of all .ass files in the current directory with content from a template header file. This is useful for standardizing styles across multiple subtitle files.

## Features

- Batch replacement of headers across all .ass files
- Preserves the [Events] section and all dialogue lines
- Handles UTF-8 BOM encoding
- Simple and fast operation

## Requirements

### Python Dependencies

None (uses only standard library).

## Installation

Make the script executable:

```bash
chmod +x ass-header.py
```

## Usage

```bash
# Replace headers in all .ass files in current directory
ass-header.py template_header.txt
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `header_path` | Path to a text file containing the desired ASS header (Script Info + V4+ Styles) |

## Header Template Format

The header file should contain the [Script Info] and [V4+ Styles] sections:

```ini
[Script Info]
Title: My Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,60,60,50,1
Style: Signs,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,8,10,10,10,1
```

## How It Works

1. Reads the template header file
2. For each .ass file in the current directory:
   - Finds the [Events] section
   - Replaces everything before [Events] with the template header
   - Adds exactly one blank line between header and [Events]
   - Writes the modified content back to the file

## Example

### Before

```ini
[Script Info]
Title: Old Title
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, ...
Style: Default,Times New Roman,60,...

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,Hello World
```

### After (with new template)

```ini
[Script Info]
Title: New Title
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, ...
Style: Default,Arial,72,...

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,Hello World
```

## Notes

- Files without an [Events] section are skipped
- The script processes only files with `.ass` extension (case-insensitive)
- Output encoding is UTF-8 with BOM
