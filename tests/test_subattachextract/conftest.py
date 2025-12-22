"""
Sub-attachment-extract-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the sub-attachment-extract.py attachment extraction tool.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from tests.conftest import import_tool

# Import sub-attachment-extract for testing
sub_attachment_extract = import_tool("sub-attachment-extract")


@pytest.fixture
def sample_mkv_file(temp_dir):
    """Create a sample MKV file for testing."""
    mkv_path = temp_dir / "test_movie.mkv"
    mkv_path.write_text("dummy mkv content")
    return mkv_path


@pytest.fixture
def mock_mkvmerge_available():
    """Mock mkvmerge/mkvextract availability check."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = '/usr/bin/mkvmerge'
        yield mock_which
