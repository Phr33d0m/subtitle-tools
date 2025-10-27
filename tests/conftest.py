"""
Pytest fixtures and configuration for submerge tests.

This module provides common fixtures, mocks, and helper functions
used across all test modules.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, List
import sys
import os

# Add the parent directory to Python path for importing submerge
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import submerge modules for mocking
import submerge


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_mkvmerge_available():
    """Mock mkvmerge dependency check."""
    with patch('shutil.which') as mock_which:
        mock_which.return_value = '/usr/bin/mkvmerge'
        yield mock_which


@pytest.fixture
def mock_file_command():
    """Mock file command for MIME type detection."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='text/plain',
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_mkvmerge_identify():
    """Mock mkvmerge --identify command for track/attachment detection."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout='File ID 0: video (AVC/H.264)\nTrack ID 1: audio (AAC)\nTrack ID 2: subtitles (SubRip)',
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_mkvmerge_with_fonts():
    """Mock mkvmerge --identify with font attachments."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout=(
                'File ID 0: video (AVC/H.264)\n'
                'Track ID 1: audio (AAC)\n'
                'Track ID 2: subtitles (SubRip)\n'
                'Attachment ID 1: application/x-truetype-font:Arial.ttf'
            ),
            returncode=0
        )
        yield mock_run


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file."""
    video_path = temp_dir / "test_video.mkv"
    video_path.write_text("dummy video content")
    return video_path


@pytest.fixture
def sample_srt_file(temp_dir):
    """Create a sample SRT subtitle file."""
    srt_path = temp_dir / "test_video.eng.srt"
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Test subtitle content
"""
    srt_path.write_text(srt_content)
    return srt_path


@pytest.fixture
def sample_ass_file(temp_dir):
    """Create a sample ASS subtitle file."""
    ass_path = temp_dir / "test_video.eng.ass"
    ass_content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Test ASS subtitle
"""
    ass_path.write_text(ass_content)
    return ass_path


@pytest.fixture
def sample_swedish_srt(temp_dir):
    """Create a Swedish SRT subtitle file to test 'se' mapping."""
    srt_path = temp_dir / "test_video.se.srt"
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Svensk text
"""
    srt_path.write_text(srt_content)
    return srt_path


@pytest.fixture
def sample_font_file(temp_dir):
    """Create a sample font file."""
    font_path = temp_dir / "Arial.ttf"
    font_path.write_bytes(b"dummy font content")
    return font_path


@pytest.fixture
def fonts_dir(temp_dir, sample_font_file):
    """Create a Fonts directory with sample fonts."""
    fonts_path = temp_dir / "Fonts"
    fonts_path.mkdir()

    # Copy the sample font to the Fonts directory
    font_in_fonts = fonts_path / sample_font_file.name
    shutil.copy2(sample_font_file, font_in_fonts)

    return fonts_path


@pytest.fixture
def complex_subtitle_setup(temp_dir):
    """Create a complex setup with multiple subtitles and fonts."""
    # Create video
    video_path = temp_dir / "complex_video.mkv"
    video_path.write_text("dummy video content")

    # Create multiple subtitle files
    subtitles = {
        "eng.srt": "1\n00:00:01,000 --> 00:00:02,000\nEnglish subtitle",
        "fr.srt": "1\n00:00:01,000 --> 00:00:02,000\nFrench subtitle",
        "se.srt": "1\n00:00:01,000 --> 00:00:02,000\nSvensk text",
        "style.ass": """[V4+ Styles]
Format: Name, Fontname, Fontsize
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,Styled subtitle"""
    }

    subtitle_paths = {}
    for filename, content in subtitles.items():
        subtitle_path = temp_dir / f"complex_video.{filename}"
        subtitle_path.write_text(content)
        subtitle_paths[filename] = subtitle_path

    # Create Fonts directory with multiple fonts
    fonts_dir = temp_dir / "Fonts"
    fonts_dir.mkdir()

    font_files = {
        "Arial.ttf": b"arial font content",
        "Times.ttf": b"times font content",
        "Custom.otf": b"custom font content"
    }

    for font_name, content in font_files.items():
        font_path = fonts_dir / font_name
        font_path.write_bytes(content)

    return {
        'video': video_path,
        'subtitles': subtitle_paths,
        'fonts_dir': fonts_dir,
        'font_files': font_files
    }


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="success",
            stderr="",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="",
            stderr="mkvmerge error: something went wrong",
            returncode=1
        )
        yield mock_run


@pytest.fixture
def mock_encoding_utf8():
    """Mock UTF-8 encoding detection."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="utf-8",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_encoding_iso8859():
    """Mock ISO-8859-1 encoding detection."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="iso-8859-1",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_encoding_unknown():
    """Mock unknown encoding detection."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="unknown-8bit",
            returncode=0
        )
        yield mock_run


# Helper functions for tests
def create_mock_subtitle_file(path: Path, language: str, content: str = None):
    """Helper to create mock subtitle files."""
    if content is None:
        content = f"1\n00:00:01,000 --> 00:00:02,000\nTest {language} subtitle"

    subtitle_path = path / f"test.{language}.srt"
    subtitle_path.write_text(content)
    return subtitle_path


def create_mock_ass_file(path: Path, language: str):
    """Helper to create mock ASS files."""
    ass_content = f"""[V4+ Styles]
Format: Name, Fontname
Style: Default,Arial

[Events]
Format: Layer, Start, End, Style, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,Test {language} ASS subtitle"""

    ass_path = path / f"test.{language}.ass"
    ass_path.write_text(ass_content)
    return ass_path


def assert_mkvmerge_command_contains(cmd: List[str], expected_flags: List[str]):
    """Helper to assert mkvmerge command contains expected flags."""
    cmd_str = ' '.join(cmd)
    for flag in expected_flags:
        assert flag in cmd_str, f"Expected flag '{flag}' not found in command: {cmd_str}"


def assert_mkvmerge_command_lacks(cmd: List[str], unexpected_flags: List[str]):
    """Helper to assert mkvmerge command does not contain unexpected flags."""
    cmd_str = ' '.join(cmd)
    for flag in unexpected_flags:
        assert flag not in cmd_str, f"Unexpected flag '{flag}' found in command: {cmd_str}"