# ocrp

Video OCR processing wrapper for VideOCR CLI.

## Description

`ocrp` is a parallel processing wrapper for VideOCR that transforms video files into SRT subtitles using OCR. It provides a rich progress display and supports batch processing of multiple video files.

## Features

- Parallel processing with configurable worker count
- Rich progress display with real-time status
- Configurable crop region for subtitle extraction
- Brightness threshold adjustment
- Time range selection for partial processing
- Dry-run mode for command preview
- GPU acceleration support

## Requirements

### System Dependencies

- **VideOCR CLI** - The VideOCR Python tool (configured via `BINARY_PATH` in the script)
- **PaddleOCR** - Required by VideOCR for OCR processing

### Python Dependencies

```
rich
```

## Installation

1. Install VideOCR and its dependencies (PaddleOCR):

   ```bash
   # Clone VideOCR repository
   git clone https://github.com/devmaxxing/videocr-PaddleOCR.git

   # Install PaddleOCR and dependencies
   pip install paddlepaddle paddleocr
   ```

2. Install Python dependencies:

   ```bash
   pip install rich
   ```

3. Configure the script:
   Edit `ocrp.py` and set `BINARY_PATH` to point to your VideOCR installation:

   ```python
   BINARY_PATH = Path("/path/to/videocr.py")
   ```

4. Make the script executable:

   ```bash
   chmod +x ocrp.py
   ```

## Usage

```bash
# Process all videos in current directory with crop region
ocrp.py --crops '1156,1383,1546,178'

# Process a single video
ocrp.py --crops '1156,1383,1546,178' video.mp4

# Start from a specific time
ocrp.py --crops '1156,1383,1546,178' -ts '02:30'

# Set end time
ocrp.py --crops '1156,1383,1546,178' -te '45:00'

# Custom brightness threshold
ocrp.py --crops '1156,1383,1546,178' -b 180

# Use 4 parallel workers
ocrp.py --crops '1156,1383,1546,178' --max 4

# Preview commands without executing
ocrp.py --crops '1156,1383,1546,178' --dry-run

# Verbose output
ocrp.py --crops '1156,1383,1546,178' -v

# Quiet mode
ocrp.py --crops '1156,1383,1546,178' -q
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--crops X,Y,W,H` | **Required.** Crop region as "x,y,width,height" |
| `-ts, --time-start` | Start time for OCR (e.g., "02:30") |
| `-te, --time-end` | End time for OCR (e.g., "45:00") |
| `-b, --brightness` | Brightness threshold (default: 145) |
| `--max N` | Maximum parallel workers (default: auto-detect) |
| `-v, --verbose` | Enable verbose output |
| `-q, --quiet` | Suppress non-error output |
| `--dry-run` | Show commands that would be executed without running them |
| `files` | Video files to process (default: all videos in current directory) |

## Crop Region

The crop region (`--crops`) defines the area of the video frame where subtitles appear:

- `x`: Left offset in pixels
- `y`: Top offset in pixels
- `width`: Width of the crop area
- `height`: Height of the crop area

### Finding the Crop Region

1. Open your video in a player
2. Identify where subtitles appear
3. Note the coordinates (typically bottom third of the frame)

Example for a 1080p video with subtitles at the bottom:

```bash
--crops '0,850,1920,230'  # Full width, bottom 230 pixels
```

## Configuration Constants

The script includes configurable defaults at the top:

```python
BINARY_PATH = Path("/path/to/your/videocr-PaddleOCR-original/videocr.py")
DEFAULT_EXTENSIONS = ["*.mp4", "*.mkv"]
DEFAULT_CONCURRENCY = 0  # 0 = auto-detect
DEFAULT_LANG = "ch"
DEFAULT_CONF_THRESHOLD = 70
DEFAULT_BRIGHTNESS_THRESHOLD = 145
DEFAULT_USE_GPU = True
```

## Output

Each processed video produces an SRT file with the same base name:

```
video.mp4 → video.srt
```
