"""
ASS QA Fix-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the ass-qafix.py quality assurance and auto-fixer tool.
"""

import pytest
from pathlib import Path

from tests.conftest import import_tool

# Import ass-qafix for testing
ass_qafix = import_tool("ass-qafix")


@pytest.fixture
def sample_ass_file(temp_dir):
    """Create a sample ASS subtitle file for testing."""
    ass_path = temp_dir / "subtitle.ass"
    ass_content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Test subtitle line 1
"""
    ass_path.write_text(ass_content)
    return ass_path


@pytest.fixture
def problematic_ass_file(temp_dir):
    """Create a problematic ASS file with QA issues."""
    ass_path = temp_dir / "problematic.ass"
    ass_content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CustomStyle,Times New Roman,18,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,1,0,100,100,0,0,1,2,0,2,5,5,5,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,00:00:01.00,00:00:02.00,Default,,0,0,0,,Normal subtitle
Dialogue: 1,0:00:03.00,0:00:04.00,NonExistentStyle,,0,0,0,,Subtitle with invalid style
Dialogue: 0,0:00:05.00,0:00:06.00,Default,,0,0,0,,Empty text line
Dialogue: 0,25:00:00.00,25:00:01.00,Default,,0,0,0,,Another subtitle
"""
    ass_path.write_text(ass_content)
    return ass_path


@pytest.fixture
def test_data_path():
    """Provide path to test data directory."""
    return Path(__file__).parent / "test_data"
