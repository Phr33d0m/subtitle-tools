#!/usr/bin/env python3

"""
Video OCR Processing Tool
Transforms video files into SRT subtitles using VideOCR CLI with parallel processing.
"""

import argparse
import concurrent.futures
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import threading
import time
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.console import Group
from rich import box
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn

# === CONFIGURATION CONSTANTS ===
# Edit these values as needed for your setup

# Full path to videocr.py CLI
BINARY_PATH = Path("/mnt/FAST/Code/videocr-PaddleOCR-original/videocr.py")

# File patterns to process when no argument is provided
DEFAULT_EXTENSIONS = ["*.mp4", "*.mkv"]

# Default concurrency for parallel mode (0 = auto-detect)
DEFAULT_CONCURRENCY = 0

# OCR Processing Parameters (matching videocr.py defaults)
DEFAULT_LANG = "ch"
DEFAULT_CONF_THRESHOLD = 70
DEFAULT_TIME_START = None
DEFAULT_TIME_END = None
DEFAULT_SIM_THRESHOLD = 70
DEFAULT_BRIGHTNESS_THRESHOLD = 145
DEFAULT_SIMILAR_IMAGE = 80
DEFAULT_SIMILAR_PIXEL = 25
DEFAULT_FRAMES_TO_SKIP = 0

# GPU/CPU Settings
DEFAULT_USE_GPU = True

# === END CONFIGURATION CONSTANTS ===


class FileStatus(Enum):
    """File processing status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FileProgress:
    """Track per-file processing state."""

    file_path: Path
    status: FileStatus
    worker_id: Optional[int] = None
    start_time: Optional[float] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class CropConfig:
    """Configuration for video crop region."""

    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_string(cls, crop_str: str) -> "CropConfig":
        """Parse crop configuration from 'x,y,width,height' string."""
        try:
            x, y, width, height = map(int, crop_str.split(","))
            return cls(x=x, y=y, width=width, height=height)
        except ValueError:
            raise argparse.ArgumentTypeError("Crop must be four comma-separated integers: 'x,y,width,height'")


@dataclass
class ProcessingConfig:
    """Configuration for video processing."""

    crop: CropConfig
    time_start: Optional[str] = DEFAULT_TIME_START
    time_end: Optional[str] = DEFAULT_TIME_END
    brightness_threshold: int = DEFAULT_BRIGHTNESS_THRESHOLD
    max_workers: int = DEFAULT_CONCURRENCY
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False


class VideoProcessor:
    """Handles video OCR processing operations."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.console = Console(quiet=self.config.quiet)
        self._file_progress: List[FileProgress] = []
        self._progress_lock = threading.Lock()

    def _create_table(self, max_workers: int) -> Table:
        """Create Rich table for displaying file processing status."""
        table = Table(expand=True, show_header=True, header_style="bold cyan", box=box.SIMPLE_HEAD)

        table.add_column("File", style="cyan", no_wrap=True, ratio=3)
        table.add_column("Status", style="yellow", no_wrap=True, ratio=1)
        table.add_column("Duration", style="magenta", no_wrap=True, ratio=1)

        return table

    def _get_status_text(self, status: FileStatus) -> str:
        """Get formatted status text without emoji."""
        return status.value.title()

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

    def _create_summary(self, successful: int, failed: int, total: int) -> Table:
        """Create summary table showing overall progress."""
        summary = Table(show_header=False, box=None, padding=0)
        summary.add_column("", style="bold")
        summary.add_column("", justify="right")

        summary.add_row("Total Files:", str(total))
        summary.add_row("Successful:", str(successful))
        summary.add_row("Failed:", str(failed))

        return summary

    def _update_table_rows(self, table: Table, max_workers: int) -> None:
        """Update table rows with current file progress including real-time duration."""
        with self._progress_lock:
            # Sort files: first by active workers, then by status priority
            status_priority = {
                FileStatus.PROCESSING: 0,
                FileStatus.QUEUED: 1,
                FileStatus.FAILED: 2,
                FileStatus.COMPLETED: 3,
            }

            sorted_files = sorted(self._file_progress, key=lambda fp: (status_priority.get(fp.status, 4), fp.file_path.name))

            # Show exactly max_workers rows
            display_files = sorted_files[:max_workers]

            for file_prog in display_files:
                status_text = self._get_status_text(file_prog.status)

                # Calculate real-time duration for active files
                if file_prog.status == FileStatus.PROCESSING and file_prog.start_time is not None:
                    current_time = time.time()
                    elapsed = current_time - file_prog.start_time
                    duration = self._format_duration(elapsed)
                else:
                    duration = self._format_duration(file_prog.duration)

                table.add_row(file_prog.file_path.name, status_text, duration)

    def _validate_binary(self) -> None:
        """Validate that the VideOCR binary exists and is executable."""
        if not BINARY_PATH.exists():
            raise FileNotFoundError(f"VideOCR binary not found: {BINARY_PATH}")
        if not os.access(BINARY_PATH, os.X_OK):
            raise PermissionError(f"VideOCR binary is not executable: {BINARY_PATH}")

    def _build_command(self, video_path: Path, output_path: Path) -> List[str]:
        """Build the VideOCR command with all parameters."""
        # Build crop string from config
        crop_str = f"{self.config.crop.x},{self.config.crop.y},{self.config.crop.width},{self.config.crop.height}"

        cmd = [
            str(BINARY_PATH),
            str(video_path),  # positional argument
            "-o",
            str(output_path),
            "-l",
            DEFAULT_LANG,
            "--crop",
            crop_str,
            "-c",
            str(DEFAULT_CONF_THRESHOLD),
            "-s",
            str(DEFAULT_SIM_THRESHOLD),
            "-b",
            str(self.config.brightness_threshold),
            "--similar-image",
            str(DEFAULT_SIMILAR_IMAGE),
            "--similar-pixel",
            str(DEFAULT_SIMILAR_PIXEL),
            "--skip",
            str(DEFAULT_FRAMES_TO_SKIP),
        ]

        # GPU flag
        if not DEFAULT_USE_GPU:
            cmd.append("--no-gpu")

        # Conditionally add time arguments only if they contain values
        if self.config.time_start:
            cmd.extend(["-ts", self.config.time_start])

        if self.config.time_end:
            cmd.extend(["-te", self.config.time_end])

        return cmd

    def _update_file_progress(self, file_path: Path, status: FileStatus, worker_id: Optional[int] = None, duration: Optional[float] = None, error_message: Optional[str] = None) -> None:
        """Update file progress information."""
        with self._progress_lock:
            # Find existing progress entry or create new one
            for prog in self._file_progress:
                if prog.file_path == file_path:
                    prog.status = status
                    prog.worker_id = worker_id
                    prog.duration = duration
                    prog.error_message = error_message
                    prog.start_time = time.time() if status == FileStatus.PROCESSING else prog.start_time
                    return

            # Create new entry if not found
            start_time = time.time() if status == FileStatus.PROCESSING else None
            self._file_progress.append(FileProgress(file_path=file_path, status=status, worker_id=worker_id, start_time=start_time, duration=duration, error_message=error_message))

    def process_video(self, video_path: Path, worker_id: Optional[int] = None) -> bool:
        """Process a single video file.

        Args:
            video_path: Path to the video file
            worker_id: ID of the worker processing this file

        Returns:
            True if processing succeeded, False otherwise
        """
        # Convert to absolute path
        abs_video = video_path.resolve()
        output_path = abs_video.with_suffix(".srt")

        # Handle dry-run mode
        if self.config.dry_run:
            cmd = self._build_command(abs_video, output_path)
            self.console.print(f"- {' '.join(cmd)}")
            return True

        start_time = time.time()

        # Update progress to processing
        self._update_file_progress(abs_video, FileStatus.PROCESSING, worker_id=worker_id)

        try:
            cmd = self._build_command(abs_video, output_path)

            if self.config.verbose:
                self.console.print(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                self._update_file_progress(abs_video, FileStatus.COMPLETED, worker_id=worker_id, duration=elapsed)
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self._update_file_progress(abs_video, FileStatus.FAILED, worker_id=worker_id, duration=elapsed, error_message=error_msg)
                return False

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self._update_file_progress(abs_video, FileStatus.FAILED, worker_id=worker_id, duration=elapsed, error_message="Timeout (1 hour)")
            return False
        except Exception as e:
            elapsed = time.time() - start_time
            self._update_file_progress(abs_video, FileStatus.FAILED, worker_id=worker_id, duration=elapsed, error_message=str(e))
            return False

    def find_video_files(self, directory: Path) -> List[Path]:
        """Find video files in the given directory."""
        video_files = []
        for ext in DEFAULT_EXTENSIONS:
            video_files.extend(directory.glob(ext))
        return sorted(video_files)

    def process_videos_parallel(self, video_files: List[Path]) -> Tuple[int, int]:
        """Process multiple video files in parallel with Rich Live table display.

        Args:
            video_files: List of video file paths

        Returns:
            Tuple of (successful_count, total_count)
        """
        if not video_files:
            self.console.print("No video files found")
            return 0, 0

        # Determine number of workers
        max_workers = self.config.max_workers
        if max_workers <= 0:
            max_workers = os.cpu_count() or 4

        # Initialize all files as queued
        abs_videos = [video.resolve() for video in video_files]
        for video in abs_videos:
            self._update_file_progress(video, FileStatus.QUEUED)

        successful = 0
        failed = 0
        total = len(abs_videos)

        # Thread-safe counters
        lock = threading.Lock()

        def process_with_worker_id(video_path: Path, worker_id: int) -> None:
            nonlocal successful, failed
            if self.process_video(video_path, worker_id):
                with lock:
                    successful += 1
            else:
                with lock:
                    failed += 1

        # Start processing in background
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks with worker IDs
            worker_counter = 0

            def get_next_worker_id():
                nonlocal worker_counter
                worker_id = worker_counter % max_workers + 1
                worker_counter += 1
                return worker_id

            # Submit tasks
            futures = [executor.submit(process_with_worker_id, video, get_next_worker_id()) for video in abs_videos]

            # Use proper Rich Live context manager for display updates
            if not self.config.quiet:
                # Create overall progress bar
                overall_progress = Progress(SpinnerColumn(), BarColumn(), TextColumn("{task.description}"), TimeRemainingColumn(), console=self.console)
                progress_task = overall_progress.add_task("Processing files...", total=total)

                # Track completion status for chi-to-eng pattern
                all_files_completed = False

                with Live(console=self.console, auto_refresh=True) as live:
                    # Continuous update loop with 1-second intervals like chi-to-eng
                    while not all_files_completed:
                        # Create current display
                        table = self._create_table(max_workers)
                        self._update_table_rows(table, max_workers)

                        # Wrap table in Panel
                        dashboard_panel = Panel(table, title="Video OCR Processing Status", border_style="blue", padding=(0, 1))

                        # Update progress bar
                        completed = successful + failed
                        overall_progress.update(progress_task, completed=completed)

                        # Update with Group containing panel and progress (chi-to-eng pattern)
                        live.update(Group(dashboard_panel, overall_progress))

                        # Check if all processing is complete
                        with lock:
                            if completed >= total:
                                all_files_completed = True
                                break

                        # Sleep for exactly 1 second (chi-to-eng pattern)
                        time.sleep(1)
            else:
                # Quiet mode: just wait for completion
                concurrent.futures.wait(futures)

        # Print final summary
        if not self.config.quiet:
            self.console.print()
            self.console.print(f"Completed: {successful} successful, {failed} failed")

        return successful, total


def parse_arguments() -> Tuple[ProcessingConfig, List[Path]]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Process video files to extract subtitles using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --crops '1156,1383,1546,178'                    # Process all videos in current directory
  %(prog)s --crops '1156,1383,1546,178' video.mp4         # Process single video
  %(prog)s --crops '1156,1383,1546,178' -ts '02:30'       # Start from 2:30
  %(prog)s --crops '1156,1383,1546,178' -b 180            # Brightness threshold 180
  %(prog)s --crops '1156,1383,1546,178' --max 4           # Use 4 parallel workers
  %(prog)s --crops '1156,1383,1546,178' --dry-run         # Show commands without executing
        """,
    )

    # Required arguments
    parser.add_argument("--crops", type=CropConfig.from_string, required=True, help='Crop region as "x,y,width,height" (required)')

    # Optional arguments
    parser.add_argument("-ts", "--time-start", type=str, default=DEFAULT_TIME_START, help=f"Start time for OCR (default: {DEFAULT_TIME_START})")

    parser.add_argument("-te", "--time-end", type=str, default=DEFAULT_TIME_END, help=f"End time for OCR (default: {DEFAULT_TIME_END})")

    parser.add_argument("-b", "--brightness", type=int, default=DEFAULT_BRIGHTNESS_THRESHOLD, help=f"Brightness threshold (default: {DEFAULT_BRIGHTNESS_THRESHOLD})")

    parser.add_argument("--max", type=int, default=DEFAULT_CONCURRENCY, help="Maximum parallel workers (default: auto-detect)")

    # Output control
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    output_group.add_argument("-q", "--quiet", action="store_true", help="Suppress non-error output")

    parser.add_argument("--dry-run", action="store_true", help="Show commands that would be executed without running them")

    # Positional arguments
    parser.add_argument("files", nargs="*", help="Video files to process (default: all videos in current directory)")

    args = parser.parse_args()

    # Handle dry-run mode: ignore user's --max argument and always process sequentially
    max_workers = 1 if getattr(args, "dry_run", False) else args.max

    # Create processing configuration
    config = ProcessingConfig(crop=args.crops, time_start=args.time_start, time_end=args.time_end, brightness_threshold=args.brightness, max_workers=max_workers, verbose=args.verbose, quiet=args.quiet, dry_run=getattr(args, "dry_run", False))

    # Handle file arguments
    if args.files:
        video_files = [Path(f) for f in args.files]
    else:
        # No files specified, use current directory
        video_files = []

    return config, video_files


def main() -> int:
    """Main entry point."""
    try:
        config, specified_files = parse_arguments()

        # Create processor
        processor = VideoProcessor(config)

        # Skip validation in dry-run mode
        if not config.dry_run:
            processor._validate_binary()

        # Determine which files to process
        if specified_files:
            video_files = []
            for file_path in specified_files:
                if file_path.is_file():
                    video_files.append(file_path)
                else:
                    processor.console.print(f"File not found: {file_path}")
                    return 1
        else:
            # Find video files in current directory
            video_files = processor.find_video_files(Path.cwd())

        if not video_files:
            processor.console.print("No video files found")
            return 1

        # Process files
        if config.dry_run:
            # Dry-run mode: process sequentially without validation messages
            for video_file in video_files:
                processor.process_video(video_file)
            return 0
        else:
            # All processing with Rich Live table (single or multiple files)
            successful, total = processor.process_videos_parallel(video_files)
            return 0 if successful == total else 1

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
