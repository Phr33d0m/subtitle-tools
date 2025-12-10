"""
OCR-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the ocrp.py OCR processing tool.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import ocrp for testing
import ocrp

# Import shared fixtures


@pytest.fixture
def sample_video_files(temp_dir):
    """Create multiple sample video files for testing."""
    videos = {}
    video_formats = ['mp4', 'mkv', 'avi']

    for i, format_ext in enumerate(video_formats):
        video_path = temp_dir / f"test_video_{i}.{format_ext}"
        video_path.write_text(f"dummy video content {i}")
        videos[format_ext] = video_path

    return videos


@pytest.fixture
def sample_crop_config():
    """Create a sample crop configuration."""
    return ocrp.CropConfig(x=100, y=50, width=800, height=600)


@pytest.fixture
def multiple_crop_configs():
    """Create multiple crop configurations for testing."""
    return [
        ocrp.CropConfig(x=100, y=50, width=800, height=600),
        ocrp.CropConfig(x=200, y=100, width=700, height=500),
    ]


@pytest.fixture
def sample_processing_config():
    """Create a sample processing configuration."""
    return ocrp.ProcessingConfig(
        time_start="00:30",
        brightness=180,
        max_workers=4
    )


@pytest.fixture
def mock_videocr_available():
    """Mock VideOCR binary availability check."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = '/usr/local/bin/videocr'
        yield mock_which


@pytest.fixture
def mock_videocr_unavailable():
    """Mock VideOCR binary unavailability."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = None
        yield mock_which


@pytest.fixture
def mock_videocr_success():
    """Mock successful VideOCR execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="OCR processing completed",
            stderr="",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_videocr_failure():
    """Mock failed VideOCR execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="",
            stderr="VideOCR error: processing failed",
            returncode=1
        )
        yield mock_run


@pytest.fixture
def mock_videocr_timeout():
    """Mock VideOCR timeout."""
    with patch('subprocess.run') as mock_run:
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("videocr", timeout=300)
        yield mock_run


@pytest.fixture
def video_processor_factory():
    """Factory for creating VideoProcessor instances."""
    def create_processor(crops=None, time_start="01:50", brightness=165, max_workers=None):
        if crops is None:
            crops = [ocrp.CropConfig(100, 50, 800, 600)]
        return ocrp.VideoProcessor(
            crops=crops,
            time_start=time_start,
            brightness=brightness,
            max_workers=max_workers
        )
    return create_processor


@pytest.fixture
def complex_video_setup(temp_dir):
    """Create a complex video setup for comprehensive testing."""
    # Create multiple video directories
    base_dir = temp_dir / "video_collection"
    base_dir.mkdir()

    # Create subdirectories
    movies_dir = base_dir / "movies"
    series_dir = base_dir / "series"
    docs_dir = base_dir / "documents"

    for directory in [movies_dir, series_dir, docs_dir]:
        directory.mkdir()

    # Create video files
    videos = {}

    # Movies
    for i in range(3):
        video_path = movies_dir / f"movie_{i+1}.mp4"
        video_path.write_text(f"movie content {i+1}")
        videos[f"movie_{i+1}"] = video_path

    # Series episodes
    for season in range(2):
        for episode in range(3):
            video_path = series_dir / f"series_s{season+1:02d}_e{episode+1:02d}.mkv"
            video_path.write_text(f"series s{season+1} e{episode+1}")
            videos[f"series_s{season+1:02d}_e{episode+1:02d}"] = video_path

    # Create non-video files (should be ignored)
    (docs_dir / "readme.txt").write_text("video collection info")
    (movies_dir / "movie_1.srt").write_text("subtitle file")

    return {
        'base_dir': base_dir,
        'movies_dir': movies_dir,
        'series_dir': series_dir,
        'docs_dir': docs_dir,
        'videos': videos,
        'total_videos': len(videos)
    }