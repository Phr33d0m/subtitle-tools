#!/usr/bin/env python3
"""
subtimefix.py — Shift all ASS subtitle timestamps by a given number of milliseconds.

Usage:
    python3 subtimefix.py -t '6032'
    python3 subtimefix.py -t '-6032' myfile.ass
    python3 subtimefix.py -t '6032' ./folder

Notes:
- Processes .ass files recursively if you provide a directory.
- Shifts both Dialogue: and Comment: timestamps.
- Respects the 'Format:' mapping inside [Events].
- Rounds to nearest centisecond (ASS precision) and clamps below zero.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from typing import List, Optional

EVENTS_HEADER = "[Events]"
FORMAT_PREFIX = "Format:"
DIALOGUE_PREFIX = "Dialogue:"
COMMENT_PREFIX = "Comment:"

# Regex for ASS time format: H:MM:SS.cc (centiseconds)
TIME_RE = re.compile(
    r"^(?P<h>\d+):(?P<m>[0-5]?\d):(?P<s>[0-5]?\d)\.(?P<cs>\d{1,2})$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Shift all timestamps in ASS files by a given millisecond offset.")
    p.add_argument("-t", "--time", type=int, required=True,
                   help="Time shift in milliseconds (positive to move forward, negative to move backward).")
    p.add_argument("path", nargs="?", default=".",
                   help="Optional path to a .ass file or directory (default: current directory).")
    return p.parse_args()


def ms_to_centiseconds(ms: int) -> int:
    """
    Convert milliseconds to centiseconds with symmetric rounding.
    E.g. 6032 ms -> 603 cs; -6032 ms -> -603 cs.
    """
    if ms >= 0:
        return (ms + 5) // 10
    else:
        return (ms - 5) // 10


def time_to_centiseconds(t: str) -> Optional[int]:
    """
    Parse ASS time string (H:MM:SS.cc) to total centiseconds.
    Returns None if the format is invalid.
    """
    m = TIME_RE.match(t.strip())
    if not m:
        return None
    h = int(m.group("h"))
    mi = int(m.group("m"))
    s = int(m.group("s"))
    cs = int(m.group("cs").ljust(2, "0")[:2])  # normalize to two digits
    return ((h * 60 + mi) * 60 + s) * 100 + cs


def centiseconds_to_time(cs_total: int) -> str:
    """
    Convert total centiseconds to ASS time string H:MM:SS.cc.
    Clamps at zero.
    """
    if cs_total < 0:
        cs_total = 0
    s_total, cs = divmod(cs_total, 100)
    m_total, s = divmod(s_total, 60)
    h, m = divmod(m_total, 60)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def detect_encoding(path: str) -> str:
    """
    Try utf-8-sig first (common for ASS). Fallback to cp1252 if needed.
    Return the encoding string to use for both reading and writing.
    """
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    # As a last resort, use latin-1 (lossless byte mapping).
    return "latin-1"


def process_file(path: str, delta_ms: int) -> tuple[int, int]:
    """
    Process a single .ass file, shifting timestamps by delta_ms.
    Returns (lines_changed, timestamps_shifted).
    """
    enc = detect_encoding(path)
    with open(path, "r", encoding=enc, newline="") as f:
        lines = f.readlines()

    in_events = False
    # Track the most recent Format: mapping inside [Events]
    format_fields: List[str] = []
    idx_start = idx_end = None  # indices of Start and End columns

    # Pre-scan to mark where [Events] blocks are (usually one, but spec allows multiple)
    # We'll process in a single pass below.
    lines_changed = 0
    timestamps_shifted = 0
    delta_cs = ms_to_centiseconds(delta_ms)

    def update_format(line: str) -> None:
        nonlocal format_fields, idx_start, idx_end
        # Example: Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        parts = line.split(":", 1)
        if len(parts) != 2:
            return
        right = parts[1].strip()
        # Split by commas, strip whitespace
        fields = [fld.strip().lower() for fld in right.split(",")]
        format_fields = fields
        # Map indices
        try:
            idx_start = fields.index("start")
            idx_end = fields.index("end")
        except ValueError:
            idx_start = idx_end = None

    def shift_event_times(line: str) -> str:
        nonlocal timestamps_shifted
        # line like "Dialogue: 0,0:00:01.00,0:00:02.00,Style,..."
        # or "Comment: 0,0:00:01.00,0:00:02.00,Style,..."
        if not format_fields or idx_start is None or idx_end is None:
            return line  # no valid format mapping; leave untouched

        prefix, rest = line.split(":", 1)
        # We need to split into exactly len(format_fields) columns for the event fields.
        # Only the text field can contain commas, and it is within the defined format;
        # so split with maxsplit = len(fields) - 1
        cells = rest.lstrip().split(",", len(format_fields) - 1)
        if len(cells) < max(idx_start, idx_end) + 1:
            return line  # malformed line; leave as is

        # Extract times
        start_str = cells[idx_start].strip()
        end_str = cells[idx_end].strip()

        start_cs = time_to_centiseconds(start_str)
        end_cs = time_to_centiseconds(end_str)
        if start_cs is None or end_cs is None:
            return line  # unexpected format; leave untouched

        new_start = centiseconds_to_time(start_cs + delta_cs)
        new_end = centiseconds_to_time(end_cs + delta_cs)

        if new_start != start_str or new_end != end_str:
            cells[idx_start] = new_start
            cells[idx_end] = new_end
            timestamps_shifted += 2  # count both start and end updates

            # Rebuild the line exactly
            return f"{prefix}: {','.join(cells)}"
        return line

    # Process lines
    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")  # preserve other whitespace
        # Track entering/leaving [Events]
        if line.strip().startswith("[") and line.strip().lower() == EVENTS_HEADER.lower():
            in_events = True
            format_fields = []
            idx_start = idx_end = None
            # write back unchanged
            continue

        if in_events:
            # If we reach the next section header, we're out of Events
            if line.strip().startswith("[") and line.strip() != "":
                in_events = False

        if in_events:
            # Refresh mapping when we see Format:
            if line.strip().lower().startswith(FORMAT_PREFIX.lower()):
                update_format(line)
                # If we normalized whitespace, keep the original line
                # (We don't change Format: lines.)
                continue

            # Shift timestamps on Dialogue: and Comment:
            if line.strip().lower().startswith(DIALOGUE_PREFIX.lower()) or line.strip().lower().startswith(COMMENT_PREFIX.lower()):
                new_line = shift_event_times(line)
                if new_line != line:
                    lines[i] = new_line + "\n"
                    lines_changed += 1
                continue

        # default: keep as-is
        # Ensure we preserve original newline
        if not raw.endswith("\n"):
            lines[i] = line
        else:
            lines[i] = line + "\n"

    # Write back in place
    with open(path, "w", encoding=enc, newline="") as f:
        f.writelines(lines)

    return lines_changed, timestamps_shifted


def gather_files(path: str) -> list[str]:
    if os.path.isfile(path):
        if path.lower().endswith(".ass"):
            return [path]
        else:
            print(f"[WARN] Skipping non-.ass file: {path}")
            return []
    elif os.path.isdir(path):
        matches = glob.glob(os.path.join(path, "**", "*.ass"), recursive=True)
        return sorted(matches)
    else:
        print(f"[ERR] Path not found: {path}", file=sys.stderr)
        return []


def main() -> None:
    args = parse_args()
    delta_ms = args.time
    target = args.path

    files = gather_files(target)

    if not files:
        print("No .ass files found in the current directory.", file=sys.stderr)
        sys.exit(1)

    total_files = 0
    total_lines_changed = 0
    total_timestamps = 0

    for path in files:
        try:
            lines_changed, timestamps_shifted = process_file(path, delta_ms)
            total_files += 1
            total_lines_changed += lines_changed
            total_timestamps += timestamps_shifted
            print(
                f"[OK] {path}: lines changed={lines_changed}, timestamps updated={timestamps_shifted}")
        except Exception as e:
            print(f"[ERR] {path}: {e}", file=sys.stderr)

    # Summary
    direction = "forward" if delta_ms >= 0 else "backward"
    print(
        f"\nProcessed {total_files} file(s). Shifted {abs(delta_ms)} ms {direction}. "
        f"Lines changed: {total_lines_changed}. Timestamps updated: {total_timestamps}."
    )


if __name__ == "__main__":
    main()
