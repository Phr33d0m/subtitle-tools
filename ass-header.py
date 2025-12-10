#!/usr/bin/env python3
import argparse
import os
import sys


def read_header(header_path):
    try:
        with open(header_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            header_lines = f.readlines()
    except OSError as e:
        print(
            f"Error reading header file '{header_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # Strip trailing empty lines
    while header_lines and header_lines[-1].strip() == "":
        header_lines.pop()

    if not header_lines:
        print("Header file is empty after stripping trailing blank lines.",
              file=sys.stderr)
        sys.exit(1)

    # Ensure last header line ends with newline
    if not header_lines[-1].endswith("\n"):
        header_lines[-1] += "\n"

    return header_lines


def process_ass_file(path, header_lines):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"Error reading '{path}': {e}", file=sys.stderr)
        return

    # Find the [Events] section
    events_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("[Events]"):
            events_index = i
            break

    if events_index is None:
        # No [Events] section; skip
        print(f"{path}: skipped (no [Events] section found)")
        return

    events_block = lines[events_index:]

    # Build new file: header + exactly one blank line + [Events] and onwards
    new_lines = list(header_lines)
    new_lines.append("\n")  # exactly one empty line
    new_lines.extend(events_block)

    try:
        with open(path, "w", encoding="utf-8-sig", errors="ignore") as f:
            f.writelines(new_lines)
        print(f"{path}: header replaced")
    except OSError as e:
        print(f"Error writing '{path}': {e}", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Replace [Script Info] and [V4+ Styles] header in all .ass files in current directory."
    )
    parser.add_argument(
        "header_path",
        help="path to a text file containing the desired ASS header (Script Info + V4+ Styles)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    header_lines = read_header(args.header_path)

    for name in os.listdir("."):
        if not name.lower().endswith(".ass"):
            continue
        if not os.path.isfile(name):
            continue
        process_ass_file(name, header_lines)


if __name__ == "__main__":
    main()
