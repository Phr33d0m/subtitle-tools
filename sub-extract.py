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
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


# ------------------------------ Data Structures ------------------------------ #

class FileStatus(Enum):
    """File processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_SUBS = "no_subs"


@dataclass
class ExtractFileProgress:
    """Track per-file extraction processing state."""
    file_path: Path
    status: FileStatus
    subtitle_tracks: str = ""  # Comma-separated language codes like "eng, jpn"
    progress_percent: int = 0  # 0-100 extraction progress
    start_time: Optional[float] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None


# ------------------------------ Utilities ------------------------------ #

def need(cmd: str) -> None:
    """Ensure an external command is available in PATH."""
    if shutil.which(cmd) is None:
        console = Console()
        console.print(f"[red]Error:[/red] '{cmd}' is required but not found in PATH.")
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

    outdir.mkdir(parents=True, exist_ok=True)

    # Correct order: input file first, then 'tracks', then specs
    cmd = ["mkvextract", str(mkv_file), "tracks", *track_specs]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, f"Successfully extracted subtitles from: {filename_only}"
    except subprocess.CalledProcessError as e:
        stderr = ""
        if e.stderr:
            stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
        error_msg = f"Error: mkvextract failed for '{filename_only}'.\nCommand: {' '.join(cmd)}\n{stderr.strip()}"
        print(error_msg, file=sys.stderr)
        return False, error_msg


# Regex for parsing mkvextract progress output
_PROGRESS_RE = re.compile(r"Progress:\s*(\d+)%")


def extract_subs_with_progress(
    mkv_file: Path,
    outdir: Path,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Tuple[bool, str]:
    """Inspect an MKV, plan unique output names, and run mkvextract with progress updates.

    Args:
        mkv_file: Path to the MKV file
        outdir: Output directory for subtitle files
        progress_callback: Optional callback function called with progress percentage (0-100)

    Returns:
        Tuple of (success, message)
    """
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
            ietf = normalize_ietf(s.lang_ietf)
            if ietf:
                langtag = ietf
            else:
                langtag = lang3
                tslug = slug(s.track_name)
                if tslug:
                    variant = tslug
        else:
            langtag = lang3

        dest = unique_planned_path(basepath, langtag, ext, variant or None, used)
        used.add(dest)
        track_specs.append(f"{s.tid}:{str(dest)}")

    outdir.mkdir(parents=True, exist_ok=True)

    # Run mkvextract with Popen for real-time progress parsing
    cmd = ["mkvextract", str(mkv_file), "tracks", *track_specs]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Parse output for progress updates
        if process.stdout:
            for line in process.stdout:
                match = _PROGRESS_RE.search(line)
                if match and progress_callback:
                    progress_callback(int(match.group(1)))

        returncode = process.wait()
        if returncode != 0:
            return False, f"Error: mkvextract failed for '{filename_only}' (exit code {returncode})"

        return True, f"Successfully extracted subtitles from: {filename_only}"
    except Exception as e:
        return False, f"Error: mkvextract failed for '{filename_only}': {e}"


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


class SubtitleExtractProcessor:
    """Handles subtitle extraction with Rich table display."""

    def __init__(self):
        self.console = Console()
        self._file_progress: List[ExtractFileProgress] = []
        self._progress_lock = threading.Lock()

    def _create_table(self) -> Table:
        """Create Rich table for displaying file processing status."""
        table = Table(expand=True, show_header=True, header_style="bold cyan", box=box.SIMPLE_HEAD)

        table.add_column("File", style="cyan", no_wrap=True, ratio=5)
        table.add_column("Tracks", style="green", no_wrap=True, ratio=1, justify="center")
        table.add_column("Progress", style="white", no_wrap=True, ratio=3)
        table.add_column("Status", style="white", no_wrap=True, ratio=2)
        table.add_column("Time", style="magenta", no_wrap=True, ratio=1)

        return table

    def _get_status_style(self, status: FileStatus) -> str:
        """Get style for status text."""
        styles = {
            FileStatus.QUEUED: "dim",
            FileStatus.PROCESSING: "yellow",
            FileStatus.COMPLETED: "green",
            FileStatus.FAILED: "red",
            FileStatus.NO_SUBS: "dim yellow",
        }
        return styles.get(status, "white")

    def _format_duration(self, duration: Optional[float]) -> str:
        """Format duration for display."""
        if duration is None:
            return "—"
        elif duration < 60:
            return f"{duration:.1f}s"
        else:
            minutes = int(duration // 60)
            seconds = duration % 60
            return f"{minutes}m {seconds:.0f}s"

    def _format_progress_bar(self, percent: int, status: FileStatus) -> str:
        """Format a progress bar string."""
        if status == FileStatus.QUEUED:
            return "[dim]—[/dim]"
        if status == FileStatus.NO_SUBS:
            return "[dim]—[/dim]"
        if status == FileStatus.COMPLETED:
            return "[green]████████████████████[/green] 100%"
        if status == FileStatus.FAILED:
            return "[red]Failed[/red]"

        # Processing status - show actual progress bar
        bar_width = 20
        filled = int(bar_width * percent / 100)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        return f"[yellow]{bar}[/yellow] {percent:3d}%"

    def _update_table_rows(self, table: Table, max_rows: int) -> None:
        """Update table rows with current file progress."""
        with self._progress_lock:
            # Sort: processing first, then queued, then completed/failed
            status_priority = {
                FileStatus.PROCESSING: 0,
                FileStatus.QUEUED: 1,
                FileStatus.FAILED: 2,
                FileStatus.NO_SUBS: 3,
                FileStatus.COMPLETED: 4,
            }

            sorted_files = sorted(
                self._file_progress,
                key=lambda fp: (status_priority.get(fp.status, 5), fp.file_path.name)
            )

            # Show up to max_rows
            display_files = sorted_files[:max_rows]

            for file_prog in display_files:
                # Format tracks
                tracks_str = file_prog.subtitle_tracks if file_prog.subtitle_tracks else "—"

                # Progress bar
                progress_bar = self._format_progress_bar(file_prog.progress_percent, file_prog.status)

                # Status with style
                status_names = {
                    FileStatus.QUEUED: "Queued",
                    FileStatus.PROCESSING: "Processing",
                    FileStatus.COMPLETED: "Done",
                    FileStatus.FAILED: "Failed",
                    FileStatus.NO_SUBS: "No Subs",
                }
                status_text = status_names.get(file_prog.status, file_prog.status.value)
                status_style = self._get_status_style(file_prog.status)

                # Calculate duration
                if file_prog.status == FileStatus.PROCESSING and file_prog.start_time is not None:
                    elapsed = time.time() - file_prog.start_time
                    duration = self._format_duration(elapsed)
                else:
                    duration = self._format_duration(file_prog.duration)

                table.add_row(
                    file_prog.file_path.name,
                    tracks_str,
                    progress_bar,
                    f"[{status_style}]{status_text}[/{status_style}]",
                    duration
                )

    def _update_file_progress(
        self,
        file_path: Path,
        status: FileStatus,
        subtitle_tracks: Optional[str] = None,
        progress_percent: Optional[int] = None,
        duration: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update file progress information.

        If subtitle_tracks or progress_percent is None, preserve existing value.
        """
        with self._progress_lock:
            # Find existing entry
            for prog in self._file_progress:
                if prog.file_path == file_path:
                    prog.status = status
                    if subtitle_tracks is not None:
                        prog.subtitle_tracks = subtitle_tracks
                    if progress_percent is not None:
                        prog.progress_percent = progress_percent
                    prog.duration = duration
                    prog.error_message = error_message
                    if status == FileStatus.PROCESSING:
                        prog.start_time = time.time()
                    return

            # Create new entry
            start_time = time.time() if status == FileStatus.PROCESSING else None
            self._file_progress.append(ExtractFileProgress(
                file_path=file_path,
                status=status,
                subtitle_tracks=subtitle_tracks or "",
                progress_percent=progress_percent or 0,
                start_time=start_time,
                duration=duration,
                error_message=error_message
            ))

    def _update_progress_percent(self, file_path: Path, percent: int) -> None:
        """Update only the progress percentage for a file."""
        with self._progress_lock:
            for prog in self._file_progress:
                if prog.file_path == file_path:
                    prog.progress_percent = percent
                    return

    def _get_subtitle_tracks(self, mkv_file: Path) -> str:
        """Get comma-separated language codes for subtitle tracks in an MKV file."""
        try:
            j = run_json_identify(mkv_file)
            tracks = j.get("tracks") or []
            langs = []
            for t in tracks:
                if t.get("type") == "subtitles":
                    props = t.get("properties") or {}
                    lang = props.get("language") or "und"
                    langs.append(lang)
            return ", ".join(langs) if langs else ""
        except Exception:
            return ""

    def process_files(
        self,
        mkv_files: List[Path],
        outdir: Path,
        max_workers: int = 1
    ) -> Tuple[int, int, int]:
        """Process multiple MKV files with Rich Live table display.

        Returns:
            Tuple of (successful_count, failed_count, no_subs_count)
        """
        if not mkv_files:
            self.console.print("No MKV files found to process")
            return 0, 0, 0

        # Determine display rows
        display_rows = min(len(mkv_files), max(max_workers, 10))

        # Initialize progress for all files with track languages
        for mkv_file in mkv_files:
            tracks = self._get_subtitle_tracks(mkv_file)
            self._update_file_progress(mkv_file, FileStatus.QUEUED, subtitle_tracks=tracks)

        successful = 0
        failed = 0
        no_subs = 0
        total = len(mkv_files)
        lock = threading.Lock()

        def process_one(mkv_file: Path) -> None:
            nonlocal successful, failed, no_subs

            self._update_file_progress(mkv_file, FileStatus.PROCESSING)
            start_time = time.time()

            # Progress callback for real-time updates
            def on_progress(percent: int) -> None:
                self._update_progress_percent(mkv_file, percent)

            success, message = extract_subs_with_progress(mkv_file, outdir, on_progress)
            elapsed = time.time() - start_time

            # Determine if it was "no subs" case
            is_no_subs = success and "No subtitle tracks" in message

            with lock:
                if is_no_subs:
                    no_subs += 1
                    final_status = FileStatus.NO_SUBS
                elif success:
                    successful += 1
                    final_status = FileStatus.COMPLETED
                else:
                    failed += 1
                    final_status = FileStatus.FAILED

            # Update progress - track languages are already set during initialization
            self._update_file_progress(
                mkv_file,
                final_status,
                subtitle_tracks="" if is_no_subs else None,  # Clear for no subs
                progress_percent=100 if final_status == FileStatus.COMPLETED else None,
                duration=elapsed,
                error_message=message if not success else None
            )

        # Process with Rich Live display
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_one, mkv_file) for mkv_file in mkv_files]

            with Live(console=self.console, auto_refresh=True, refresh_per_second=4) as live:
                while True:
                    # Create current display
                    table = self._create_table()
                    self._update_table_rows(table, display_rows)

                    # Panel title with count
                    completed = successful + failed + no_subs
                    title = f"Subtitle Extraction ({completed}/{total})"
                    dashboard_panel = Panel(
                        table,
                        title=title,
                        border_style="blue",
                        padding=(0, 1)
                    )

                    # Update display
                    live.update(dashboard_panel)

                    # Check if done
                    with lock:
                        if completed >= total:
                            break

                    time.sleep(0.1)  # Update frequently for smooth progress bars

        # Print final summary
        self.console.print()
        self.console.print(f"Completed: {successful} extracted, {no_subs} no subtitles, {failed} failed")

        return successful, failed, no_subs


def iter_mkvs_in_dir(d: Path) -> Iterable[Path]:
    """Yield MKV files (.mkv and .MKV) in the given directory."""
    yield from sorted([*d.glob("*.mkv"), *d.glob("*.MKV")], key=lambda p: p.name)


def main(argv: Optional[List[str]] = None) -> int:
    console = Console()

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
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory for extracted subtitles (must exist)",
    )
    args = parser.parse_args(argv)

    # Validate parallel argument
    if args.parallel < 1:
        console.print("[red]Error:[/red] Number of parallel workers must be at least 1.")
        return 1

    # Determine output directory
    if args.output:
        outdir = Path(args.output)
        if not outdir.is_dir():
            console.print(f"[red]Error:[/red] Output directory '{args.output}' does not exist.")
            return 1
    else:
        outdir = Path.cwd()

    # Create processor
    processor = SubtitleExtractProcessor()

    if not args.path:
        mkv_files = list(iter_mkvs_in_dir(Path.cwd()))
        if not mkv_files:
            console.print("No .mkv files found in current directory.")
            return 0

        successful, failed, no_subs = processor.process_files(mkv_files, outdir, args.parallel)
        return 0 if failed == 0 else 1

    p = Path(args.path)

    if p.is_dir():
        mkv_files = list(iter_mkvs_in_dir(p))
        if not mkv_files:
            console.print(f"No .mkv files found in '{p.name}'.")
            return 0

        successful, failed, no_subs = processor.process_files(mkv_files, outdir, args.parallel)
        return 0 if failed == 0 else 1

    if p.is_file() and p.suffix.lower() == ".mkv":
        # Single file - use processor for consistency
        successful, failed, no_subs = processor.process_files([p], outdir, 1)
        return 0 if failed == 0 else 1

    console.print("[red]Error:[/red] argument must be a directory, a .mkv file, or omitted.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
