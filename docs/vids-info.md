# vids-info

Display video file information in a formatted table.

## Description

`vids-info` scans the current directory for video files (.mkv, .mp4) and displays their metadata (duration, resolution, FPS) in a formatted table using Rich.

## Features

- Displays duration, resolution, and FPS for all videos
- Optional sorting by duration
- Rich table output
- Handles missing or invalid metadata gracefully

## Requirements

### System Dependencies

- **ffprobe** (from FFmpeg) - for reading video metadata

### Python Dependencies

```
rich
```

## Installation

1. Install FFmpeg:

   ```bash
   # Arch Linux
   sudo pacman -S ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # macOS
   brew install ffmpeg
   ```

2. Install Python dependencies:

   ```bash
   pip install rich
   ```

3. Make the script executable:

   ```bash
   chmod +x vids-info.py
   ```

## Usage

```bash
# Display info for all videos in current directory
vids-info.py

# Sort by duration (longest first)
vids-info.py -s
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-s, --sort` | Sort by length (descending) |

## Output

```
                        Video Files in Current Directory
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Filename                               Length     Resolution      FPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Movie 2024 [1080p].mkv                24min30sec  1920x1080      23.98
Episode 01.mkv                        23min45sec  1920x1080      29.97
Episode 02.mp4                        23min50sec  1280x720       25.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Displayed Information

| Column | Description |
|--------|-------------|
| Filename | Name of the video file |
| Length | Duration in `XminYsec` format |
| Resolution | Width x Height in pixels |
| FPS | Frames per second (from avg_frame_rate) |

## Supported Formats

- `.mkv` (Matroska)
- `.mp4` (MPEG-4)

Both uppercase and lowercase extensions are supported.

## Notes

- Files that cannot be probed display "?" for unavailable fields
- FPS is calculated from the first video stream's `avg_frame_rate`
- Duration is rounded to the nearest second
