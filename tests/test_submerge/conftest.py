"""
Sub-merge-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the sub-merge.py subtitle merging tool.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import import_tool

# Import sub-merge for testing
sub_merge = import_tool("sub-merge")

# Import shared fixtures
from tests.shared.fixtures import (
    mock_encoding_utf8,
    mock_encoding_iso8859,
    mock_encoding_unknown,
    mock_subprocess_success,
    mock_subprocess_failure,
    complex_subtitle_setup
)

# Keep compatibility with existing global fixtures


@pytest.fixture
def mock_subtitle_file_factory():
    """Factory for creating mock SubtitleFile objects."""
    def create_mock_subtitle_file(path: Path, language_code: str):
        """Create a mock SubtitleFile instance."""
        # Mock the from_path method to avoid file system calls
        with patch.object(sub_merge.SubtitleFile, 'from_path') as mock_from_path:
            mock_subtitle_file = sub_merge.SubtitleFile(
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
    with patch.object(sub_merge, 'merge_video_with_subtitles') as mock_merge:
        mock_merge.return_value = True
        yield mock_merge


@pytest.fixture
def mock_process_videos():
    """Mock process_videos function."""
    with patch.object(sub_merge, 'process_videos') as mock_process:
        mock_process.return_value = sub_merge.ProcessingStats()
        yield mock_process


@pytest.fixture
def mock_collect_font_attachments():
    """Mock collect_font_attachments function."""
    with patch.object(sub_merge, 'collect_font_attachments') as mock_collect:
        mock_collect.return_value = []
        yield mock_collect