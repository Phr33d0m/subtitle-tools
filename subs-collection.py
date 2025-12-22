#!/usr/bin/env python3
"""
subs-collection.py — Build a mirrored directory structure with only subtitles and attachments.

Usage:
    subs-collection.py <input_dir> <output_dir> [--dry-run] [--verbose]

This script walks a TV series collection, extracts subtitles and attachments from MKV files,
and creates a mirrored directory structure in the output directory. Directories containing
only hardsubbed content (no extractable subtitles) are automatically removed.
"""

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

# Constants
PARALLEL_WORKERS = 5
SUB_EXTENSIONS = {".ass", ".srt", ".sub", ".sup", ".vtt", ".ssa"}

console = Console()


@dataclass
class Stats:
    """Statistics for the extraction process."""

    directories_processed: int = 0
    directories_with_subs: int = 0
    directories_skipped: int = 0
    directories_removed: int = 0
    directories_ignored: int = 0
    files_extracted: int = 0
    files_skipped: int = 0
    files_ignored: int = 0
    files_deleted: int = 0
    zips_created: int = 0
    errors: List[str] = field(default_factory=list)
    dirs_to_zip: Set[Path] = field(default_factory=set)

    def print_summary(self) -> None:
        """Print a rich summary table."""
        table = Table(title="Extraction Summary", show_header=False, border_style="blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        table.add_row("Directories processed", str(self.directories_processed))
        table.add_row("Directories with subs", f"[green]{self.directories_with_subs}[/green]")
        table.add_row("Directories skipped", f"[yellow]{self.directories_skipped}[/yellow]")
        table.add_row("Directories removed", f"[dim]{self.directories_removed}[/dim]")
        if self.directories_ignored:
            table.add_row("Directories ignored", f"[magenta]{self.directories_ignored}[/magenta]")
        table.add_row("Files extracted", f"[green]{self.files_extracted}[/green]")
        table.add_row("Files skipped", f"[yellow]{self.files_skipped}[/yellow]")
        if self.files_deleted:
            table.add_row("Files deleted (orphans)", f"[red]{self.files_deleted}[/red]")
        if self.files_ignored:
            table.add_row("Files ignored", f"[magenta]{self.files_ignored}[/magenta]")
        if self.zips_created:
            table.add_row("Zips created", f"[blue]{self.zips_created}[/blue]")

        if self.errors:
            table.add_row("Errors", f"[red]{len(self.errors)}[/red]")

        console.print()
        console.print(table)


def check_dependencies() -> None:
    """Ensure required tools are available."""
    for tool in ["subattachextract", "subextract"]:
        if shutil.which(tool) is None:
            console.print(f"[red]Error:[/red] '{tool}' is required but not found in PATH.")
            sys.exit(1)


def count_subtitle_files(directory: Path) -> int:
    """Count subtitle files in directory (non-recursive)."""
    if not directory.exists():
        return 0
    count = 0
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in SUB_EXTENSIONS:
            count += 1
    return count


def find_orphaned_subs(input_dir: Path, output_dir: Path) -> List[Path]:
    """Find subtitle files in output_dir that have no corresponding MKV in input_dir.

    Returns:
        List of orphaned subtitle file paths to delete.
    """
    if not output_dir.exists():
        return []

    # Get all MKV basenames in input directory
    mkv_basenames = set()
    for f in input_dir.iterdir():
        if f.is_file() and f.suffix.lower() == ".mkv":
            mkv_basenames.add(f.stem)

    # Find subtitle files without corresponding MKV
    orphans = []
    for f in output_dir.iterdir():
        if f.is_file() and f.suffix.lower() in SUB_EXTENSIONS:
            # Check if subtitle matches any MKV basename
            # Handles: basename.lang.ext, basename.lang.variant.ext, basename.lang-N.ext
            has_matching_mkv = any(f.name.startswith(basename + ".") for basename in mkv_basenames)
            if not has_matching_mkv:
                orphans.append(f)

    return orphans


def cleanup_orphaned_subs(
    input_dir: Path,
    output_dir: Path,
    dry_run: bool,
    verbose: bool,
    stats: Stats,
    progress: Progress,
) -> bool:
    """Delete orphaned subtitle files and return True if any were deleted."""
    orphans = find_orphaned_subs(input_dir, output_dir)

    if not orphans:
        return False

    deleted_count = 0
    for orphan in orphans:
        if dry_run:
            if verbose:
                progress.console.print(f"  [red]Would delete orphan:[/red] {orphan.name}")
            deleted_count += 1  # Count for dry-run reporting
        else:
            orphan.unlink()
            deleted_count += 1
            if verbose:
                progress.console.print(f"  [red]Deleted orphan:[/red] {orphan.name}")

    stats.files_deleted += deleted_count
    return deleted_count > 0


def has_work_zip(input_root: Path, rel_path: Path) -> bool:
    """Check if _work.zip exists in the source directory."""
    source_dir = input_root / rel_path
    return (source_dir / "_work.zip").exists()


def extract_version_from_filename(filename: str) -> Optional[int]:
    """Extract version number from an MKV filename.

    Looks for pattern: 'SeriesName - ###vX [garbage].mkv' where X is the version.

    Returns:
        The version number as int, or None if no version found.

    Examples:
        'Zui Qiang Shengji - 009v3 [1080p].mkv' → 3
        'Zui Qiang Shengji - 008 [1080p].mkv' → None
    """
    match = re.search(r"- \d+v(\d+)\s*\[", filename)
    if match:
        return int(match.group(1))
    return None


def get_max_version_in_dir(directory: Path) -> Optional[int]:
    """Find the maximum version number across all MKV files in a directory.

    Returns:
        The highest version found, or None if no versioned files exist.
    """
    if not directory.exists():
        return None

    max_version: Optional[int] = None
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() == ".mkv":
            version = extract_version_from_filename(f.name)
            if version is not None:
                if max_version is None or version > max_version:
                    max_version = version

    return max_version


def get_bgpp_info(input_root: Path, rel_path: Path) -> Optional[int]:
    """Get BGPP version info for a directory.

    Returns:
        None if not a BGPP release (no _work.zip)
        0 if BGPP release but no versioned files
        >= 1 for the max version found in MKV filenames
    """
    source_dir = input_root / rel_path
    if not (source_dir / "_work.zip").exists():
        return None

    max_version = get_max_version_in_dir(source_dir)
    return max_version if max_version is not None else 0


def get_zip_path(output_root: Path, rel_path: Path, bgpp_version: Optional[int] = None) -> Path:
    """Get the zip file path for a given relative directory path.

    Args:
        output_root: The output root directory
        rel_path: The relative path of the directory
        bgpp_version: None = no BGPP tag, 0 = [BGPP], >= 1 = [BGPPvN]
    """
    zips_dir = output_root / "_zips"
    if bgpp_version is None:
        suffix = ""
    elif bgpp_version == 0:
        suffix = " [BGPP]"
    else:
        suffix = f" [BGPPv{bgpp_version}]"

    if rel_path.parent.parts:
        return zips_dir / rel_path.parent / f"{rel_path.name}{suffix}.zip"
    else:
        return zips_dir / f"{rel_path.name}{suffix}.zip"


def cleanup_old_bgpp_zips(output_root: Path, rel_path: Path, current_version: Optional[int], verbose: bool) -> None:
    """Delete all BGPP-related zips that don't match the current version.

    This cleans up:
    - Untagged zips (when BGPP is now needed)
    - [BGPP] zips (when versioned is now needed)
    - [BGPPvN] zips where N != current_version
    """
    zips_dir = output_root / "_zips"
    if rel_path.parent.parts:
        zip_parent = zips_dir / rel_path.parent
    else:
        zip_parent = zips_dir

    if not zip_parent.exists():
        return

    base_name = rel_path.name

    # Build list of zips to check
    candidates = [
        (zip_parent / f"{base_name}.zip", None),  # untagged
        (zip_parent / f"{base_name} [BGPP].zip", 0),  # unversioned BGPP
    ]
    # Check for versioned BGPP zips (v1 through v99)
    for v in range(1, 100):
        candidates.append((zip_parent / f"{base_name} [BGPPv{v}].zip", v))

    # Delete any that don't match current_version
    for zip_path, version in candidates:
        if zip_path.exists() and version != current_version:
            zip_path.unlink()
            if verbose:
                console.print(f"  [yellow]Deleted old zip:[/yellow] {zip_path.relative_to(output_root)}")


def create_zip_for_dir(output_root: Path, rel_path: Path, input_root: Path, dry_run: bool, verbose: bool) -> bool:
    """Create a zip file for a single directory.

    Returns:
        True if zip was created, False otherwise.
    """
    if dry_run:
        return False

    source_dir = output_root / rel_path

    # Skip if source doesn't exist or is empty
    if not source_dir.exists():
        return False

    # Check if there are any files to zip
    has_files = any(f.is_file() and f.suffix.lower() != ".zip" for f in source_dir.rglob("*"))
    if not has_files:
        return False

    # Get BGPP version info (None = not BGPP, 0 = BGPP without version, >= 1 = BGPPvN)
    bgpp_version = get_bgpp_info(input_root, rel_path)

    # Clean up old BGPP zips that don't match current version
    cleanup_old_bgpp_zips(output_root, rel_path, bgpp_version, verbose)

    zip_path = get_zip_path(output_root, rel_path, bgpp_version=bgpp_version)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Create zip excluding .zip files
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in source_dir.rglob("*"):
            if file.is_file() and file.suffix.lower() != ".zip":
                arcname = file.relative_to(source_dir)
                zf.write(file, arcname)

    if verbose:
        console.print(f"  [blue]Zipped:[/blue] {zip_path.relative_to(output_root)}")

    return True


def needs_zip_update(output_root: Path, rel_path: Path, bgpp_version: Optional[int]) -> bool:
    """Check if a zip needs to be created or updated.

    Returns True if:
    - The correct zip doesn't exist
    - An old version zip exists but the version has changed
    """
    correct_zip = get_zip_path(output_root, rel_path, bgpp_version=bgpp_version)
    if not correct_zip.exists():
        return True

    # Check if any old zips exist that need cleanup
    zips_dir = output_root / "_zips"
    if rel_path.parent.parts:
        zip_parent = zips_dir / rel_path.parent
    else:
        zip_parent = zips_dir

    if not zip_parent.exists():
        return False

    base_name = rel_path.name

    # Check for any existing zip that doesn't match current version
    candidates = [
        (zip_parent / f"{base_name}.zip", None),
        (zip_parent / f"{base_name} [BGPP].zip", 0),
    ]
    for v in range(1, 100):
        candidates.append((zip_parent / f"{base_name} [BGPPv{v}].zip", v))

    for zip_path, version in candidates:
        if zip_path.exists() and version != bgpp_version:
            return True  # Old version exists, needs update

    return False


def find_missing_zips(output_root: Path, input_root: Path) -> List[Path]:
    """Find directories that should have zips but don't.

    Returns:
        List of relative paths that need zips created.
    """
    missing = []

    # Find all directories with subtitle files
    for subdir in output_root.iterdir():
        if not subdir.is_dir() or subdir.name == "_zips":
            continue

        rel_path = subdir.relative_to(output_root)

        # Check if this directory has subtitle files directly
        has_direct_subs = any(
            f.is_file() and f.suffix.lower() in SUB_EXTENSIONS
            for f in subdir.iterdir()
        )

        # Check subdirectories (seasons)
        for sub_subdir in subdir.iterdir():
            if sub_subdir.is_dir():
                sub_rel_path = sub_subdir.relative_to(output_root)
                has_subs = any(
                    f.is_file() and f.suffix.lower() in SUB_EXTENSIONS
                    for f in sub_subdir.iterdir()
                )
                if has_subs:
                    bgpp_version = get_bgpp_info(input_root, sub_rel_path)
                    if needs_zip_update(output_root, sub_rel_path, bgpp_version):
                        missing.append(sub_rel_path)

        # Check if parent directory needs zip (has subdirs with subs or direct subs)
        has_any_content = has_direct_subs or any(
            any(f.is_file() and f.suffix.lower() in SUB_EXTENSIONS for f in sub.iterdir())
            for sub in subdir.iterdir() if sub.is_dir()
        )
        if has_any_content:
            bgpp_version = get_bgpp_info(input_root, rel_path)
            if needs_zip_update(output_root, rel_path, bgpp_version):
                missing.append(rel_path)

    return missing


def should_ignore_dir(path: Path, patterns: List[str]) -> bool:
    """Check if any part of the path exactly matches an ignore pattern (case-sensitive)."""
    if not patterns:
        return False
    # Check each component of the path for exact match
    return any(part in patterns for part in path.parts)


def should_ignore_file(filename: str, patterns: List[str]) -> bool:
    """Check if filename contains any ignore pattern (case-insensitive)."""
    if not patterns:
        return False
    name_lower = filename.lower()
    return any(pattern.lower() in name_lower for pattern in patterns)


def get_mkv_files(directory: Path, ignore_file_patterns: List[str]) -> tuple[List[Path], int]:
    """Get all MKV files in a directory (non-recursive), filtering out ignored files.

    Returns:
        Tuple of (list of MKV files, count of ignored files)
    """
    files = []
    ignored = 0
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() == ".mkv":
            if should_ignore_file(f.name, ignore_file_patterns):
                ignored += 1
            else:
                files.append(f)
    return sorted(files), ignored


def has_existing_subs(mkv_file: Path, output_dir: Path) -> bool:
    """Check if any subtitle file or nosubs marker exists for this MKV."""
    if not output_dir.exists():
        return False

    basename = mkv_file.stem

    # Check for nosubs marker (hardsubbed file)
    if (output_dir / f"{basename}.nosubs").exists():
        return True

    for f in output_dir.iterdir():
        if f.is_file() and f.suffix.lower() in SUB_EXTENSIONS:
            # Subtitle files are named: basename.lang.ext or basename.lang-N.ext
            if f.name.startswith(basename + "."):
                return True
    return False


def file_has_subs(mkv_file: Path, output_dir: Path) -> bool:
    """Check if any subtitle file (not marker) exists for this MKV."""
    if not output_dir.exists():
        return False

    basename = mkv_file.stem
    for f in output_dir.iterdir():
        if f.is_file() and f.suffix.lower() in SUB_EXTENSIONS:
            if f.name.startswith(basename + "."):
                return True
    return False


def create_nosubs_marker(mkv_file: Path, output_dir: Path, dry_run: bool) -> None:
    """Create a .nosubs marker for a hardsubbed MKV file."""
    if dry_run:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / f"{mkv_file.stem}.nosubs"
    marker.touch()


def has_subtitle_files(directory: Path) -> bool:
    """Check if directory contains any subtitle files."""
    if not directory.exists():
        return False

    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in SUB_EXTENSIONS:
            return True
    return False


def has_nosubs_markers(directory: Path) -> bool:
    """Check if directory contains any .nosubs marker files."""
    if not directory.exists():
        return False

    for f in directory.iterdir():
        if f.is_file() and f.suffix == ".nosubs":
            return True
    return False


def delete_directory(directory: Path) -> None:
    """Delete a directory and all its contents."""
    if directory.exists():
        shutil.rmtree(directory)


def extract_for_file(mkv_file: Path, output_dir: Path, dry_run: bool) -> bool:
    """Run subattachextract and subextract for a single MKV file (no parallelism)."""
    if dry_run:
        return True

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract attachments (single file, no parallel needed)
    result1 = subprocess.run(
        ["subattachextract", str(mkv_file), "-o", str(output_dir), "-q"],
        capture_output=True,
    )

    # Extract subtitles (single file, no parallel needed)
    result2 = subprocess.run(
        ["subextract", str(mkv_file), "-o", str(output_dir)],
        capture_output=True,
    )

    return result1.returncode == 0 and result2.returncode == 0


def extract_for_directory(input_dir: Path, output_dir: Path, dry_run: bool) -> bool:
    """Run subattachextract and subextract on entire directory with parallelism."""
    if dry_run:
        return True

    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract attachments (parallel on directory)
    result1 = subprocess.run(
        ["subattachextract", str(input_dir), "-o", str(output_dir), "-p", str(PARALLEL_WORKERS), "-q"],
        capture_output=True,
    )

    # Extract subtitles (parallel on directory)
    result2 = subprocess.run(
        ["subextract", str(input_dir), "-o", str(output_dir), "-p", str(PARALLEL_WORKERS)],
        capture_output=True,
    )

    return result1.returncode == 0 and result2.returncode == 0


def process_directory(
    input_dir: Path,
    output_dir: Path,
    rel_path: Path,
    dry_run: bool,
    verbose: bool,
    stats: Stats,
    progress: Progress,
    task_id: int,
    ignore_file_patterns: List[str],
) -> None:
    """Process a single directory containing MKV files."""
    mkv_files, ignored_count = get_mkv_files(input_dir, ignore_file_patterns)
    stats.files_ignored += ignored_count

    if not mkv_files:
        return

    stats.directories_processed += 1

    # Clean up orphaned subtitle files first (source MKV no longer exists)
    orphans_deleted = cleanup_orphaned_subs(
        input_dir, output_dir, dry_run, verbose, stats, progress
    )
    if orphans_deleted:
        stats.dirs_to_zip.add(rel_path)

    # Count subtitle files before extraction (for zip tracking)
    before_count = count_subtitle_files(output_dir)

    # Check if output is empty (first run for this directory)
    output_is_empty = before_count == 0 and (not output_dir.exists() or not any(output_dir.iterdir()))

    # Update progress description with full relative path
    progress.update(task_id, description=f"[cyan]{rel_path}[/cyan]")

    if output_is_empty and ignored_count == 0:
        # First run: extract entire directory with parallelism (only if no ignored files)
        if extract_for_directory(input_dir, output_dir, dry_run):
            stats.files_extracted += len(mkv_files)
            if verbose:
                progress.console.print(f"  [green]Extracted:[/green] {len(mkv_files)} files (parallel)")
            # Create .nosubs markers for hardsubbed files
            for mkv_file in mkv_files:
                if not file_has_subs(mkv_file, output_dir):
                    create_nosubs_marker(mkv_file, output_dir, dry_run)
        else:
            stats.errors.append(f"Failed to extract from directory: {input_dir}")
            if verbose:
                progress.console.print("  [red]Failed:[/red] directory extraction")
    else:
        # Incremental: extract only missing files one by one
        files_to_process = []
        for mkv_file in mkv_files:
            if has_existing_subs(mkv_file, output_dir):
                stats.files_skipped += 1
            else:
                files_to_process.append(mkv_file)

        # If all files were skipped, count as skipped directory
        if not files_to_process:
            stats.directories_skipped += 1
            return

        # Extract missing files one by one
        for mkv_file in files_to_process:
            if extract_for_file(mkv_file, output_dir, dry_run):
                stats.files_extracted += 1
                if verbose:
                    progress.console.print(f"  [green]Extracted:[/green] {mkv_file.name}")
                # Create .nosubs marker if no subs were extracted
                if not file_has_subs(mkv_file, output_dir):
                    create_nosubs_marker(mkv_file, output_dir, dry_run)
            else:
                stats.errors.append(f"Failed to extract from: {mkv_file}")
                if verbose:
                    progress.console.print(f"  [red]Failed:[/red] {mkv_file.name}")

    # Check if any subtitles were extracted
    if not dry_run:
        if has_subtitle_files(output_dir):
            stats.directories_with_subs += 1

            # Check if new subs were added (for zip tracking)
            after_count = count_subtitle_files(output_dir)
            if after_count > before_count:
                stats.dirs_to_zip.add(rel_path)
        elif not has_nosubs_markers(output_dir):
            # No subs and no markers - remove the directory
            delete_directory(output_dir)
            stats.directories_removed += 1
            if verbose:
                progress.console.print("  [dim]Removed (hardsub only)[/dim]")


def find_video_directories(root: Path, ignore_dir_patterns: List[str]) -> tuple[List[Path], int]:
    """Find all directories containing MKV files, filtering out ignored directories.

    Returns:
        Tuple of (list of directories, count of ignored directories)
    """
    dirs_with_mkv: Set[Path] = set()
    ignored_dirs: Set[Path] = set()

    for mkv_file in root.rglob("*.mkv"):
        rel_path = mkv_file.parent.relative_to(root)
        if should_ignore_dir(rel_path, ignore_dir_patterns):
            ignored_dirs.add(mkv_file.parent)
        else:
            dirs_with_mkv.add(mkv_file.parent)

    # Also check for uppercase extension
    for mkv_file in root.rglob("*.MKV"):
        rel_path = mkv_file.parent.relative_to(root)
        if should_ignore_dir(rel_path, ignore_dir_patterns):
            ignored_dirs.add(mkv_file.parent)
        else:
            dirs_with_mkv.add(mkv_file.parent)

    return sorted(dirs_with_mkv), len(ignored_dirs)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build a mirrored directory structure with only subtitles and attachments.")
    parser.add_argument("input_dir", help="Source directory containing TV shows")
    parser.add_argument("output_dir", help="Destination for subs collection")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be done without extracting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    parser.add_argument(
        "--ignore-dir", "-D", action="append", default=[], metavar="NAME",
        help="Ignore directories with exact NAME match (case-sensitive, repeatable)"
    )
    parser.add_argument(
        "--ignore-file", "-F", action="append", default=[], metavar="PATTERN",
        help="Ignore files containing PATTERN (case-insensitive, repeatable)"
    )

    args = parser.parse_args()

    input_root = Path(args.input_dir).resolve()
    output_root = Path(args.output_dir).resolve()

    # Validate input directory
    if not input_root.is_dir():
        console.print(f"[red]Error:[/red] Input directory '{args.input_dir}' does not exist.")
        return 1

    # Check dependencies
    check_dependencies()

    # Create output root if needed
    if not args.dry_run:
        output_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        console.print(Panel("[yellow]DRY-RUN MODE[/yellow] - No files will be extracted", border_style="yellow"))
        console.print()

    # Find all directories with MKV files
    with console.status("[bold blue]Scanning for MKV files...", spinner="dots"):
        video_dirs, ignored_dirs = find_video_directories(input_root, args.ignore_dir)

    if not video_dirs:
        console.print("[yellow]No directories with MKV files found.[/yellow]")
        return 0

    stats = Stats()
    stats.directories_ignored = ignored_dirs

    msg = f"Found [cyan]{len(video_dirs)}[/cyan] directories with MKV files"
    if ignored_dirs:
        msg += f" ([magenta]{ignored_dirs}[/magenta] ignored)"
    console.print(msg + "\n")

    # Check for missing zips and create them
    if not args.dry_run and output_root.exists():
        missing_zips = find_missing_zips(output_root, input_root)
        if missing_zips:
            console.print(f"Creating [cyan]{len(missing_zips)}[/cyan] missing zip files...")
            for rel_path in sorted(missing_zips, key=lambda p: (len(p.parts), str(p)), reverse=True):
                if create_zip_for_dir(output_root, rel_path, input_root, args.dry_run, args.verbose):
                    stats.zips_created += 1
            console.print()

    # Group directories by their first-level parent (series)
    series_dirs: dict[Path, List[Path]] = {}
    for video_dir in video_dirs:
        rel_path = video_dir.relative_to(input_root)
        # First part is the series name
        series = Path(rel_path.parts[0]) if rel_path.parts else rel_path
        if series not in series_dirs:
            series_dirs[series] = []
        series_dirs[series].append(video_dir)

    # Process each directory with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=not args.verbose,
    ) as progress:
        task = progress.add_task("[cyan]Processing...", total=len(video_dirs))

        for series, dirs_in_series in series_dirs.items():
            series_needs_zip = False

            for video_dir in dirs_in_series:
                # Compute relative path and corresponding output directory
                rel_path = video_dir.relative_to(input_root)
                out_dir = output_root / rel_path

                # Track dirs_to_zip size before processing
                zip_count_before = len(stats.dirs_to_zip)

                process_directory(video_dir, out_dir, rel_path, args.dry_run, args.verbose, stats, progress, task, args.ignore_file)
                progress.advance(task)

                # If this directory needs zipping (was added to dirs_to_zip), zip it immediately
                if len(stats.dirs_to_zip) > zip_count_before and rel_path in stats.dirs_to_zip:
                    if create_zip_for_dir(output_root, rel_path, input_root, args.dry_run, args.verbose):
                        stats.zips_created += 1
                        series_needs_zip = True

            # After all directories in this series are done, zip the series itself
            if series_needs_zip and len(series.parts) > 0:
                if create_zip_for_dir(output_root, series, input_root, args.dry_run, args.verbose):
                    stats.zips_created += 1

    # Print summary
    stats.print_summary()

    if stats.errors:
        console.print()
        console.print("[red]Errors encountered:[/red]")
        for error in stats.errors:
            console.print(f"  [dim]•[/dim] {error}")
        return 1

    console.print("\n[green]Done.[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
