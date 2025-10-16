#!/usr/bin/env python3
"""
submerge.py — Merge subtitle files into video containers using mkvmerge.

This tool finds video files and their matching subtitle files, then merges them
into MKV containers with proper language metadata and font attachments.

Behavior:
- No argument: process all videos in current directory
- Directory argument: process all videos in that directory
- Supports both IETF language tags (zh-Hans, pt-BR) and traditional 3-letter codes (eng, chi)
- Priority: ASS subtitles > SRT subtitles
- Optionally embeds fonts from Fonts/ directory for ASS subtitles

Requirements: mkvmerge, file
"""

from __future__ import annotations

import argparse
import concurrent.futures
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set


# ------------------------------ Constants ------------------------------ #

DEFAULT_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.MP4', '.MKV'}
DEFAULT_SUBTITLE_EXTENSIONS = {'.ass', '.srt', '.ASS', '.SRT'}
FONTS_DIR_NAME = "Fonts"

# Format priority: higher number = higher priority
SUBTITLE_FORMAT_PRIORITY = {
    '.ass': 2,
    '.ASS': 2,
    '.srt': 1,
    '.SRT': 1,
}


# ------------------------------ Data Structures ------------------------------ #

@dataclass(frozen=True)
class SubtitleFile:
    """Represents a subtitle file with its metadata."""
    path: Path
    language_code: str
    extension: str
    priority: int

    @classmethod
    def from_path(cls, path: Path) -> Optional[SubtitleFile]:
        """Create SubtitleFile from path, extracting language code from compound extension."""
        if path.suffix not in DEFAULT_SUBTITLE_EXTENSIONS:
            return None

        # Parse compound extension like ".zh-Hans.ass" or ".eng.srt"
        stem = path.stem
        parts = stem.split('.')

        if len(parts) >= 2:
            # Last part is the base name, second to last is language code
            language_code = parts[-1]
        elif len(parts) == 1:
            # No language code found
            return None
        else:
            return None

        extension = path.suffix
        priority = SUBTITLE_FORMAT_PRIORITY.get(extension, 0)

        return cls(
            path=path,
            language_code=language_code,
            extension=extension,
            priority=priority
        )


@dataclass(frozen=True)
class FontAttachment:
    """Represents a font file for attachment."""
    path: Path
    mime_type: str


@dataclass
class ProcessingStats:
    """Statistics for video processing operations."""
    total_videos: int = 0
    processed_videos: int = 0
    skipped_videos: int = 0
    failed_videos: int = 0
    fonts_embedded: int = 0

    def __str__(self) -> str:
        return (f"Processing complete:\n"
                f"  Total videos found: {self.total_videos}\n"
                f"  Successfully processed: {self.processed_videos}\n"
                f"  Skipped: {self.skipped_videos}\n"
                f"  Failed: {self.failed_videos}\n"
                f"  Fonts embedded: {self.fonts_embedded}")


# ------------------------------ Utilities ------------------------------ #

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S'
    )


def check_dependencies() -> None:
    """Ensure required external commands are available."""
    missing_commands = []

    for cmd in ['mkvmerge', 'file']:
        if shutil.which(cmd) is None:
            missing_commands.append(cmd)

    if missing_commands:
        logging.error("Required commands not found: %s",
                      ', '.join(missing_commands))
        logging.error(
            "Please install MKVToolNix and ensure 'file' command is available")
        sys.exit(1)


def get_mime_type(file_path: Path) -> str:
    """Get MIME type of a file using the 'file' command."""
    try:
        result = subprocess.run(
            ['file', '--brief', '--mime-type', str(file_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logging.warning("Failed to detect MIME type for %s: %s",
                        file_path.name, e)
        return "application/octet-stream"


def normalize_language_code(language_code: str) -> str:
    """Normalize language code for mkvmerge."""
    # For IETF tags like zh-Hans, pt-BR, mkvmerge accepts them as-is
    # For 3-letter codes like eng, chi, also accept as-is
    # Just ensure proper formatting
    return language_code.strip()


# ------------------------------ Core Functions ------------------------------ #

def find_video_files(root_dir: Path) -> List[Path]:
    """Find all video files in the given directory tree."""
    video_files = []

    for ext in DEFAULT_VIDEO_EXTENSIONS:
        video_files.extend(root_dir.rglob(f"*{ext}"))

    return sorted(video_files)


def find_subtitle_files(base_path: Path) -> List[SubtitleFile]:
    """Find subtitle files matching the given base path."""
    subtitle_files = []

    # Get the base name without extension
    base_name = base_path.name

    # Look for all subtitle files in the same directory
    for ext in DEFAULT_SUBTITLE_EXTENSIONS:
        for sub_path in base_path.parent.glob(f"*{ext}"):
            # Check if the subtitle file matches the video base name plus language code
            # Remove the language code and extension from subtitle file name to get the video base name
            sub_stem = sub_path.stem  # Everything before the extension
            sub_parts = sub_stem.split('.')

            if len(sub_parts) >= 2:
                # The language code should be the last part
                potential_lang_code = sub_parts[-1]
                potential_base_name = '.'.join(sub_parts[:-1])

                # Check if the base name matches
                if potential_base_name == base_name:
                    subtitle_file = SubtitleFile.from_path(sub_path)
                    if subtitle_file:
                        subtitle_files.append(subtitle_file)

    # Sort by priority (higher first), then by language code
    subtitle_files.sort(key=lambda x: (-x.priority, x.language_code))

    return subtitle_files


def collect_font_attachments(root_dir: Path) -> List[FontAttachment]:
    """Collect font files from the Fonts directory."""
    fonts_dir = root_dir / FONTS_DIR_NAME

    if not fonts_dir.is_dir():
        logging.debug("No Fonts directory found in %s", root_dir)
        return []

    logging.info("Fonts directory detected: %s", fonts_dir)

    font_attachments = []
    font_extensions = {'.ttf', '.otf', '.ttc', '.woff',
                       '.woff2', '.TTF', '.OTF', '.TTC', '.WOFF', '.WOFF2'}

    for font_path in fonts_dir.rglob('*'):
        if font_path.is_file() and font_path.suffix in font_extensions:
            mime_type = get_mime_type(font_path)
            font_attachments.append(FontAttachment(
                path=font_path, mime_type=mime_type))

    if font_attachments:
        logging.info("Found %d font file(s) for attachment",
                     len(font_attachments))

    return font_attachments


def merge_video_with_subtitle(
    video_path: Path,
    subtitle_file: SubtitleFile,
    font_attachments: List[FontAttachment],
    temp_dir: Optional[Path],
    dry_run: bool = False
) -> bool:
    """Merge video file with subtitle using mkvmerge."""

    base_name = video_path.stem
    output_path = video_path.parent / f"{base_name}.mkv"
    # Create temp file in the same directory to avoid cross-device link issues
    temp_output = output_path.with_suffix('.mkv.temp')

    # Build mkvmerge command
    cmd = [
        'mkvmerge',
        '-q',  # Quiet mode
        '-o', str(temp_output),
        '--no-subtitles', str(video_path),
        '--language', '0:' +
        normalize_language_code(subtitle_file.language_code),
        '--track-name', '0:' + subtitle_file.language_code.upper(),
        '--default-track-flag', '0:yes',
        str(subtitle_file.path)
    ]

    # Add font attachments if available and subtitle format requires fonts (ASS)
    if subtitle_file.extension.lower() == '.ass' and font_attachments:
        logging.info("Embedding %d font(s) into MKV", len(font_attachments))
        for font in font_attachments:
            cmd.extend([
                '--attachment-mime-type', font.mime_type,
                '--attach-file', str(font.path)
            ])

    if dry_run:
        logging.info("DRY RUN: Would execute: %s", ' '.join(cmd))
        return True

    # Clean up any existing temp file
    if temp_output.exists():
        temp_output.unlink()

    # Execute mkvmerge
    try:
        logging.debug("Executing: %s", ' '.join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        # Verify the temp file was created successfully
        if not temp_output.exists() or temp_output.stat().st_size == 0:
            logging.error("mkvmerge output file is missing or empty")
            return False

        # Replace original files safely
        backup_video = video_path.with_suffix(video_path.suffix + '.bak')
        backup_sub = subtitle_file.path.with_suffix(
            subtitle_file.path.suffix + '.bak')

        try:
            # Create backups
            if video_path.exists():
                video_path.rename(backup_video)
            if subtitle_file.path.exists():
                subtitle_file.path.rename(backup_sub)

            # Move temp file to final location (same device, so rename works)
            temp_output.rename(output_path)

            # Remove backups after successful merge
            if backup_video.exists():
                backup_video.unlink()
            if backup_sub.exists():
                backup_sub.unlink()

            logging.info("✓ Created: %s", output_path)
            return True

        except Exception as e:
            # Restore backups if something went wrong
            logging.error(
                "Failed to replace files, attempting to restore backups: %s", e)
            if backup_video.exists():
                backup_video.rename(video_path)
            if backup_sub.exists():
                backup_sub.rename(subtitle_file.path)
            if temp_output.exists():
                temp_output.unlink()
            return False

    except subprocess.CalledProcessError as e:
        logging.error("mkvmerge failed for %s: %s", video_path.name,
                      e.stderr.decode() if e.stderr else str(e))
        if temp_output.exists():
            temp_output.unlink()
        return False
    except subprocess.TimeoutExpired:
        logging.error("mkvmerge timed out for %s", video_path.name)
        if temp_output.exists():
            temp_output.unlink()
        return False


def process_single_video(
    video_path: Path,
    subtitle_files: List[SubtitleFile],
    font_attachments: List[FontAttachment],
    temp_dir: Optional[Path],
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Process a single video file."""

    if not subtitle_files:
        return False, f"No matching subtitle files found for {video_path.name}"

    # Use the highest priority subtitle file
    selected_subtitle = subtitle_files[0]

    logging.info("Processing %s with %s", video_path.name,
                 selected_subtitle.path.name)

    success = merge_video_with_subtitle(
        video_path=video_path,
        subtitle_file=selected_subtitle,
        font_attachments=font_attachments,
        temp_dir=temp_dir,
        dry_run=dry_run
    )

    if success:
        return True, f"Successfully merged {selected_subtitle.path.name} into {video_path.name}"
    else:
        return False, f"Failed to merge {selected_subtitle.path.name} into {video_path.name}"


def process_videos(
    video_files: List[Path],
    font_attachments: List[FontAttachment],
    max_workers: int = 1,
    dry_run: bool = False
) -> ProcessingStats:
    """Process multiple video files with optional parallelization."""

    stats = ProcessingStats()
    stats.total_videos = len(video_files)

    if not video_files:
        logging.info("No video files found to process")
        return stats

    if max_workers == 1:
        # Sequential processing
        for video_path in video_files:
            base_path = video_path.with_suffix('')
            subtitle_files = find_subtitle_files(base_path)

            if not subtitle_files:
                logging.warning(
                    "- No matching subtitle files for %s → skipping", video_path.name)
                stats.skipped_videos += 1
                continue

            success, message = process_single_video(
                video_path, subtitle_files, font_attachments, None, dry_run
            )

            if success:
                stats.processed_videos += 1
                if subtitle_files[0].extension.lower() == '.ass' and font_attachments:
                    stats.fonts_embedded += len(font_attachments)
            else:
                stats.failed_videos += 1
                logging.error(message)
    else:
        # Parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_video = {}

            for video_path in video_files:
                base_path = video_path.with_suffix('')
                subtitle_files = find_subtitle_files(base_path)

                if not subtitle_files:
                    logging.warning(
                        "- No matching subtitle files for %s → skipping", video_path.name)
                    stats.skipped_videos += 1
                    continue

                future = executor.submit(
                    process_single_video,
                    video_path, subtitle_files, font_attachments, None, dry_run
                )
                future_to_video[future] = (video_path, subtitle_files)

            for future in concurrent.futures.as_completed(future_to_video):
                video_path, subtitle_files = future_to_video[future]
                try:
                    success, message = future.result()
                    if success:
                        stats.processed_videos += 1
                        if subtitle_files[0].extension.lower() == '.ass' and font_attachments:
                            stats.fonts_embedded += len(font_attachments)
                    else:
                        stats.failed_videos += 1
                        logging.error(message)
                except Exception as exc:
                    stats.failed_videos += 1
                    logging.error(
                        "Video %s generated an exception: %s", video_path.name, exc)

    return stats


# ------------------------------ CLI Interface ------------------------------ #

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Merge subtitle files into video containers using mkvmerge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Process current directory
  %(prog)s /path/to/videos          # Process specific directory
  %(prog)s -p 4                     # Use 4 parallel workers
  %(prog)s --dry-run                # Preview operations without executing
  %(prog)s -v                       # Verbose output
        """
    )

    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory containing video files (default: current directory)'
    )

    parser.add_argument(
        '-p', '--parallel',
        type=int,
        default=1,
        metavar='N',
        help='Number of parallel workers (default: 1)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview operations without executing'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    setup_logging(args.verbose)

    # Check dependencies
    check_dependencies()

    # Validate arguments
    if args.parallel < 1:
        logging.error("Number of parallel workers must be at least 1")
        return 1

    # Determine root directory
    root_dir = Path(args.path).resolve()
    if not root_dir.is_dir():
        logging.error("Path must be a directory: %s", root_dir)
        return 1

    if args.dry_run:
        logging.info("DRY RUN MODE - No files will be modified")

    logging.info("Processing directory: %s", root_dir)
    if args.parallel > 1:
        logging.info("Using %d parallel workers", args.parallel)

    # Collect font attachments
    font_attachments = collect_font_attachments(root_dir)

    # Find video files
    video_files = find_video_files(root_dir)

    if not video_files:
        logging.info("No video files found in %s", root_dir)
        return 0

    logging.info("Found %d video file(s) to process", len(video_files))

    # Process videos
    stats = process_videos(
        video_files=video_files,
        font_attachments=font_attachments,
        max_workers=args.parallel,
        dry_run=args.dry_run
    )

    # Print final statistics
    logging.info(str(stats))

    return 0 if stats.failed_videos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
