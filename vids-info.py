#!/usr/bin/env python3
import argparse
import subprocess
import json
from pathlib import Path
import shutil
import sys

try:
    from rich.table import Table
    from rich.console import Console
except ImportError:
    print("The 'rich' library is required. Install it with:\n  pip install rich")
    sys.exit(1)


def check_ffprobe():
    if shutil.which("ffprobe") is None:
        print("Error: 'ffprobe' not found. Please install ffmpeg and ensure ffprobe is in your PATH.")
        sys.exit(1)


def parse_fps(fps_str: str) -> str:
    """
    Convert an fps string like '30000/1001' or '25/1' to a human-readable
    float string like '29.97' or '25.00'. Returns '?' if it can't parse.
    """
    if not fps_str or fps_str in ("0/0", "0/1", "N/A"):
        return "?"
    try:
        num, den = fps_str.split("/")
        num = float(num)
        den = float(den)
        if den == 0:
            return "?"
        fps = num / den
        # Show up to 2 decimal places
        return f"{fps:.2f}"
    except Exception:
        return "?"


def get_video_info(path: Path):
    """
    Returns (duration_str, resolution_str, fps_str, duration_raw) for the given video file.
    duration_str -> 'XminYsec'
    resolution_str -> 'WIDTHxHEIGHT'
    fps_str -> 'XX.XX' (frames per second)
    duration_raw -> float seconds (for sorting)
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration:stream=width,height,avg_frame_rate",
        "-of", "json",
        str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Could not probe this file
        return "?", "?", "?", 0.0

    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return "?", "?", "?", 0.0

    # Duration
    duration_str = "?"
    duration_raw = 0.0
    try:
        duration_raw = float(info["format"]["duration"])
        total_seconds = int(round(duration_raw))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        duration_str = f"{minutes}min{seconds}sec"
    except Exception:
        pass

    # Resolution & FPS (from first video stream)
    resolution_str = "?"
    fps_str = "?"
    try:
        streams = info.get("streams", [])
        vstreams = [s for s in streams if s.get("codec_type") == "video"] or streams
        if vstreams:
            v = vstreams[0]
            w = v.get("width")
            h = v.get("height")
            if w and h:
                resolution_str = f"{w}x{h}"

            fps_raw = v.get("avg_frame_rate")
            fps_str = parse_fps(fps_raw)
    except Exception:
        pass

    return duration_str, resolution_str, fps_str, duration_raw


def main():
    parser = argparse.ArgumentParser(description="Display video file info")
    parser.add_argument("-s", "--sort", action="store_true",
                        help="Sort by length (descending)")
    args = parser.parse_args()

    check_ffprobe()

    exts = {".mkv", ".mp4"}
    files = [p for p in Path(".").iterdir() if p.is_file() and p.suffix.lower() in exts]
    files.sort()

    if not files:
        print("No .mkv or .mp4 files found in the current directory.")
        return

    video_data = []
    for f in files:
        length, res, fps, duration_raw = get_video_info(f)
        video_data.append((f.name, length, res, fps, duration_raw))

    if args.sort:
        video_data.sort(key=lambda x: (-x[4], x[0]))

    console = Console()
    table = Table(title="Video Files in Current Directory", expand=True)

    table.add_column("Filename", style="bold", overflow="fold")
    table.add_column("Length", justify="right")
    table.add_column("Resolution", justify="right")
    table.add_column("FPS", justify="right")

    for name, length, res, fps, _ in video_data:
        table.add_row(name, length, res, fps)

    console.print(table)


if __name__ == "__main__":
    main()
