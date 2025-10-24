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

DEFAULT_VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.MP4', '.MKV', '.webm'}
DEFAULT_SUBTITLE_EXTENSIONS = {'.ass', '.srt', '.ASS', '.SRT'}
FONTS_DIR_NAME = "Fonts"

# Format priority: higher number = higher priority
SUBTITLE_FORMAT_PRIORITY = {
    '.ass': 2,
    '.ASS': 2,
    '.srt': 1,
    '.SRT': 1,
}

# Language code mapping: maps various formats to standardized mkvmerge-compatible codes
LANGUAGE_CODE_MAPPING = {
    # ISO 639-1 (2-letter codes)
    'en': 'eng', 'es': 'spa', 'fr': 'fre', 'de': 'ger', 'it': 'ita',
    'pt': 'por', 'ru': 'rus', 'ja': 'jpn', 'ko': 'kor', 'ar': 'ara',
    'hi': 'hin', 'th': 'tha', 'vi': 'vie', 'bg': 'bul', 'cs': 'cze',
    'da': 'dan', 'el': 'gre', 'he': 'heb', 'hu': 'hun', 'nl': 'dut',
    'no': 'nor', 'pl': 'pol', 'ro': 'rum', 'sv': 'swe', 'tr': 'tur',
    'uk': 'ukr', 'zh': 'chi', 'fa': 'per', 'ur': 'urd', 'bn': 'ben',
    'pa': 'pan', 'ta': 'tam', 'te': 'tel', 'ml': 'mal', 'kn': 'kan',
    'gu': 'guj', 'mr': 'mar', 'ne': 'nep', 'si': 'sin', 'my': 'bur',
    'km': 'khm', 'lo': 'lao', 'ka': 'geo', 'am': 'amh', 'sw': 'swa',
    'zu': 'zul', 'af': 'afr', 'is': 'ice', 'mt': 'mlt', 'cy': 'wel',
    'ga': 'gle', 'gd': 'gla', 'eu': 'baq', 'ca': 'cat', 'gl': 'glg',
    'sr': 'srp', 'hr': 'hrv', 'sl': 'slv', 'et': 'est', 'lv': 'lav',
    'lt': 'lit', 'fi': 'fin', 'mk': 'mac', 'sq': 'alb', 'hy': 'arm',
    'az': 'aze', 'kk': 'kaz', 'ky': 'kir', 'uz': 'uzb', 'tg': 'tgk',
    'mn': 'mon', 'bo': 'tib', 'dz': 'dzo', 'ny': 'nya', 'sn': 'sna',
    'yo': 'yor', 'ig': 'ibo', 'ha': 'hau', 'so': 'som', 'ti': 'tir',

    # ISO 639-2/T (3-letter codes) - map to themselves
    'eng': 'eng', 'spa': 'spa', 'fre': 'fre', 'ger': 'ger', 'ita': 'ita',
    'por': 'por', 'rus': 'rus', 'jpn': 'jpn', 'kor': 'kor', 'ara': 'ara',
    'hin': 'hin', 'tha': 'tha', 'vie': 'vie', 'bul': 'bul', 'cze': 'cze',
    'dan': 'dan', 'gre': 'gre', 'heb': 'heb', 'hun': 'hun', 'dut': 'dut',
    'nor': 'nor', 'pol': 'pol', 'rum': 'rum', 'swe': 'swe', 'tur': 'tur',
    'ukr': 'ukr', 'chi': 'chi', 'per': 'per', 'urd': 'urd', 'ben': 'ben',
    'pan': 'pan', 'tam': 'tam', 'tel': 'tel', 'mal': 'mal', 'kan': 'kan',
    'guj': 'guj', 'mar': 'mar', 'nep': 'nep', 'sin': 'sin', 'bur': 'bur',
    'khm': 'khm', 'lao': 'lao', 'geo': 'geo', 'amh': 'amh', 'swa': 'swa',
    'zul': 'zul', 'afr': 'afr', 'ice': 'ice', 'mlt': 'mlt', 'wel': 'wel',
    'gle': 'gle', 'gla': 'gla', 'baq': 'baq', 'cat': 'cat', 'glg': 'glg',
    'srp': 'srp', 'hrv': 'hrv', 'slv': 'slv', 'est': 'est', 'lav': 'lav',
    'lit': 'lit', 'fin': 'fin', 'mac': 'mac', 'alb': 'alb', 'arm': 'arm',
    'aze': 'aze', 'kaz': 'kaz', 'kir': 'kir', 'uzb': 'uzb', 'tgk': 'tgk',
    'mon': 'mon', 'tib': 'tib', 'dzo': 'dzo', 'nya': 'nya', 'sna': 'sna',
    'yor': 'yor', 'ibo': 'ibo', 'hau': 'hau', 'som': 'som', 'tir': 'tir',

    # IETF language tags - mkvmerge accepts many of these directly
    'zh-Hans': 'zh-Hans', 'zh-Hant': 'zh-Hant', 'zh-cn': 'zh-Hans', 'zh-tw': 'zh-Hant',
    'pt-BR': 'pt-BR', 'pt-PT': 'pt-PT', 'en-US': 'eng', 'en-GB': 'eng',
    'es-ES': 'spa', 'es-MX': 'spa', 'fr-FR': 'fre', 'fr-CA': 'fre',
    'de-DE': 'ger', 'de-AT': 'ger', 'it-IT': 'ita', 'ja-JP': 'jpn',
    'ko-KR': 'kor', 'ar-SA': 'ara', 'ru-RU': 'rus', 'hi-IN': 'hin',
    'th-TH': 'tha', 'vi-VN': 'vie', 'bg-BG': 'bul', 'tr-TR': 'tur',

    # Additional common variations
    'chi': 'chi', 'chn': 'chi',  # Chinese variations
    'spa': 'spa', 'es': 'spa',   # Spanish variations
    'fre': 'fre', 'fr': 'fre',   # French variations
    'ger': 'ger', 'de': 'ger',   # German variations
    'cze': 'cze', 'cs': 'cze',   # Czech variations
    'gre': 'gre', 'el': 'gre',   # Greek variations
    'rum': 'rum', 'ro': 'rum',   # Romanian variations
    'mac': 'mac', 'mk': 'mac',   # Macedonian variations
    'baq': 'baq', 'eu': 'baq',   # Basque variations
    'bur': 'bur', 'my': 'bur',   # Burmese variations
    'tib': 'tib', 'bo': 'tib',   # Tibetan variations
    'per': 'per', 'fa': 'per',   # Persian variations
}

# Language code to language name mapping for track names
# Only need to map standardized codes (3-letter and IETF) since all variants are normalized by LANGUAGE_CODE_MAPPING
LANGUAGE_NAME_MAPPING = {
    # ISO 639-2/T (3-letter codes)
    'eng': 'English', 'spa': 'Spanish', 'fre': 'French', 'ger': 'German', 'ita': 'Italian',
    'por': 'Portuguese', 'rus': 'Russian', 'jpn': 'Japanese', 'kor': 'Korean', 'ara': 'Arabic',
    'hin': 'Hindi', 'tha': 'Thai', 'vie': 'Vietnamese', 'bul': 'Bulgarian', 'cze': 'Czech',
    'dan': 'Danish', 'gre': 'Greek', 'heb': 'Hebrew', 'hun': 'Hungarian', 'dut': 'Dutch',
    'nor': 'Norwegian', 'pol': 'Polish', 'rum': 'Romanian', 'swe': 'Swedish', 'tur': 'Turkish',
    'ukr': 'Ukrainian', 'chi': 'Chinese', 'per': 'Persian', 'urd': 'Urdu', 'ben': 'Bengali',
    'pan': 'Punjabi', 'tam': 'Tamil', 'tel': 'Telugu', 'mal': 'Malayalam', 'kan': 'Kannada',
    'guj': 'Gujarati', 'mar': 'Marathi', 'nep': 'Nepali', 'sin': 'Sinhala', 'bur': 'Burmese',
    'khm': 'Khmer', 'lao': 'Lao', 'geo': 'Georgian', 'amh': 'Amharic', 'swa': 'Swahili',
    'zul': 'Zulu', 'afr': 'Afrikaans', 'ice': 'Icelandic', 'mlt': 'Maltese', 'wel': 'Welsh',
    'gle': 'Irish', 'gla': 'Scottish Gaelic', 'baq': 'Basque', 'cat': 'Catalan', 'glg': 'Galician',
    'srp': 'Serbian', 'hrv': 'Croatian', 'slv': 'Slovenian', 'est': 'Estonian', 'lav': 'Latvian',
    'lit': 'Lithuanian', 'fin': 'Finnish', 'mac': 'Macedonian', 'alb': 'Albanian', 'arm': 'Armenian',
    'aze': 'Azerbaijani', 'kaz': 'Kazakh', 'kir': 'Kyrgyz', 'uzb': 'Uzbek', 'tgk': 'Tajik',
    'mon': 'Mongolian', 'tib': 'Tibetan', 'dzo': 'Dzongkha', 'nya': 'Chichewa', 'sna': 'Shona',
    'yor': 'Yoruba', 'ibo': 'Igbo', 'hau': 'Hausa', 'som': 'Somali', 'tir': 'Tigrinya',

    # IETF language tags that mkvmerge accepts directly
    'zh-Hans': 'Chinese (Simplified)', 'zh-Hant': 'Chinese (Traditional)',
    'pt-BR': 'Portuguese (Brazil)', 'pt-PT': 'Portuguese (Portugal)',

    # Special case for undetermined language
    'und': 'Unknown',
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
    def from_path(cls, path: Path, base_name: Optional[str] = None) -> Optional[SubtitleFile]:
        """Create SubtitleFile from path, extracting language code from compound extension.

        Args:
            path: Path to the subtitle file
            base_name: Base video name to match against (for simple extension detection)
        """
        if path.suffix not in DEFAULT_SUBTITLE_EXTENSIONS:
            return None

        # Parse compound extension like ".zh-Hans.ass" or ".eng.srt"
        stem = path.stem
        parts = stem.split('.')

        extension = path.suffix
        priority = SUBTITLE_FORMAT_PRIORITY.get(extension, 0)

        if len(parts) >= 2 and base_name:
            # Check if this matches the pattern: base_name.language_code.extension
            potential_base_name = '.'.join(parts[:-1])
            potential_lang_code = parts[-1]

            if potential_base_name == base_name:
                # This is a compound extension with language code
                detected_language = detect_language_code(potential_lang_code)
                return cls(
                    path=path,
                    language_code=detected_language,
                    extension=extension,
                    priority=priority
                )

        if len(parts) >= 2:
            # General compound extension case (backward compatibility)
            language_code = parts[-1]
            detected_language = detect_language_code(language_code)
            return cls(
                path=path,
                language_code=detected_language,
                extension=extension,
                priority=priority
            )
        elif len(parts) == 1:
            # Simple extension (no language code) - only if base_name is provided
            if base_name and parts[0] == base_name:
                # This is a subtitle without language code matching the video
                return cls(
                    path=path,
                    language_code="und",  # Undetermined language
                    extension=extension,
                    priority=priority
                )

        return None


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
    total_subtitle_tracks: int = 0
    fonts_embedded: int = 0

    def __str__(self) -> str:
        return (f"Processing complete:\n"
                f"  Total videos found: {self.total_videos}\n"
                f"  Successfully processed: {self.processed_videos}\n"
                f"  Skipped: {self.skipped_videos}\n"
                f"  Failed: {self.failed_videos}\n"
                f"  Total subtitle tracks merged: {self.total_subtitle_tracks}\n"
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


def detect_language_code(language_code: str) -> str:
    """Detect and normalize language code from various formats."""
    if not language_code:
        return "und"  # Undetermined language

    normalized_code = language_code.strip()

    # Look up in mapping dictionary
    mapped_code = LANGUAGE_CODE_MAPPING.get(normalized_code.lower())
    if mapped_code:
        return mapped_code

    # For unrecognized codes, try to be smart about it
    # If it's already 3 letters and looks like ISO 639-2, use as-is
    if len(normalized_code) == 3 and normalized_code.isalpha():
        logging.debug("Unrecognized 3-letter language code: %s",
                      normalized_code)
        return normalized_code.lower()

    # If it's 2 letters and looks like ISO 639-1, try to convert
    if len(normalized_code) == 2 and normalized_code.isalpha():
        logging.debug("Unrecognized 2-letter language code: %s",
                      normalized_code)
        return normalized_code.lower()

    # For IETF tags, if not in mapping, use as-is (mkvmerge might handle them)
    if '-' in normalized_code:
        logging.debug("Using IETF language tag: %s", normalized_code)
        return normalized_code

    # Default to undetermined
    logging.debug(
        "Could not identify language code: %s -> using 'und'", language_code)
    return "und"


def get_language_name(language_code: str) -> str:
    """Get the full language name from a language code."""
    if not language_code:
        return "Unknown"

    # Look up in the language name mapping
    language_name = LANGUAGE_NAME_MAPPING.get(language_code)
    if language_name:
        return language_name

    # Try lowercase version
    language_name = LANGUAGE_NAME_MAPPING.get(language_code.lower())
    if language_name:
        return language_name

    # For unrecognized codes, try to be helpful
    if language_code == "und":
        return "Unknown"

    # If it's an IETF tag, try the base part
    if '-' in language_code:
        base_code = language_code.split('-')[0]
        language_name = LANGUAGE_NAME_MAPPING.get(base_code.lower())
        if language_name:
            return language_name

    # Default to the code itself if we can't find a name
    logging.debug("Could not find language name for: %s", language_code)
    return language_code.title()


# ------------------------------ Core Functions ------------------------------ #

def find_video_files(root_dir: Path) -> List[Path]:
    """Find all video files in the given directory tree."""
    video_files = []

    for ext in DEFAULT_VIDEO_EXTENSIONS:
        video_files.extend(root_dir.rglob(f"*{ext}"))

    return sorted(video_files)


def find_subtitle_files(base_path: Path) -> List[SubtitleFile]:
    """Find all subtitle files matching the given base path."""
    subtitle_files = []

    # Get the base name without extension
    base_name = base_path.name

    # Use a more robust approach: find all files in directory and check if they start with our base name
    # This avoids issues with special characters in filenames (brackets, etc.)
    for file_path in base_path.parent.iterdir():
        if not file_path.is_file():
            continue

        # Check if the filename starts with our base name followed by a dot
        if file_path.name.startswith(f"{base_name}."):
            # Skip the video file itself
            if file_path == base_path:
                continue

            # Only include subtitle files
            if file_path.suffix in DEFAULT_SUBTITLE_EXTENSIONS:
                subtitle_file = SubtitleFile.from_path(file_path, base_name)
                if subtitle_file:
                    subtitle_files.append(subtitle_file)

    # Sort by priority (higher first), then by language code, then by path for consistency
    subtitle_files.sort(
        key=lambda x: (-x.priority, x.language_code, str(x.path)))

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


def merge_video_with_subtitles(
    video_path: Path,
    subtitle_files: List[SubtitleFile],
    font_attachments: List[FontAttachment],
    temp_dir: Optional[Path],
    dry_run: bool = False
) -> bool:
    """Merge video file with multiple subtitle tracks using mkvmerge."""

    base_name = video_path.stem
    output_path = video_path.parent / f"{base_name}.mkv"
    # Create temp file in the same directory to avoid cross-device link issues
    temp_output = output_path.with_suffix('.mkv.temp')

    # Build mkvmerge command
    cmd = [
        'mkvmerge',
        '-q',  # Quiet mode
        '-o', str(temp_output),
        '--no-subtitles', str(video_path)
    ]

    # Add all subtitle tracks
    for i, subtitle_file in enumerate(subtitle_files):
        track_id = str(i)
        language_code = normalize_language_code(subtitle_file.language_code)
        language_name = get_language_name(subtitle_file.language_code)
        display_name = language_name

        cmd.extend([
            '--language', f'{track_id}:{language_code}',
            '--track-name', f'{track_id}:{display_name}'
        ])

        # Set first subtitle as default track
        if i == 0:
            cmd.extend(['--default-track-flag', f'{track_id}:yes'])
        else:
            cmd.extend(['--default-track-flag', f'{track_id}:no'])

        cmd.append(str(subtitle_file.path))

    # Add font attachments if available and any subtitle format requires fonts (ASS)
    has_ass_subtitles = any(sub.extension.lower() ==
                            '.ass' for sub in subtitle_files)
    if has_ass_subtitles and font_attachments:
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

        # Create list of all subtitle paths for backup
        subtitle_paths = [sub.path for sub in subtitle_files]

        # Replace original files safely
        backup_video = video_path.with_suffix(video_path.suffix + '.bak')
        backup_subs = [sub_path.with_suffix(
            sub_path.suffix + '.bak') for sub_path in subtitle_paths]

        try:
            # Create backups
            if video_path.exists():
                video_path.rename(backup_video)
            for sub_path in subtitle_paths:
                if sub_path.exists():
                    sub_path.rename(sub_path.with_suffix(
                        sub_path.suffix + '.bak'))

            # Move temp file to final location (same device, so rename works)
            temp_output.rename(output_path)

            # Remove backups after successful merge
            if backup_video.exists():
                backup_video.unlink()
            for backup_sub in backup_subs:
                if backup_sub.exists():
                    backup_sub.unlink()

            subtitle_names = [
                get_language_name(sub.language_code) for sub in subtitle_files]
            logging.info("✓ Created: %s with subtitles: %s",
                         output_path, ', '.join(subtitle_names))
            return True

        except Exception as e:
            # Restore backups if something went wrong
            logging.error(
                "Failed to replace files, attempting to restore backups: %s", e)
            if backup_video.exists():
                backup_video.rename(video_path)
            for i, sub_path in enumerate(subtitle_paths):
                if backup_subs[i].exists():
                    backup_subs[i].rename(sub_path)
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
    """Process a single video file with all matching subtitle tracks."""

    if not subtitle_files:
        return False, f"No matching subtitle files found for {video_path.name}"

    # Log all found subtitle files
    subtitle_names = [
        get_language_name(sub.language_code) for sub in subtitle_files]
    logging.info("Processing %s with %d subtitle(s): %s", video_path.name,
                 len(subtitle_files), ', '.join(subtitle_names))

    success = merge_video_with_subtitles(
        video_path=video_path,
        subtitle_files=subtitle_files,
        font_attachments=font_attachments,
        temp_dir=temp_dir,
        dry_run=dry_run
    )

    if success:
        subtitle_files_str = ', '.join(sub.path.name for sub in subtitle_files)
        return True, f"Successfully merged {subtitle_files_str} into {video_path.name}"
    else:
        subtitle_files_str = ', '.join(sub.path.name for sub in subtitle_files)
        return False, f"Failed to merge {subtitle_files_str} into {video_path.name}"


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
                stats.total_subtitle_tracks += len(subtitle_files)
                # Count font embedding if any subtitle is ASS format
                if any(sub.extension.lower() == '.ass' for sub in subtitle_files) and font_attachments:
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
                        stats.total_subtitle_tracks += len(subtitle_files)
                        # Count font embedding if any subtitle is ASS format
                        if any(sub.extension.lower() == '.ass' for sub in subtitle_files) and font_attachments:
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
