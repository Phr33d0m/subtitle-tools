"""
Test short duration dialogue warning detection for ass_qafix.py.

This module tests the detection and warning of very short dialogue lines
(less than 250ms duration) which typically indicate OCR merge errors.
"""

import pytest
from pathlib import Path
from io import StringIO
import sys

import ass_qafix


class TestShortDurationDetection:
    """Test detection of short duration dialogue lines."""

    def test_detect_short_duration_dialogue_above_threshold(self, temp_dir):
        """Test detection of a 30 centisecond (300ms) dialogue - should not warn."""
        test_file = temp_dir / "above_threshold.ass"
        content = """[Script Info]
Title: Above Threshold Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:24.00,0:05:24.30,Default,,0,0,0,,This line is 300ms - above threshold.
Dialogue: 0,0:05:25.00,0:05:26.00,Default,,0,0,0,,Normal duration line.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        # 30 centiseconds = 300ms, which is >= 250ms, so no warning
        assert len(warnings) == 0

    def test_detect_very_short_duration_dialogue(self, temp_dir):
        """Test detection of a 5 centisecond (50ms) dialogue - should warn."""
        test_file = temp_dir / "very_short.ass"
        content = """[Script Info]
Title: Very Short Duration Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:24.32,0:05:24.37,Default,,0,0,0,,This is too short to display.
Dialogue: 0,0:05:25.00,0:05:26.00,Default,,0,0,0,,Normal duration line.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        # 5 centiseconds = 50ms, which is < 250ms, so should warn
        assert len(warnings) == 1
        assert "This is too short to display" in warnings[0]["text"]
        assert warnings[0]["duration_ms"] == 50

    def test_detect_boundary_250ms_dialogue(self, temp_dir):
        """Test detection of exactly 25 centisecond (250ms) dialogue - should not warn."""
        test_file = temp_dir / "boundary.ass"
        content = """[Script Info]
Title: Boundary Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:00.25,Default,,0,0,0,,Exactly 250ms duration.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        # 25 centiseconds = 250ms, which is exactly the threshold (not < 250ms)
        assert len(warnings) == 0

    def test_detect_below_boundary_240ms_dialogue(self, temp_dir):
        """Test detection of 24 centisecond (240ms) dialogue - should warn."""
        test_file = temp_dir / "below_boundary.ass"
        content = """[Script Info]
Title: Below Boundary Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:00.24,Default,,0,0,0,,Just under 250ms duration.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        # 24 centiseconds = 240ms, which is < 250ms
        assert len(warnings) == 1
        assert warnings[0]["duration_ms"] == 240

    def test_multiple_short_duration_dialogues(self, temp_dir):
        """Test detection of multiple short duration dialogues."""
        test_file = temp_dir / "multiple_short.ass"
        content = """[Script Info]
Title: Multiple Short Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:00.05,Default,,0,0,0,,First short line.
Dialogue: 0,0:01:01.00,0:01:02.00,Default,,0,0,0,,Normal duration line.
Dialogue: 0,0:01:03.00,0:01:03.10,Default,,0,0,0,,Second short line.
Dialogue: 0,0:01:04.00,0:01:04.08,Default,,0,0,0,,Third short line.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        # Should find 3 short lines (50ms, 100ms, 80ms - all < 250ms)
        assert len(warnings) == 3

    def test_warning_contains_timestamp_info(self, temp_dir):
        """Test that warning contains timestamp information."""
        test_file = temp_dir / "warning_info.ass"
        content = """[Script Info]
Title: Warning Info Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:24.32,0:05:24.40,Default,,0,0,0,,Short line with specific time.
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        assert len(warnings) == 1
        warning = warnings[0]
        assert warning["start"] == "0:05:24.32"
        assert warning["end"] == "0:05:24.40"
        assert warning["duration_ms"] == 80
        assert "Short line with specific time" in warning["text"]

    def test_no_dialogues_no_warnings(self, temp_dir):
        """Test that file with no dialogues produces no warnings."""
        test_file = temp_dir / "no_dialogues.ass"
        content = """[Script Info]
Title: No Dialogues Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        test_file.write_text(content)

        warnings = ass_qafix.detect_short_duration_dialogues(str(test_file))

        assert len(warnings) == 0


class TestShortDurationWarningIntegration:
    """Test integration of short duration warnings with main processing."""

    def test_process_ass_returns_short_duration_warnings(self, temp_dir, capsys):
        """Test that process_ass outputs warnings for short duration dialogues."""
        test_file = temp_dir / "integration_test.ass"
        content = """[Script Info]
Title: Integration Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:24.32,0:05:24.36,Default,,0,0,0,,Very short OCR error line.
Dialogue: 0,0:05:25.00,0:05:26.00,Default,,0,0,0,,Normal line.
"""
        test_file.write_text(content)

        # Process the file
        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Check stats include short duration removed count
        assert hasattr(stats, 'short_duration_removed')
        assert stats.short_duration_removed == 1
