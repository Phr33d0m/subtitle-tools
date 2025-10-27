"""
Subtimefix-specific pytest configuration and fixtures.

This module provides fixtures and configuration specific to testing
the subtimefix.py timestamp shifting tool.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import subtimefix for testing
import subtimefix

# Import shared fixtures
from tests.shared.fixtures import (
    temp_dir,
    sample_video_file,
    mock_subprocess_success,
    mock_subprocess_failure,
)


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
Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,Test subtitle line 2
"""
    ass_path.write_text(ass_content)
    return ass_path


@pytest.fixture
def complex_ass_setup(temp_dir):
    """Create a complex ASS setup for comprehensive testing."""
    base_dir = temp_dir / "subtitle_collection"
    base_dir.mkdir()

    ass_files = {}

    # Normal ASS file
    normal_ass = base_dir / "normal.ass"
    normal_ass.write_text("normal subtitle content")
    ass_files["normal"] = normal_ass

    # ASS with AI-generated timestamps
    ai_ass = base_dir / "ai_generated.ass"
    ai_ass.write_text("ai generated content")
    ass_files["ai"] = ai_ass

    # Empty ASS file
    empty_ass = base_dir / "empty.ass"
    empty_ass.write_text("")
    ass_files["empty"] = empty_ass

    return {
        'base_dir': base_dir,
        'ass_files': ass_files
    }
