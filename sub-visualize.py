#!/usr/bin/env python3
"""
Estimate a good videocr brightness_threshold for cropped subtitle screenshots
and optionally generate preview images for a range of thresholds.

Usage:
    # Basic usage: suggest brightness and generate previews around it
    python sub_brightness.py screenshot.png

    # Only print suggested value, no images:
    python sub_brightness.py screenshot.png --no-visualize

    # Use a different span (e.g. base-8 .. base+7):
    python sub_brightness.py screenshot.png --span 8

    # Use a custom base brightness for previews (but still compute + print suggested):
    python sub_brightness.py screenshot.png -b 130

    # Write previews to a specific directory:
    python sub_brightness.py screenshot.png --output-dir previews/
"""

import argparse
from pathlib import Path

import cv2
import numpy as np


def suggest_threshold(img: np.ndarray) -> int:
    """
    Suggest a brightness_threshold for videocr, based on the per-pixel
    min-channel (min(B, G, R)) and Otsu's method.
    """
    # img is BGR uint8
    if img.ndim != 3 or img.shape[2] != 3:
        raise ValueError("Expected a color BGR image with 3 channels.")

    # For VideOCR's logic, a pixel survives if B>=t, G>=t, R>=t.
    # So the maximum t that keeps a pixel is min(B,G,R).
    min_chan = img.min(axis=2).astype(np.uint8)

    # Otsu finds a threshold that separates "dark cluster" from "bright cluster"
    # on this min-channel image.
    ret, _ = cv2.threshold(
        min_chan, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return int(ret)


def apply_brightness_threshold(img: np.ndarray, t: int) -> np.ndarray:
    """
    Apply the same masking logic VideOCR uses:

        frame = cv2.bitwise_and(
            frame, frame,
            mask=cv2.inRange(frame,
                             (t, t, t),
                             (255, 255, 255))
        )
    """
    t = max(0, min(255, int(t)))  # clamp to 0..255
    lower = (t, t, t)
    upper = (255, 255, 255)

    mask = cv2.inRange(img, lower, upper)
    out = cv2.bitwise_and(img, img, mask=mask)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate a videocr brightness_threshold for a cropped subtitle "
            "screenshot and optionally generate preview images for nearby values."
        )
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Path to the cropped subtitle screenshot (BGR-ish image).",
    )
    parser.add_argument(
        "--span",
        type=int,
        default=5,
        help=(
            "Range around the base value to visualize. "
            "Generates thresholds from base-span to base+span-1 "
            "(default: 5 ⇒ typically 10 images)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for output images (default: same directory as input).",
    )
    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="Only print suggested threshold, do not write preview images.",
    )
    parser.add_argument(
        "-b",
        "--brightness",
        type=int,
        default=None,
        help=(
            "Custom base brightness value for preview generation. "
            "If not provided, the suggested brightness is used as the base."
        ),
    )

    args = parser.parse_args()

    img_path: Path = args.image
    if not img_path.is_file():
        raise SystemExit(f"Input file not found: {img_path}")

    # Read as color (BGR)
    img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"Failed to read image as color: {img_path}")

    # 1) Suggest the best threshold
    best_t = suggest_threshold(img)
    print(f"Suggested brightness_threshold (Otsu on min-channel): {best_t}")

    if args.no_visualize:
        return

    # 2) Decide base value for visualization
    if args.brightness is not None:
        base_t = max(0, min(255, args.brightness))
        print(f"Using custom base brightness for visualization: {base_t}")
    else:
        base_t = best_t
        print(f"Using suggested brightness as base for visualization: {base_t}")

    # 3) Generate preview images
    out_dir = args.output_dir or img_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # We generate [base-span, ..., base+span-1], clamped to 0..255
    start = max(0, base_t - args.span)
    stop = min(256, base_t + args.span)  # exclusive upper bound
    thresholds = list(range(start, stop))

    stem = img_path.stem

    for t in thresholds:
        out_img = apply_brightness_threshold(img, t)
        out_name = f"{stem}_{t}.png"
        out_path = out_dir / out_name
        ok = cv2.imwrite(str(out_path), out_img)
        if ok:
            print(f"Wrote {out_path}")
        else:
            print(f"Failed to write {out_path}")


if __name__ == "__main__":
    main()
