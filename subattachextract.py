#!/usr/bin/env python3
"""
Extract attachments from MKV files and organize them into Covers/Fonts/Others directories.
A Python rewrite of subattachextract.sh with parallel processing and enhanced features.
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import time


@dataclass
class Attachment:
    """Represents an attachment in an MKV file."""
    id: int
    filename: str
    mime_type: str
    size: Optional[int] = None


@dataclass
class ExtractionStats:
    """Statistics for extraction operations."""
    files_processed: int = 0
    attachments_found: int = 0
    attachments_extracted: int = 0
    attachments_skipped: int = 0
    errors: int = 0


class AttachmentExtractor:
    """Main class for extracting attachments from MKV files."""

    def __init__(self, dry_run: bool = False, verbose: bool = True,
                 max_workers: int = 4, stats: Optional[ExtractionStats] = None):
        self.dry_run = dry_run
        self.verbose = verbose
        self.max_workers = max_workers
        self.stats = stats or ExtractionStats()
        self.existing_files: Set[str] = set()

    def log(self, message: str, force: bool = False) -> None:
        """Print message if verbose mode is enabled or force is True."""
        if self.verbose or force:
            print(message)

    def check_dependencies(self) -> None:
        """Check if required external tools are available."""
        for tool in ['mkvmerge', 'mkvextract']:
            try:
                subprocess.run([tool, '--version'],
                               capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(
                    f"Error: '{tool}' is required but not found in PATH.", file=sys.stderr)
                sys.exit(1)

    def category_for(self, mime_type: str, filename: str) -> str:
        """Determine category directory based on MIME type and filename."""
        mime_lower = mime_type.lower()
        name_lower = filename.lower()

        # Check for fonts
        if (mime_lower.startswith('font/') or
            mime_lower in ['application/vnd.ms-opentype', 'application/x-font-otf',
                           'application/x-font-ttf', 'application/x-truetype-font'] or
                name_lower.endswith(('.ttf', '.otf', '.ttc', '.woff', '.woff2'))):
            return 'Fonts'

        # Check for images
        if (mime_lower.startswith('image/') or
            name_lower.endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')) or
                'cover' in name_lower or 'poster' in name_lower):
            return 'Covers'

        return 'Others'

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # Remove path components and get basename
        filename = os.path.basename(filename)

        # Replace problematic characters
        replacements = {
            '/': '_', '\\': '_', ':': '_', '*': '_', '?': '_',
            '"': '_', '<': '_', '>': '_', '|': '_'
        }

        for old, new in replacements.items():
            filename = filename.replace(old, new)

        # Limit filename length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext

        return filename

    def build_existing_name_set(self, outroot: Path) -> None:
        """Build a set of existing filenames in category directories."""
        categories = ['Covers', 'Fonts', 'Others']

        for category in categories:
            category_dir = outroot / category
            if category_dir.exists():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        self.existing_files.add(file_path.name)

    def remember_existing(self, filename: str) -> None:
        """Add a filename to the existing files set after extraction."""
        self.existing_files.add(filename)

    def get_mkv_attachments(self, mkv_path: Path) -> List[Attachment]:
        """Get list of attachments from MKV file using mkvmerge."""
        try:
            result = subprocess.run(
                ['mkvmerge', '-J', '--ui-language', 'en_US', str(mkv_path)],
                capture_output=True, text=True, check=True
            )
            data = json.loads(result.stdout)

            attachments = []
            for att in data.get('attachments', []):
                filename = att.get(
                    'file_name', f"attachment-{att.get('id', 'unknown')}")
                filename = self.sanitize_filename(filename)
                if '/' in filename:
                    filename = filename.split('/')[-1]  # Get basename

                attachments.append(Attachment(
                    id=att['id'],
                    filename=filename,
                    mime_type=att.get(
                        'content_type', 'application/octet-stream'),
                    size=att.get('size')
                ))

            return attachments

        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            self.log(
                f"Warning: failed to inspect '{mkv_path}' — {e}", force=True)
            return []

    def extract_one_attachment(self, mkv_path: Path, attachment: Attachment,
                               dest_path: Path) -> bool:
        """Extract a single attachment from MKV file."""
        if self.dry_run:
            return True

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ['mkvextract', 'attachments', str(mkv_path),
                 f"{attachment.id}:{str(dest_path)}"],
                capture_output=True, check=True
            )

            return dest_path.exists() and dest_path.stat().st_size > 0

        except subprocess.CalledProcessError:
            return False

    def process_attachments_for_file(self, mkv_path: Path, outroot: Path) -> None:
        """Process all attachments for a single MKV file."""
        if not mkv_path.exists() or mkv_path.stat().st_size == 0:
            self.log(
                f"Warning: '{mkv_path}' not found or empty — skipping.", force=True)
            self.stats.errors += 1
            return

        self.stats.files_processed += 1
        attachments = self.get_mkv_attachments(mkv_path)

        if not attachments:
            self.log(f"No attachments in: {mkv_path}")
            return

        self.stats.attachments_found += len(attachments)
        self.log(f"Attachments from: {mkv_path}")

        for attachment in attachments:
            # Skip if filename already exists
            if attachment.filename in self.existing_files:
                self.log(
                    f"  - Skipped existing filename: {attachment.filename}")
                self.stats.attachments_skipped += 1
                continue

            category = self.category_for(
                attachment.mime_type, attachment.filename)
            dest_path = outroot / category / attachment.filename

            # Check if destination already exists (race condition)
            if dest_path.exists():
                self.log(
                    f"  - Skipped (already present now): {category}/{attachment.filename}")
                self.remember_existing(attachment.filename)
                self.stats.attachments_skipped += 1
                continue

            if self.extract_one_attachment(mkv_path, attachment, dest_path):
                self.log(f"  - Saved: {category}/{attachment.filename}")
                self.remember_existing(attachment.filename)
                self.stats.attachments_extracted += 1
            else:
                self.log(
                    f"  - Empty/failed: {category}/{attachment.filename} (skipped)")
                self.stats.attachments_skipped += 1
                # Clean up any zero-byte remnants
                if dest_path.exists():
                    dest_path.unlink()

    def find_mkv_files(self, path: Path) -> List[Path]:
        """Find all MKV files in the given path."""
        if path.is_file():
            return [path] if path.suffix.lower() == '.mkv' else []
        elif path.is_dir():
            return list(path.glob('*.mkv')) + list(path.glob('*.MKV'))
        return []

    def process_files(self, paths: List[Path], outroot: Path) -> None:
        """Process multiple MKV files with parallel execution."""
        if not paths:
            self.log("No .mkv files found.", force=True)
            return

        # Build existing files set once
        self.build_existing_name_set(outroot)

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.process_attachments_for_file, mkv_path, outroot): mkv_path
                for mkv_path in paths
            }

            completed = 0
            total = len(paths)

            for future in as_completed(future_to_path):
                mkv_path = future_to_path[future]
                try:
                    future.result()
                except Exception as e:
                    self.log(f"Error processing {mkv_path}: {e}", force=True)
                    self.stats.errors += 1

                completed += 1
                if self.verbose and total > 1:
                    progress = (completed / total) * 100
                    print(
                        f"Progress: {completed}/{total} files ({progress:.1f}%)")

    def print_stats(self) -> None:
        """Print extraction statistics."""
        self.log("\n" + "="*50, force=True)
        self.log("Extraction Summary:", force=True)
        self.log(f"Files processed: {self.stats.files_processed}", force=True)
        self.log(
            f"Attachments found: {self.stats.attachments_found}", force=True)
        self.log(
            f"Attachments extracted: {self.stats.attachments_extracted}", force=True)
        self.log(
            f"Attachments skipped: {self.stats.attachments_skipped}", force=True)
        if self.stats.errors > 0:
            self.log(f"Errors encountered: {self.stats.errors}", force=True)
        self.log("="*50, force=True)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract attachments from MKV files and organize them into Covers/Fonts/Others directories."
    )
    parser.add_argument(
        'path', nargs='?', default='.',
        help='MKV file, directory containing MKVs, or current directory if omitted'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be extracted without actually extracting files'
    )
    parser.add_argument(
        '--quiet', '-q', action='store_true',
        help='Suppress verbose output'
    )
    parser.add_argument(
        '--parallel', '-p', type=int, default=4,
        help='Number of parallel workers (default: 4)'
    )

    args = parser.parse_args()

    # Determine output root
    path = Path(args.path)
    if path.is_file():
        outroot = Path.cwd()
    else:
        outroot = path

    # Create extractor
    extractor = AttachmentExtractor(
        dry_run=args.dry_run,
        verbose=not args.quiet,
        max_workers=args.parallel
    )

    # Check dependencies
    extractor.check_dependencies()

    # Find MKV files
    mkv_files = extractor.find_mkv_files(path)

    if args.dry_run:
        extractor.log("DRY RUN MODE - No files will be extracted", force=True)

    # Process files
    start_time = time.time()
    extractor.process_files(mkv_files, outroot)
    elapsed = time.time() - start_time

    # Print stats
    extractor.print_stats()
    if extractor.stats.files_processed > 0:
        extractor.log(f"Completed in {elapsed:.2f} seconds", force=True)

    extractor.log("Done.", force=True)


if __name__ == '__main__':
    main()
