"""
Global pytest configuration for subtitle processing tools.

This module provides top-level configuration and imports shared
fixtures from the shared directory.
"""

import pytest
import sys
import tempfile
import shutil
import importlib.util
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

# Add the parent directory to Python path for importing tools
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def import_dashed_module(module_name: str):
    """Import a module with dashes in its name.

    Python doesn't allow dashes in module names for normal imports,
    so we use importlib to load them dynamically.
    """
    file_path = PROJECT_ROOT / f"{module_name}.py"
    if not file_path.exists():
        raise ImportError(f"Module file not found: {file_path}")

    # Convert dashed name to valid Python identifier for the module
    safe_name = module_name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(safe_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[safe_name] = module
    spec.loader.exec_module(module)
    return module


# Pre-import all tool modules and register them with underscore names
# This allows test files to use: import ass_qafix, import submerge, etc.
_module_mappings = {
    "ass-qafix": "ass_qafix",
    "sub-merge": "submerge",
    "sub-extract": "subextract",
    "sub-attachment-extract": "subattachextract",
    "sub-time-fix": "subtimefix",
}

for dashed_name, underscore_name in _module_mappings.items():
    try:
        module = import_dashed_module(dashed_name)
        sys.modules[underscore_name] = module
    except ImportError:
        pass  # Module may not exist in all test environments

# Import shared fixtures (avoiding conflicts with existing ones)


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