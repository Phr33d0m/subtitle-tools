"""
Subattachextract-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the subattachextract.py attachment extraction tool.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import subattachextract for testing

# Import shared fixtures


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
