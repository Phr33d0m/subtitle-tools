"""
Common pytest fixtures for subtitle processing tools.

Provides reusable fixtures for temporary directories, mock files,
and other common test scenarios.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing."""
    video_path = temp_dir / "test_video.mkv"
    video_path.write_text("dummy video content")
    return video_path


@pytest.fixture
def sample_srt_file(temp_dir):
    """Create a sample SRT subtitle file."""
    srt_path = temp_dir / "test_video.eng.srt"
    srt_path.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:02,000\n"
        "This is a test subtitle.\n"
    )
    return srt_path


@pytest.fixture
def sample_ass_file(temp_dir):
    """Create a sample ASS subtitle file."""
    ass_path = temp_dir / "test_video.eng.ass"
    ass_path.write_text(
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,0,0,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,This is a test subtitle.\n"
    )
    return ass_path


@pytest.fixture
def fonts_dir(temp_dir):
    """Create a temporary fonts directory with sample fonts."""
    fonts_path = temp_dir / "Fonts"
    fonts_path.mkdir()

    # Create sample font files
    font_files = {
        "Arial.ttf": b"dummy font content for Arial",
        "Times.otf": b"dummy font content for Times",
        "Custom.woff": b"dummy font content for Custom"
    }

    for font_name, content in font_files.items():
        (fonts_path / font_name).write_bytes(content)

    return fonts_path


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run for successful operations."""
    mock = Mock()
    mock.return_code = 0
    return mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run for failed operations."""
    mock = Mock()
    mock.return_code = 1
    mock.stderr = "Mock error message"
    return mock


@pytest.fixture
def mock_encoding_utf8():
    """Mock file command to return UTF-8 encoding."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="utf-8",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_encoding_iso8859():
    """Mock file command to return ISO-8859-1 encoding."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="iso-8859-1",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_encoding_unknown():
    """Mock file command to return unknown encoding."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            stdout="unknown-8bit",
            returncode=0
        )
        yield mock_run


@pytest.fixture
def mock_mkvmerge_with_fonts():
    """Mock mkvmerge identify output for video with fonts."""
    mock = Mock()
    mock.stdout = (
        "File ID 0: video\n"
        "File ID 1: audio (AAC)\n"
        "File ID 2: subtitle (SubRip)\n"
        "File ID 3: attachment ID 1: application/x-truetype-font:Arial.ttf\n"
        "File ID 4: attachment ID 2: application/vnd.ms-opentype:Times.otf"
    )
    mock.returncode = 0
    return mock


@pytest.fixture
def complex_subtitle_setup(temp_dir):
    """Create a complex subtitle setup with multiple languages and fonts."""
    video_path = temp_dir / "complex_video.mkv"
    video_path.write_text("dummy video content")

    # Create various subtitle files
    subtitles = {}

    # English SRT
    eng_srt = temp_dir / "complex_video.eng.srt"
    eng_srt.write_text("English subtitle content")
    subtitles["eng.srt"] = eng_srt

    # French SRT
    fr_srt = temp_dir / "complex_video.fr.srt"
    fr_srt.write_text("French subtitle content")
    subtitles["fr.srt"] = fr_srt

    # Swedish SRT (using 'se' code)
    se_srt = temp_dir / "complex_video.se.srt"
    se_srt.write_text("Swedish subtitle content")
    subtitles["se.srt"] = se_srt

    # English ASS
    eng_ass = temp_dir / "complex_video.eng.ass"
    eng_ass.write_text(
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,0,0,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,English ASS subtitle.\n"
    )
    subtitles["style.ass"] = eng_ass

    # Create fonts directory
    fonts_dir = temp_dir / "Fonts"
    fonts_dir.mkdir()

    font_files = {
        "Arial.ttf": b"arial font content",
        "Times.ttf": b"times font content",
        "Custom.otf": b"custom font content"
    }

    for font_name, content in font_files.items():
        (fonts_dir / font_name).write_bytes(content)

    return {
        "video": video_path,
        "subtitles": subtitles,
        "fonts_dir": fonts_dir,
        "font_files": font_files
    }


class MockSubtitleFile:
    """Mock SubtitleFile class for testing."""
    def __init__(self, path: Path, language_code: str, extension: str, priority: int):
        self.path = path
        self.language_code = language_code
        self.extension = extension
        self.priority = priority


@pytest.fixture
def mock_subtitle_file_factory():
    """Factory for creating mock subtitle files."""
    def create_mock_subtitle_file(path: Path, language_code: str, extension: str = ".srt", priority: int = 1):
        return MockSubtitleFile(path, language_code, extension, priority)

    return create_mock_subtitle_file