#!/usr/bin/env python3
"""
extract_subs.py — Extract all subtitle tracks from MKV files.

Behavior:
- No argument: process all MKVs in the current directory, store subs in the current directory.
- Directory argument: process all MKVs in that directory, store subs alongside each MKV.
- File argument (.mkv): process only that file, store subs in the current directory.

Requirements: mkvmerge, mkvextract
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


# ------------------------------ Utilities ------------------------------ #

def need(cmd: str) -> None:
    """Ensure an external command is available in PATH."""
    if shutil.which(cmd) is None:
        print(f"Error: '{cmd}' is required but not found in PATH.", file=sys.stderr)
        sys.exit(1)


def codec_ext(codec_id: str) -> str:
    """Map Matroska subtitle codec ID to a typical file extension."""
    cid = (codec_id or "").upper()
    if cid in {"S_TEXT/UTF8", "S_TEXT/ASCII", "S_TEXT/USF"}:
        return "srt"
    if cid in {"S_TEXT/ASS", "S_ASS"}:
        return "ass"
    if cid in {"S_TEXT/SSA", "S_SSA"}:
        return "ssa"
    if cid == "S_VOBSUB":
        return "sub"
    if cid == "S_HDMV/PGS":
        return "sup"
    if cid == "S_TEXT/WEBVTT":
        return "vtt"
    return "sub"


_slug_bad_chars = re.compile(r"[^a-z0-9._-]+")
_slug_dashes = re.compile(r"-+")


def slug(s: str) -> str:
    """Make a string safe for filenames: lowercase, dash-separated, safe chars only."""
    s = (s or "").lower().replace(" ", "-")
    s = _slug_bad_chars.sub("-", s)
    s = _slug_dashes.sub("-", s).strip("-")
    return s


_lang3_re = re.compile(r"^[A-Za-z]{3}$")
_lang_ietf_re = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*$")


def lang_code_3(lang: Optional[str]) -> str:
    """Return 3-letter ISO-639-2 code lowercased if valid, else 'und'."""
    if lang and _lang3_re.match(lang):
        return lang.lower()
    return "und"


def normalize_ietf(ietf: Optional[str]) -> Optional[str]:
    """Normalize IETF tag: base language lowercased, rest kept as-is. Return None if invalid."""
    if ietf and _lang_ietf_re.match(ietf):
        base, _, rest = ietf.partition("-")
        return base.lower() + (("-" + rest) if rest else "")
    return None


@dataclass(frozen=True)
class SubTrack:
    tid: int
    codec_id: str
    lang3: str
    lang_ietf: str
    track_name: str


def run_json_identify(file_path: Path) -> dict:
    """Identify tracks via mkvmerge in JSON format."""
    cmd = [
        "mkvmerge",
        "--identification-format", "json",
        "--identify", str(file_path),
    ]
    try:
        res = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n{(e.stderr or '').strip()}"
        ) from e

    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse JSON from: {' '.join(cmd)}\n{e}\nOutput was:\n{res.stdout[:5000]}"
        ) from e


def unique_planned_path(
    basepath: Path, lang: str, ext: str, variant: Optional[str], used: Set[Path]
) -> Path:
    """Ensure destination path is unique against filesystem and planned names."""
    if variant:
        candidate = basepath.with_name(f"{basepath.name}.{lang}.{variant}.{ext}")
    else:
        candidate = basepath.with_name(f"{basepath.name}.{lang}.{ext}")

    n = 2
    while candidate.exists() or candidate in used:
        if variant:
            candidate = basepath.with_name(f"{basepath.name}.{lang}.{variant}-{n}.{ext}")
        else:
            candidate = basepath.with_name(f"{basepath.name}.{lang}-{n}.{ext}")
        n += 1
    return candidate


def extract_subs_for_file(mkv_file: Path, outdir: Path) -> Tuple[bool, str]:
    """Inspect an MKV, plan unique output names, and run mkvextract."""
    filename_only = mkv_file.name
    base = os.path.splitext(filename_only)[0]
    basepath = outdir / base

    # Identify subtitle tracks
    try:
        j = run_json_identify(mkv_file)
    except RuntimeError as e:
        return False, f"Warning: failed to inspect '{filename_only}': {e}"

    tracks = j.get("tracks") or []
    if not isinstance(tracks, list):
        errlist = j.get("errors") or []
        if errlist:
            return False, f"Warning: mkvmerge reported: {' | '.join(map(str, errlist))}"
        return False, f"Warning: no track list found in mkvmerge output for '{filename_only}'."

    # Collect subtitle tracks
    subs: List[SubTrack] = []
    for t in tracks:
        if t.get("type") != "subtitles":
            continue
        props = t.get("properties") or {}
        subs.append(
            SubTrack(
                tid=int(t["id"]),
                codec_id=(props.get("codec_id") or t.get("codec") or "S_TEXT/UTF8"),
                lang3=(props.get("language") or "und"),
                lang_ietf=(props.get("language_ietf") or ""),
                track_name=(props.get("track_name") or ""),
            )
        )

    if not subs:
        return True, f"No subtitle tracks in: {filename_only}"

    # Count tracks per 3-letter language
    lang_counts = Counter(lang_code_3(s.lang3) for s in subs)

    # Plan unique output destinations
    used: Set[Path] = set()
    track_specs: List[str] = []

    for s in subs:
        ext = codec_ext(s.codec_id)
        lang3 = lang_code_3(s.lang3)
        multi_for_lang = lang_counts[lang3] > 1

        variant = ""
        if multi_for_lang:
            # Multiple tracks share the same 3-letter language → prefer IETF
            ietf = normalize_ietf(s.lang_ietf)
            if ietf:
                langtag = ietf
                # When using IETF per spec, do not append track_name.
            else:
                # No valid IETF; fall back to 3-letter + slugified track_name if any
                langtag = lang3
                tslug = slug(s.track_name)
                if tslug:
                    variant = tslug
        else:
            # Only one track for this language → just 3-letter language
            langtag = lang3

        dest = unique_planned_path(basepath, langtag, ext, variant or None, used)
        used.add(dest)
        track_specs.append(f"{s.tid}:{str(dest)}")

    print(f"Extracting subtitles from: {filename_only}")
    outdir.mkdir(parents=True, exist_ok=True)

    # Correct order: input file first, then 'tracks', then specs
    cmd = ["mkvextract", str(mkv_file), "tracks", *track_specs]
    try:
        subprocess.run(cmd, check=True)
        return True, f"Successfully extracted subtitles from: {filename_only}"
    except subprocess.CalledProcessError as e:
        stderr = ""
        if e.stderr:
            stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
        error_msg = f"Error: mkvextract failed for '{filename_only}'.\nCommand: {' '.join(cmd)}\n{stderr.strip()}"
        print(error_msg, file=sys.stderr)
        return False, error_msg


def process_mkvs(
    mkv_files: List[Path],
    outdir: Path,
    max_workers: int = 1
) -> Tuple[int, int]:
    """Process multiple MKV files with optional parallelization.

    Returns:
        Tuple of (successful_count, failed_count)
    """
    successful = 0
    failed = 0

    if not mkv_files:
        return successful, failed

    if max_workers == 1:
        # Sequential processing
        for mkv_file in mkv_files:
            success, message = extract_subs_for_file(mkv_file, outdir)
            if success:
                successful += 1
            else:
                failed += 1
    else:
        # Parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(extract_subs_for_file, mkv_file, outdir): mkv_file
                for mkv_file in mkv_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                mkv_file = future_to_file[future]
                try:
                    success, message = future.result()
                    if success:
                        successful += 1
                    else:
                        failed += 1
                        # Print error messages to stderr for failed files
                        print(message, file=sys.stderr)
                except Exception as exc:
                    failed += 1
                    print(f"File {mkv_file.name} generated an exception: {exc}", file=sys.stderr)

    return successful, failed


def iter_mkvs_in_dir(d: Path) -> Iterable[Path]:
    """Yield MKV files (.mkv and .MKV) in the given directory."""
    yield from sorted([*d.glob("*.mkv"), *d.glob("*.MKV")], key=lambda p: p.name)


def main(argv: Optional[List[str]] = None) -> int:
    need("mkvmerge")
    need("mkvextract")

    parser = argparse.ArgumentParser(description="Extract all subtitle tracks from MKV files.")
    parser.add_argument(
        "path",
        nargs="?",
        help="Directory containing MKVs, a single .mkv file, or omitted for current directory.",
    )
    parser.add_argument(
        "-p", "--parallel",
        type=int,
        default=1,
        metavar="N",
        help="Number of parallel workers (default: 1)",
    )
    args = parser.parse_args(argv)

    # Validate parallel argument
    if args.parallel < 1:
        print("Error: Number of parallel workers must be at least 1.", file=sys.stderr)
        return 1

    if not args.path:
        cur = Path.cwd()
        mkv_files = list(iter_mkvs_in_dir(cur))
        if not mkv_files:
            print("No .mkv files found in current directory.")
            return 0

        successful, failed = process_mkvs(mkv_files, cur, args.parallel)
        if args.parallel > 1:
            print(f"Processed with {args.parallel} workers:")
        print(f"Successful: {successful}, Failed: {failed}")
        if failed == 0:
            print("Done.")
        else:
            print("Done with errors.", file=sys.stderr)
        return 0 if failed == 0 else 1

    p = Path(args.path)

    if p.is_dir():
        mkv_files = list(iter_mkvs_in_dir(p))
        if not mkv_files:
            print(f"No .mkv files found in '{p.name}'.")
            return 0

        successful, failed = process_mkvs(mkv_files, p, args.parallel)
        if args.parallel > 1:
            print(f"Processed with {args.parallel} workers:")
        print(f"Successful: {successful}, Failed: {failed}")
        if failed == 0:
            print("Done.")
        else:
            print("Done with errors.", file=sys.stderr)
        return 0 if failed == 0 else 1

    if p.is_file() and p.suffix.lower() == ".mkv":
        success, message = extract_subs_for_file(p, Path.cwd())
        if success:
            print("Done.")
        else:
            print("Done with errors.", file=sys.stderr)
        return 0 if success else 1

    print("Error: argument must be a directory, a .mkv file, or omitted.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
