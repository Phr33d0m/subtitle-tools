#!/usr/bin/env python3

"""
Video OCR Processing Tool
Transforms video files into SRT subtitles using VideOCR CLI with parallel processing.
"""

import argparse
import concurrent.futures
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import threading
import time

# === CONFIGURATION CONSTANTS ===
# Edit these values as needed for your setup

# Absolute path to your videocr binary
BINARY_PATH = Path(
    "/UPDATE/THIS/PATH/TO/YOUR/OWN/videocr-cli-GPU-v1.3.2-Linux/videocr-cli.bin"
)

# File patterns to process when no argument is provided
DEFAULT_EXTENSIONS = ["*.mp4", "*.mkv", "*.avi"]

# Default concurrency for parallel mode (0 = auto-detect)
DEFAULT_CONCURRENCY = 0

# OCR Processing Parameters
DEFAULT_LANG = "chinese_cht"
DEFAULT_SUBTITLE_POSITION = "center"
DEFAULT_CONF_THRESHOLD = 75
DEFAULT_TIME_START = "01:50"
DEFAULT_SIM_THRESHOLD = 80
DEFAULT_MAX_MERGE_GAP = 0.2
DEFAULT_BRIGHTNESS_THRESHOLD = 165
DEFAULT_SSIM_THRESHOLD = 92
DEFAULT_OCR_IMAGE_MAX_WIDTH = 1520
DEFAULT_FRAMES_TO_SKIP = 1
DEFAULT_MIN_SUBTITLE_DURATION = 0.1

# GPU/CPU Settings
DEFAULT_USE_GPU = True
DEFAULT_USE_FULLFRAME = False
DEFAULT_USE_DUAL_ZONE = False
DEFAULT_USE_ANGLE_CLS = False
DEFAULT_POST_PROCESSING = True
DEFAULT_USE_SERVER_MODEL = False

# === END CONFIGURATION CONSTANTS ===


@dataclass
class CropConfig:
    """Configuration for video crop region."""
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_string(cls, crop_str: str) -> 'CropConfig':
        """Parse crop configuration from 'x,y,width,height' string."""
        try:
            x, y, width, height = map(int, crop_str.split(','))
            return cls(x=x, y=y, width=width, height=height)
        except ValueError:
            raise argparse.ArgumentTypeError(
                "Crop must be four comma-separated integers: 'x,y,width,height'"
            )


@dataclass
class ProcessingConfig:
    """Configuration for video processing."""
    crop: CropConfig
    time_start: str = DEFAULT_TIME_START
    brightness_threshold: int = DEFAULT_BRIGHTNESS_THRESHOLD
    max_workers: int = DEFAULT_CONCURRENCY
    verbose: bool = False
    quiet: bool = False


class VideoProcessor:
    """Handles video OCR processing operations."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        level = logging.DEBUG if self.config.verbose else logging.INFO
        if self.config.quiet:
            level = logging.WARNING

        logging.basicConfig(
            level=level,
            format='[%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def _validate_binary(self) -> None:
        """Validate that the VideOCR binary exists and is executable."""
        if not BINARY_PATH.exists():
            raise FileNotFoundError(f"VideOCR binary not found: {BINARY_PATH}")
        if not os.access(BINARY_PATH, os.X_OK):
            raise PermissionError(
                f"VideOCR binary is not executable: {BINARY_PATH}")

    def _build_command(self, video_path: Path, output_path: Path) -> List[str]:
        """Build the VideOCR command with all parameters."""
        cmd = [
            str(BINARY_PATH),
            "--video_path", str(video_path),
            "--lang", DEFAULT_LANG,
            "--subtitle_position", DEFAULT_SUBTITLE_POSITION,
            "--output", str(output_path),
            "--conf_threshold", str(DEFAULT_CONF_THRESHOLD),
            "--time_start", self.config.time_start,
            "--sim_threshold", str(DEFAULT_SIM_THRESHOLD),
            "--max_merge_gap", str(DEFAULT_MAX_MERGE_GAP),
            "--brightness_threshold", str(self.config.brightness_threshold),
            "--ssim_threshold", str(DEFAULT_SSIM_THRESHOLD),
            "--ocr_image_max_width", str(DEFAULT_OCR_IMAGE_MAX_WIDTH),
            "--frames_to_skip", str(DEFAULT_FRAMES_TO_SKIP),
            "--min_subtitle_duration", str(DEFAULT_MIN_SUBTITLE_DURATION),
            "--use_gpu", str(DEFAULT_USE_GPU).lower(),
            "--use_fullframe", str(DEFAULT_USE_FULLFRAME).lower(),
            "--use_dual_zone", str(DEFAULT_USE_DUAL_ZONE).lower(),
            "--use_angle_cls", str(DEFAULT_USE_ANGLE_CLS).lower(),
            "--post_processing", str(DEFAULT_POST_PROCESSING).lower(),
            "--use_server_model", str(DEFAULT_USE_SERVER_MODEL).lower(),
            "--crop_x", str(self.config.crop.x),
            "--crop_y", str(self.config.crop.y),
            "--crop_width", str(self.config.crop.width),
            "--crop_height", str(self.config.crop.height),
        ]
        return cmd

    def process_video(self, video_path: Path) -> bool:
        """Process a single video file.

        Args:
            video_path: Path to the video file

        Returns:
            True if processing succeeded, False otherwise
        """
        # Convert to absolute path
        abs_video = video_path.resolve()
        output_path = abs_video.with_suffix('.srt')

        self.logger.info(f"Processing: {abs_video} -> {output_path}")
        start_time = time.time()

        try:
            cmd = self._build_command(abs_video, output_path)

            if self.config.verbose:
                self.logger.debug(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                elapsed = time.time() - start_time
                self.logger.info(f"Completed in {elapsed:.1f}s: {abs_video}")
                return True
            else:
                self.logger.error(f"Failed to process {abs_video}")
                if result.stderr:
                    self.logger.error(f"Error: {result.stderr.strip()}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout processing {abs_video}")
            return False
        except Exception as e:
            self.logger.error(f"Error processing {abs_video}: {e}")
            return False

    def find_video_files(self, directory: Path) -> List[Path]:
        """Find video files in the given directory."""
        video_files = []
        for ext in DEFAULT_EXTENSIONS:
            video_files.extend(directory.glob(ext))
        return sorted(video_files)

    def process_videos_parallel(self, video_files: List[Path]) -> Tuple[int, int]:
        """Process multiple video files in parallel.

        Args:
            video_files: List of video file paths

        Returns:
            Tuple of (successful_count, total_count)
        """
        if not video_files:
            self.logger.warning("No video files found")
            return 0, 0

        # Determine number of workers
        max_workers = self.config.max_workers
        if max_workers <= 0:
            max_workers = os.cpu_count() or 4

        self.logger.info(
            f"Processing {len(video_files)} files with {max_workers} workers")

        successful = 0
        failed = 0

        # Thread-safe counters
        lock = threading.Lock()

        def process_with_counter(video_path: Path) -> None:
            nonlocal successful, failed
            if self.process_video(video_path):
                with lock:
                    successful += 1
            else:
                with lock:
                    failed += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(process_with_counter, video)
                       for video in video_files]

            # Wait for completion with progress indication
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                if not self.config.quiet:
                    print(
                        f"\rProgress: {completed}/{len(video_files)}", end='', flush=True)

        if not self.config.quiet:
            print()  # New line after progress

        self.logger.info(
            f"Completed: {successful} successful, {failed} failed")
        return successful, successful + failed


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
        """
    )

    # Required arguments
    parser.add_argument(
        '--crops',
        type=CropConfig.from_string,
        required=True,
        help='Crop region as "x,y,width,height" (required)'
    )

    # Optional arguments
    parser.add_argument(
        '-ts', '--time-start',
        type=str,
        default=DEFAULT_TIME_START,
        help=f'Start time for OCR (default: {DEFAULT_TIME_START})'
    )

    parser.add_argument(
        '-b', '--brightness',
        type=int,
        default=DEFAULT_BRIGHTNESS_THRESHOLD,
        help=f'Brightness threshold (default: {DEFAULT_BRIGHTNESS_THRESHOLD})'
    )

    parser.add_argument(
        '--max',
        type=int,
        default=DEFAULT_CONCURRENCY,
        help='Maximum parallel workers (default: auto-detect)'
    )

    # Output control
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    output_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress non-error output'
    )

    # Positional arguments
    parser.add_argument(
        'files',
        nargs='*',
        help='Video files to process (default: all videos in current directory)'
    )

    args = parser.parse_args()

    # Create processing configuration
    config = ProcessingConfig(
        crop=args.crops,
        time_start=args.time_start,
        brightness_threshold=args.brightness,
        max_workers=args.max,
        verbose=args.verbose,
        quiet=args.quiet
    )

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

        # Create processor and validate binary
        processor = VideoProcessor(config)
        processor._validate_binary()

        # Determine which files to process
        if specified_files:
            video_files = []
            for file_path in specified_files:
                if file_path.is_file():
                    video_files.append(file_path)
                else:
                    processor.logger.error(f"File not found: {file_path}")
                    return 1
        else:
            # Find video files in current directory
            video_files = processor.find_video_files(Path.cwd())

        if not video_files:
            processor.logger.error("No video files found")
            return 1

        # Process files
        if len(video_files) == 1:
            # Single file processing
            success = processor.process_video(video_files[0])
            return 0 if success else 1
        else:
            # Parallel processing
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
