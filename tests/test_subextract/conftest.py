"""
Subextract-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the subextract.py subtitle extraction tool.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import json

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import subextract for testing
import subextract

# Import shared fixtures


@pytest.fixture
def sample_mkv_file(temp_dir):
    """Create a sample MKV file for testing."""
    mkv_path = temp_dir / "test_movie.mkv"
    mkv_path.write_text("dummy mkv content")
    return mkv_path


@pytest.fixture
def sample_mkv_files(temp_dir):
    """Create multiple sample MKV files for testing."""
    mkv_files = {}
    movie_titles = ["Movie1", "Movie2", "Movie3"]

    for title in movie_titles:
        mkv_path = temp_dir / f"{title}.mkv"
        mkv_path.write_text(f"dummy mkv content for {title}")
        mkv_files[title] = mkv_path

    return mkv_files


@pytest.fixture
def mock_mkvmerge_available():
    """Mock mkvmerge/mkvextract availability check."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = '/usr/bin/mkvmerge'
        yield mock_which


@pytest.fixture
def mock_mkvmerge_unavailable():
    """Mock mkvmerge/mkvextract unavailability."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = None
        yield mock_which


@pytest.fixture
def mock_mkvmerge_identify_output():
    """Mock mkvmerge identify JSON output with subtitle tracks."""
    return {
        "container": {
            "type": "Matroska",
            "recognized": True
        },
        "tracks": [
            {
                "id": 0,
                "type": "video",
                "codec": "V_MPEG4/ISO/AVC",
                "language": "und"
            },
            {
                "id": 1,
                "type": "audio",
                "codec": "A_AAC",
                "language": "eng"
            },
            {
                "id": 2,
                "type": "subtitles",
                "codec": "S_TEXT/UTF8",
                "language": "eng",
                "properties": {
                    "track_name": "English"
                }
            },
            {
                "id": 3,
                "type": "subtitles",
                "codec": "S_TEXT/ASS",
                "language": "fre",
                "properties": {
                    "track_name": "French"
                }
            },
            {
                "id": 4,
                "type": "subtitles",
                "codec": "S_TEXT/UTF8",
                "language": "spa",
                "properties": {
                    "track_name": "Spanish"
                }
            }
        ],
        "attachments": [
            {
                "id": 1,
                "type": "application/x-truetype-font",
                "file_name": "Arial.ttf",
                "description": "Arial"
            }
        ]
    }


@pytest.fixture
def mock_mkvmerge_identify_no_subs():
    """Mock mkvmerge identify JSON output with no subtitle tracks."""
    return {
        "container": {
            "type": "Matroska",
            "recognized": True
        },
        "tracks": [
            {
                "id": 0,
                "type": "video",
                "codec": "V_MPEG4/ISO/AVC"
            },
            {
                "id": 1,
                "type": "audio",
                "codec": "A_AAC",
                "language": "eng"
            }
        ],
        "attachments": []
    }


@pytest.fixture
def mock_mkvmerge_success():
    """Mock successful mkvmerge execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout=json.dumps({}),
            stderr="",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_mkvmerge_failure():
    """Mock failed mkvmerge execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="",
            stderr="mkvmerge error: file not found",
            returncode=1
        )
        yield mock_run


@pytest.fixture
def complex_mkv_setup(temp_dir):
    """Create a complex MKV setup for comprehensive testing."""
    # Create multiple MKV files with different configurations
    base_dir = temp_dir / "mkv_collection"
    base_dir.mkdir()

    movies = {}

    # Movie 1: Multiple subtitle tracks
    movie1 = base_dir / "action_movie_2023.mkv"
    movie1.write_text("action movie content")
    movies["action"] = movie1

    # Movie 2: Single subtitle track
    movie2 = base_dir / "drama_movie.mkv"
    movie2.write_text("drama movie content")
    movies["drama"] = movie2

    # Movie 3: No subtitles
    movie3 = base_dir / "silent_film.mkv"
    movie3.write_text("silent film content")
    movies["silent"] = movie3

    # Movie 4: Multiple languages with different codecs
    movie4 = base_dir / "international_movie.mkv"
    movie4.write_text("international movie content")
    movies["international"] = movie4

    # Create non-MKV files (should be ignored)
    (base_dir / "readme.txt").write_text("movie collection info")
    (base_dir / "trailer.mp4").write_text("trailer content")
    (base_dir / "subtitle.srt").write_text("standalone subtitle")

    # Create subdirectory
    series_dir = base_dir / "series"
    series_dir.mkdir()
    episode1 = series_dir / "series_s01e01.mkv"
    episode1.write_text("episode 1 content")
    movies["episode1"] = episode1

    return {
        'base_dir': base_dir,
        'movies': movies,
        'total_files': len(movies)
    }


@pytest.fixture
def subtitle_track_factory():
    """Factory for creating mock SubTrack objects."""
    def create_subtrack(track_id, language="eng", codec="S_TEXT/UTF8", track_name=None):
        return subextract.SubTrack(
            id=track_id,
            language=language,
            codec=codec,
            track_name=track_name or f"Track {track_id}"
        )
    return create_subtrack


@pytest.fixture
def extraction_stats():
    """Create a mock ExtractionStats object for tracking."""
    # If the tool has statistics tracking
    class MockExtractionStats:
        def __init__(self):
            self.files_processed = 0
            self.subtitles_extracted = 0
            self.failures = 0
            self.start_time = None
            self.end_time = None

        def add_success(self):
            self.files_processed += 1

        def add_failure(self):
            self.failures += 1

        def add_subtitle(self):
            self.subtitles_extracted += 1

    return MockExtractionStats()