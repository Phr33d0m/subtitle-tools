# sub-visualize

Estimate brightness thresholds for OCR subtitle extraction.

## Description

`sub-visualize` analyzes a cropped subtitle screenshot to estimate the optimal `brightness_threshold` parameter for VideOCR. It uses Otsu's method on the min-channel (minimum of B, G, R) to find the threshold that best separates text from background.

## Features

- Automatic threshold estimation using Otsu's method
- Preview image generation for threshold comparison
- Configurable range around base threshold
- Custom output directory support

## Requirements

### Python Dependencies

```
opencv-python
numpy
```

## Installation

1. Install Python dependencies:

   ```bash
   pip install opencv-python numpy
   ```

2. Make the script executable:

   ```bash
   chmod +x sub-visualize.py
   ```

## Usage

```bash
# Basic usage: suggest brightness and generate previews
sub-visualize.py screenshot.png

# Only print suggested value, no images
sub-visualize.py screenshot.png --no-visualize

# Use a different span (generates base-8 to base+7)
sub-visualize.py screenshot.png --span 8

# Use a custom base brightness for previews
sub-visualize.py screenshot.png -b 130

# Write previews to a specific directory
sub-visualize.py screenshot.png --output-dir previews/
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `image` | Path to the cropped subtitle screenshot |
| `--span N` | Range around the base value to visualize (default: 5, generates 10 images) |
| `--output-dir DIR` | Directory for output images (default: same as input) |
| `--no-visualize` | Only print suggested threshold, do not write preview images |
| `-b, --brightness N` | Custom base brightness value for preview generation |

## How It Works

### Threshold Estimation

1. **Load Image**: Reads the screenshot as a color BGR image
2. **Min-Channel**: Calculates `min(B, G, R)` for each pixel
   - This matches VideOCR's logic where a pixel survives if `B >= t` AND `G >= t` AND `R >= t`
3. **Otsu's Method**: Finds the threshold that best separates the "dark cluster" (background) from the "bright cluster" (text)
4. **Output**: Suggests the optimal brightness threshold

### Preview Generation

For each threshold value in the range, applies VideOCR's masking logic:

```python
mask = cv2.inRange(frame, (t, t, t), (255, 255, 255))
output = cv2.bitwise_and(frame, frame, mask=mask)
```

Generates images named: `{input_stem}_{threshold}.png`

## Example Workflow

1. **Capture Screenshot**: Take a frame from your video with visible subtitles
2. **Crop**: Crop to just the subtitle region
3. **Analyze**:

   ```bash
   sub-visualize.py subtitle_crop.png
   ```

4. **Output**:

   ```
   Suggested brightness_threshold (Otsu on min-channel): 145
   Using suggested brightness as base for visualization: 145
   Wrote subtitle_crop_140.png
   Wrote subtitle_crop_141.png
   ...
   Wrote subtitle_crop_149.png
   ```

5. **Compare**: View the generated images to verify the suggested threshold
6. **Use**: Apply the threshold to your OCR command:

   ```bash
   ocrp.py --crops '...' -b 145 video.mp4
   ```

## Output Files

With default settings (`--span 5`), generates 10 preview images:

- `{stem}_{base-5}.png`
- `{stem}_{base-4}.png`
- ...
- `{stem}_{base+4}.png`

Each image shows what text would be visible at that brightness threshold.
