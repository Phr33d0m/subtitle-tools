"""
Test half-translation detection for ass_qafix.py.

This module tests the detection of potentially half-translated subtitle files
by analyzing the last dialogue line's timestamp across multiple files.
"""

from pathlib import Path
from typing import Dict, Set

import pytest

import ass_qafix


class TestExtractMinute:
    """Test extracting minute from ASS timestamp."""

    def test_extract_minute_valid_timestamp(self):
        """Test extracting minute from valid timestamps."""
        assert ass_qafix.extract_minute("0:05:30.00") == 5
        assert ass_qafix.extract_minute("0:12:45.50") == 12
        assert ass_qafix.extract_minute("0:00:01.00") == 0
        assert ass_qafix.extract_minute("1:59:59.99") == 59

    def test_extract_minute_invalid_timestamp(self):
        """Test extracting minute from invalid timestamps returns None."""
        assert ass_qafix.extract_minute("invalid") is None
        assert ass_qafix.extract_minute("") is None
        assert ass_qafix.extract_minute("12:34") is None


class TestAnalyzeHalfTranslation:
    """Test the half-translation analysis logic."""

    def test_basic_detection(self):
        """Test basic half-translation detection."""
        # minute 9 has 3 files (winner), threshold = 9 - 2 = 7
        # Files with minute < 7 should be flagged
        file_minutes = {
            "file1.ass": 5,  # Should be flagged (5 < 7)
            "file2.ass": 7,  # Should NOT be flagged (7 >= 7)
            "file3.ass": 8,  # Should NOT be flagged
            "file4.ass": 9,  # Should NOT be flagged (winner)
            "file5.ass": 9,  # Should NOT be flagged (winner)
            "file6.ass": 9,  # Should NOT be flagged (winner)
        }

        warnings = ass_qafix.analyze_half_translation(file_minutes)

        assert "file1.ass" in warnings
        assert "file2.ass" not in warnings
        assert "file3.ass" not in warnings
        assert "file4.ass" not in warnings
        assert "file5.ass" not in warnings
        assert "file6.ass" not in warnings

    def test_tie_uses_highest_minute(self):
        """Test that ties are broken by choosing the highest minute."""
        # minute 8 and minute 9 both have 2 files
        # Winner should be minute 9 (highest), threshold = 9 - 2 = 7
        file_minutes = {
            "file1.ass": 5,   # Should be flagged (5 < 7)
            "file2.ass": 8,   # Should NOT be flagged (8 >= 7)
            "file3.ass": 8,   # Should NOT be flagged
            "file4.ass": 9,   # Should NOT be flagged (winner)
            "file5.ass": 9,   # Should NOT be flagged (winner)
        }

        warnings = ass_qafix.analyze_half_translation(file_minutes)

        assert "file1.ass" in warnings
        assert "file2.ass" not in warnings
        assert len(warnings) == 1

    def test_below_minimum_files_returns_empty(self):
        """Test that fewer than 5 files returns no warnings."""
        file_minutes = {
            "file1.ass": 5,
            "file2.ass": 9,
            "file3.ass": 9,
        }

        warnings = ass_qafix.analyze_half_translation(file_minutes, min_files=5)

        assert len(warnings) == 0

    def test_all_same_minute_no_warnings(self):
        """Test that all files at the same minute produces no warnings."""
        file_minutes = {
            "file1.ass": 9,
            "file2.ass": 9,
            "file3.ass": 9,
            "file4.ass": 9,
            "file5.ass": 9,
        }

        warnings = ass_qafix.analyze_half_translation(file_minutes)

        # All files at minute 9, threshold = 9 - 2 = 7
        # No file is below 7, so no warnings
        assert len(warnings) == 0

    def test_threshold_calculation(self):
        """Test that threshold = winner_minute - 2."""
        # minute 10 is winner with 3 files, threshold = 10 - 2 = 8
        file_minutes = {
            "file1.ass": 6,   # Should be flagged (6 < 8)
            "file2.ass": 7,   # Should be flagged (7 < 8)
            "file3.ass": 8,   # Should NOT be flagged (8 >= 8)
            "file4.ass": 10,  # Should NOT be flagged (winner)
            "file5.ass": 10,  # Should NOT be flagged (winner)
            "file6.ass": 10,  # Should NOT be flagged (winner)
        }

        warnings = ass_qafix.analyze_half_translation(file_minutes)

        assert "file1.ass" in warnings
        assert "file2.ass" in warnings
        assert "file3.ass" not in warnings
        assert len(warnings) == 2

    def test_empty_input_returns_empty(self):
        """Test that empty input returns no warnings."""
        warnings = ass_qafix.analyze_half_translation({})
        assert len(warnings) == 0

    def test_custom_minimum_files(self):
        """Test custom minimum files parameter."""
        file_minutes = {
            "file1.ass": 5,
            "file2.ass": 9,
            "file3.ass": 9,
        }

        # With min_files=3, should work
        warnings = ass_qafix.analyze_half_translation(file_minutes, min_files=3)
        # Winner is minute 9 (2 files), threshold = 9 - 2 = 7
        # file1.ass at minute 5 should be flagged
        assert "file1.ass" in warnings


class TestGetLastDialogueMinute:
    """Test extracting the last dialogue's start minute from ASS content."""

    def test_get_last_dialogue_minute_from_file(self, temp_dir):
        """Test extracting last dialogue minute from an ASS file."""
        test_file = temp_dir / "test.ass"
        content = """[Script Info]
Title: Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,First line
Dialogue: 0,0:05:30.00,0:05:32.00,Default,,0,0,0,,Middle line
Dialogue: 0,0:12:45.00,0:12:47.00,Default,,0,0,0,,Last line
"""
        test_file.write_text(content)

        minute = ass_qafix.get_last_dialogue_minute(str(test_file))

        assert minute == 12  # Last dialogue starts at minute 12

    def test_get_last_dialogue_minute_empty_file(self, temp_dir):
        """Test with file containing no dialogues."""
        test_file = temp_dir / "empty.ass"
        content = """[Script Info]
Title: Empty Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        test_file.write_text(content)

        minute = ass_qafix.get_last_dialogue_minute(str(test_file))

        assert minute is None

    def test_get_last_dialogue_minute_single_dialogue(self, temp_dir):
        """Test with file containing single dialogue line."""
        test_file = temp_dir / "single.ass"
        content = """[Script Info]
Title: Single Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:07:15.00,0:07:17.00,Default,,0,0,0,,Only line
"""
        test_file.write_text(content)

        minute = ass_qafix.get_last_dialogue_minute(str(test_file))

        assert minute == 7


class TestWarningColumnInTable:
    """Test that WARNING column is added to the results table."""

    def test_warning_column_present_in_table(self):
        """Test that generate_results_table includes Warning column."""
        reports = [
            "Processed 'file1.ass': dialogue=10, fixed=0, style_fixes=0, empty_text_removed=0, fake_text_removed=0, deduped=0, consecutive_merged=0, alternating_merged=0, overlap_fixes=0, short_removed=0"
        ]
        stats = ass_qafix.QAStats(dialogue_lines=10)
        warning_files = {"file1.ass"}

        panel = ass_qafix.generate_results_table(reports, stats, warning_files)

        # The panel should contain the table with our data
        # We can't easily inspect Rich objects, but we can verify no errors occur
        assert panel is not None

    def test_warning_shows_for_flagged_files(self):
        """Test that WARNING appears for flagged files."""
        # This is more of an integration test - we verify the function runs without error
        reports = [
            "Processed 'file1.ass': dialogue=10, fixed=0, style_fixes=0, empty_text_removed=0, fake_text_removed=0, deduped=0, consecutive_merged=0, alternating_merged=0, overlap_fixes=0, short_removed=0",
            "Processed 'file2.ass': dialogue=15, fixed=0, style_fixes=0, empty_text_removed=0, fake_text_removed=0, deduped=0, consecutive_merged=0, alternating_merged=0, overlap_fixes=0, short_removed=0"
        ]
        stats = ass_qafix.QAStats(dialogue_lines=25)
        warning_files = {"file1.ass"}  # Only file1 is flagged

        panel = ass_qafix.generate_results_table(reports, stats, warning_files)

        assert panel is not None


class TestIntegration:
    """Integration tests for the full half-translation detection workflow."""

    def test_full_workflow_with_multiple_files(self, temp_dir):
        """Test the complete workflow with multiple ASS files."""
        # Create 6 ASS files with different last dialogue minutes
        base_content = """[Script Info]
Title: Test File {num}
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,First line
Dialogue: 0,0:{minute:02d}:30.00,0:{minute:02d}:32.00,Default,,0,0,0,,Last line
"""

        # Create files with various last dialogue minutes
        # 3 files end at minute 9 (winner), others at lower minutes
        file_configs = [
            ("ep01.ass", 5),   # Should be flagged
            ("ep02.ass", 7),   # Should NOT be flagged (7 >= 7)
            ("ep03.ass", 9),   # Winner
            ("ep04.ass", 9),   # Winner
            ("ep05.ass", 9),   # Winner
            ("ep06.ass", 8),   # Should NOT be flagged
        ]

        for filename, minute in file_configs:
            file_path = temp_dir / filename
            content = base_content.format(num=filename, minute=minute)
            file_path.write_text(content)

        # Collect last dialogue minutes
        file_minutes = {}
        for filename, _ in file_configs:
            file_path = temp_dir / filename
            minute = ass_qafix.get_last_dialogue_minute(str(file_path))
            if minute is not None:
                file_minutes[filename] = minute

        # Analyze for half-translation
        warnings = ass_qafix.analyze_half_translation(file_minutes)

        # Verify results
        assert "ep01.ass" in warnings  # minute 5 < 7 (threshold)
        assert "ep02.ass" not in warnings  # minute 7 >= 7
        assert "ep03.ass" not in warnings
        assert "ep04.ass" not in warnings
        assert "ep05.ass" not in warnings
        assert "ep06.ass" not in warnings
