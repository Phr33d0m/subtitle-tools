"""
Submerge-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the submerge.py subtitle merging tool.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import submerge for testing
import submerge

# Import shared fixtures
from tests.shared.fixtures import (
    sample_video_file,
    sample_srt_file,
    sample_ass_file,
    fonts_dir,
    mock_subprocess_success,
    mock_subprocess_failure,
    mock_encoding_utf8,
    mock_encoding_iso8859,
    mock_encoding_unknown,
    complex_subtitle_setup,
)

# Keep compatibility with existing global fixtures
from tests.conftest import (
    temp_dir,
    mock_mkvmerge_available,
    mock_file_command,
    mock_mkvmerge_identify,
    mock_mkvmerge_with_fonts,
    sample_swedish_srt,
)


@pytest.fixture
def mock_subtitle_file_factory():
    """Factory for creating mock SubtitleFile objects."""
    def create_mock_subtitle_file(path: Path, language_code: str):
        """Create a mock SubtitleFile instance."""
        # Mock the from_path method to avoid file system calls
        with patch.object(submerge.SubtitleFile, 'from_path') as mock_from_path:
            mock_subtitle_file = submerge.SubtitleFile(
                path=path,
                language_code=language_code,
                extension=path.suffix,
                priority=1 if path.suffix.lower() == '.ass' else 2  # ASS gets higher priority
            )
            mock_from_path.return_value = mock_subtitle_file
            return mock_subtitle_file

    return create_mock_subtitle_file


@pytest.fixture
def mock_merge_video_with_subtitles():
    """Mock merge_video_with_subtitles function."""
    with patch('submerge.merge_video_with_subtitles') as mock_merge:
        mock_merge.return_value = True
        yield mock_merge


@pytest.fixture
def mock_process_videos():
    """Mock process_videos function."""
    with patch('submerge.process_videos') as mock_process:
        mock_process.return_value = submerge.ProcessingStats()
        yield mock_process


@pytest.fixture
def mock_collect_font_attachments():
    """Mock collect_font_attachments function."""
    with patch('submerge.collect_font_attachments') as mock_collect:
        mock_collect.return_value = []
        yield mock_collect