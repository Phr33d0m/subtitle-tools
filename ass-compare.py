#!/usr/bin/env python3

import argparse
import glob
import os
import sys

# ANSI Color Codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


def parse_ass_timestamps(filepath):
    """
    Parses an .ass file and returns a list of dictionaries containing
    start/end timestamps for 'Dialogue:' events only.
    """
    dialogue_events = []

    # Standard .ass defaults (Format: Layer, Start, End, ...)
    # Start is usually index 1, End is usually index 2 after splitting by comma
    start_idx = 1
    end_idx = 2

    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()

        is_events_section = False

        for line in lines:
            line = line.strip()

            # Locate [Events] section
            if line == "[Events]":
                is_events_section = True
                continue

            if not is_events_section:
                continue

            # Check format line to be safe about column positions
            if line.startswith("Format:"):
                parts = [p.strip() for p in line[7:].split(",")]
                try:
                    start_idx = parts.index("Start")
                    end_idx = parts.index("End")
                except ValueError:
                    pass  # Use defaults
                continue

            # STRICT FILTER: Only 'Dialogue:' lines
            if line.startswith("Dialogue:"):
                # Split by comma, limit split to avoid splitting the text itself too much
                # We need enough parts to cover the timestamp indices
                parts = [p.strip() for p in line[9:].split(",", 9)]

                if len(parts) > max(start_idx, end_idx):
                    dialogue_events.append({"start": parts[start_idx], "end": parts[end_idx]})

    except Exception as e:
        print(f"{RED}Error reading file {filepath}: {e}{RESET}")
        return None

    return dialogue_events


def find_merges(single_set, multi_set):
    """
    Find timestamps in single_set that span multiple timestamps in multi_set.
    Returns (merges, used_multi) where:
    - merges: list of (single_ts, [multi_ts, ...]) tuples
    - used_multi: set of multi timestamps that were part of a merge
    """
    merges = []
    used_multi = set()

    for single in sorted(single_set):
        # Find all multi timestamps that start at or after single start
        # and end at or before single end
        candidates = [m for m in multi_set if m[0] >= single[0] and m[1] <= single[1]]
        if len(candidates) >= 2:
            # Check if first starts at single start and last ends at single end
            candidates_sorted = sorted(candidates)
            if candidates_sorted[0][0] == single[0] and candidates_sorted[-1][1] == single[1]:
                merges.append((single, candidates_sorted))
                used_multi.update(candidates)

    return merges, used_multi


def main():
    parser = argparse.ArgumentParser(
        description="Compare timestamps between CHI and ENG .ass subtitle files"
    )
    parser.add_argument(
        "-c", "--chi", default=".", help="Directory containing Chinese (.ass) files"
    )
    parser.add_argument(
        "-e", "--eng", default=".", help="Directory containing English (.eng.ass) files"
    )
    parser.add_argument(
        "-nc", "--no-color", action="store_true", help="Disable colored output"
    )
    args = parser.parse_args()

    chi_path = args.chi
    eng_path = args.eng

    # Set colors based on --no-color flag
    if args.no_color:
        red, green, reset = "", "", ""
    else:
        red, green, reset = RED, GREEN, RESET

    # Enable colors in Windows CMD if necessary
    os.system("")

    eng_files = sorted(glob.glob(os.path.join(eng_path, "*.eng.ass")))

    if not eng_files:
        print(f"No .eng.ass files found in {eng_path}")
        return

    # Helper flag to track if we found ANY error in ANY file
    all_files_perfect = True

    for eng_filepath in eng_files:
        base_name = os.path.basename(eng_filepath).replace(".eng.ass", "")
        chi_filepath = os.path.join(chi_path, f"{base_name}.ass")

        # Determine if pair exists
        if not os.path.exists(chi_filepath):
            print(f"{red}{base_name} [Missing CHI file]{reset}")
            all_files_perfect = False
            continue

        # Parse
        chi_data = parse_ass_timestamps(chi_filepath)
        eng_data = parse_ass_timestamps(eng_filepath)

        if chi_data is None or eng_data is None:
            all_files_perfect = False
            continue

        errors = []

        # 1. Compare Timestamps (Set-based)
        chi_timestamps = {(d["start"], d["end"]) for d in chi_data}
        eng_timestamps = {(d["start"], d["end"]) for d in eng_data}

        # Find timestamps unique to each file
        chi_only = chi_timestamps - eng_timestamps
        eng_only = eng_timestamps - chi_timestamps

        # Detect merges (these are acceptable, not errors)
        # ENG line spanning multiple CHI lines (e.g., 2 CHI → 1 ENG)
        eng_merges, chi_used = find_merges(eng_only, chi_only)
        # CHI line spanning multiple ENG lines (e.g., 2 ENG → 1 CHI)
        chi_merges, eng_used = find_merges(chi_only, eng_only)

        # Calculate line count adjustment from merges
        # eng_merges: each merge has 1 ENG line covering N CHI lines → CHI has (N-1) extra
        chi_merge_adjustment = sum(len(chi_list) - 1 for _, chi_list in eng_merges)
        # chi_merges: each merge has 1 CHI line covering N ENG lines → ENG has (N-1) extra
        eng_merge_adjustment = sum(len(eng_list) - 1 for _, eng_list in chi_merges)

        # 2. Compare Counts (adjusted for merges)
        adjusted_chi_count = len(chi_data) - chi_merge_adjustment
        adjusted_eng_count = len(eng_data) - eng_merge_adjustment
        if adjusted_chi_count != adjusted_eng_count:
            errors.append(f"Line count mismatch: CHI has {len(chi_data)}, ENG has {len(eng_data)}")

        # Only report timestamps that are truly unmatched (not part of a merge)
        chi_remaining = chi_only - chi_used - {m[0] for m in chi_merges}
        eng_remaining = eng_only - eng_used - {m[0] for m in eng_merges}

        for ts in sorted(chi_remaining):
            errors.append(f"CHI-only: {ts[0]} - {ts[1]}")
        for ts in sorted(eng_remaining):
            errors.append(f"ENG-only: {ts[0]} - {ts[1]}")

        # Output logic for this specific file
        if errors:
            all_files_perfect = False
            # Print Filename in RED
            print(f"{red}{base_name}{reset}")
            # Print all errors found in this file
            for err in errors:
                print(f"  - {err}")
            print("")  # Newline for separation

    # Final Summary
    if all_files_perfect:
        print(f"{green}OK{reset}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
