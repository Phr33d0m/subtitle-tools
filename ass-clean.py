#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import os

# Regex to detect "Dialogue" lines (case-sensitive like your grep)
DIALOGUE_LINE_RE = re.compile(r"^\s*Dialogue\b")


def run_grep(pattern: str, target_path: str):
    """
    Run: egrep [flags] PATTERN target_path

    Returns:
        { filepath: earliest_matching_zero_based_line_index }
    """

    # Base flags: -n (line number), -a (process binary as text)
    cmd = ["egrep", "-na"]

    # Determine mode based on target path
    if os.path.isdir(target_path):
        # Recursive if it's a directory
        cmd.append("-R")
    else:
        # Force filename printing (-H) if it's a single file
        # Otherwise grep omits the filename, breaking the parser below
        cmd.append("-H")

    cmd.extend(["--", pattern, target_path])

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # exit code 0 = matches, 1 = no matches, others = error
    if result.returncode not in (0, 1):
        # Suppress error print if file not found to avoid cluttering output when automated
        if "No such file" not in result.stderr:
            print("Error running egrep:", result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    earliest_match = {}

    for line in result.stdout.splitlines():
        # Expected format due to -H or -R: path:line:matched_text
        try:
            path, lineno_str, _ = line.split(":", 2)
        except ValueError:
            continue

        try:
            lineno = int(lineno_str) - 1  # convert to 0-based index
        except ValueError:
            continue

        if path not in earliest_match or lineno < earliest_match[path]:
            earliest_match[path] = lineno

    return earliest_match


def process_file(path: str, cutoff_index: int, mode: str, dry_run: bool = False):
    """
    mode == "before":
        - Remove the line at cutoff_index (the grep match)
        - Remove ALL Dialogue lines BEFORE it

    mode == "after":
        - Remove the line at cutoff_index (the grep match)
        - Remove ALL Dialogue lines AFTER it
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeError) as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return

    new_lines = []
    removed_lines = []

    for idx, line in enumerate(lines):
        remove = False

        # Always remove the matched line itself
        if idx == cutoff_index:
            remove = True
        elif mode == "before":
            if idx < cutoff_index and DIALOGUE_LINE_RE.match(line):
                remove = True
        elif mode == "after":
            if idx > cutoff_index and DIALOGUE_LINE_RE.match(line):
                remove = True

        if remove:
            removed_lines.append(line)
        else:
            new_lines.append(line)

    if not removed_lines:
        return

    if dry_run:
        print(f"- [DRY RUN] {path} will remove:")
        for line in removed_lines:
            print(f"  - {line.rstrip()}")
        return

    try:
        with open(path, "w", encoding="utf-8", errors="ignore") as f:
            f.writelines(new_lines)
    except OSError as e:
        print(f"Error writing {path}: {e}", file=sys.stderr)
        return

    print(f"- {path}: {len(removed_lines)} lines removed")


def parse_args():
    parser = argparse.ArgumentParser(description="Clean ASS/Dialogue lines around a grep match.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--before",
        action="store_true",
        help="remove the matched line and all preceding Dialogue lines",
    )
    group.add_argument(
        "--after",
        action="store_true",
        help="remove the matched line and all following Dialogue lines",
    )

    parser.add_argument(
        "pattern",
        help="egrep regex pattern to search for (e.g. 'Dialogue.*0,0:01:.*I am')",
    )
    parser.add_argument(
        "target_path",
        nargs="?",
        default=".",
        help="file or directory to search (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show which lines would be removed, without changing files",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    mode = "before" if args.before else "after"
    pattern = args.pattern
    target_path = args.target_path

    matches = run_grep(pattern, target_path)
    if not matches:
        return  # no output if nothing to do

    for path, cutoff_index in sorted(matches.items()):
        process_file(path, cutoff_index, mode=mode, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
