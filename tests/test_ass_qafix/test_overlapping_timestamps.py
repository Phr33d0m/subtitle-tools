"""
Test overlapping timestamp fixing functionality.

This module tests the feature that detects and fixes overlapping timestamps
between consecutive dialogue lines where the difference is less than 0.02 seconds.
"""

from pathlib import Path

from tests.test_ass_qafix.conftest import ass_qafix


class TestOverlappingTimestamps:
    """Test fixing overlapping timestamps between consecutive dialogue lines."""

    def test_simple_overlap_fix(self, temp_dir):
        """Test fixing simple overlapping timestamps as described in the requirements."""
        test_file = temp_dir / "overlap_test.ass"
        content = """[Script Info]
Title: Overlapping Timestamp Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:43.92,0:05:45.34,Default,,0,0,0,,I have someone I like
Dialogue: 0,0:05:45.33,0:05:46.41,Default,,0,0,0,,I can't accept you
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should still have 2 dialogue lines
        assert len(dialogue_lines) == 2

        # Check the first line: end should be changed from 0:05:45.34 to 0:05:45.33
        first_line = dialogue_lines[0]
        assert "0:05:43.92,0:05:45.33,Default,,0,0,0,,I have someone I like" in first_line

        # Check the second line: start should be changed from 0:05:45.33 to 0:05:45.34
        second_line = dialogue_lines[1]
        assert "0:05:45.34,0:05:46.41,Default,,0,0,0,,I can't accept you" in second_line

        # Verify stats show overlap fixes were applied
        assert stats.overlap_fixes > 0

        # Clean up
        Path(out_path).unlink()

    def test_no_overlap_scenario(self, temp_dir):
        """Test that non-overlapping timestamps are left unchanged."""
        test_file = temp_dir / "no_overlap_test.ass"
        content = """[Script Info]
Title: No Overlap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:43.92,0:05:45.20,Default,,0,0,0,,First line
Dialogue: 0,0:05:45.30,0:05:46.41,Default,,0,0,0,,Second line
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 dialogue lines
        assert len(dialogue_lines) == 2

        # Check that timestamps are unchanged (no overlap to fix)
        assert "0:05:43.92,0:05:45.20,Default,,0,0,0,,First line" in dialogue_lines[0]
        assert "0:05:45.30,0:05:46.41,Default,,0,0,0,,Second line" in dialogue_lines[1]

        # Verify no overlap fixes were applied
        assert stats.overlap_fixes == 0

        # Clean up
        Path(out_path).unlink()

    def test_multiple_overlapping_dialogues(self, temp_dir):
        """Test fixing multiple overlapping dialogues in sequence."""
        test_file = temp_dir / "multiple_overlap_test.ass"
        content = """[Script Info]
Title: Multiple Overlap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.50,Default,,0,0,0,,Line 1
Dialogue: 0,0:01:02.49,0:01:04.00,Default,,0,0,0,,Line 2
Dialogue: 0,0:01:04.00,0:01:06.00,Default,,0,0,0,,Line 3
Dialogue: 0,0:01:05.99,0:01:07.50,Default,,0,0,0,,Line 4
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 4 dialogue lines
        assert len(dialogue_lines) == 4

        # Check first overlap fix: Line 1 end should change from 2.50 to 2.49
        assert "0:01:00.00,0:01:02.49,Default,,0,0,0,,Line 1" in dialogue_lines[0]

        # Check second overlap fix: Line 2 start should change from 2.49 to 2.50
        assert "0:01:02.50,0:01:04.00,Default,,0,0,0,,Line 2" in dialogue_lines[1]

        # Check third overlap fix: Line 3 end should change from 6.00 to 5.99
        assert "0:01:04.00,0:01:05.99,Default,,0,0,0,,Line 3" in dialogue_lines[2]

        # Check fourth overlap fix: Line 4 start should change from 5.99 to 6.00
        assert "0:01:06.00,0:01:07.50,Default,,0,0,0,,Line 4" in dialogue_lines[3]

        # Verify multiple overlap fixes were applied
        assert stats.overlap_fixes >= 2

        # Clean up
        Path(out_path).unlink()

    def test_exact_timestamp_match(self, temp_dir):
        """Test handling of exact timestamp matches (end == start)."""
        test_file = temp_dir / "exact_match_test.ass"
        content = """[Script Info]
Title: Exact Match Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:03:15.20,0:03:17.45,Default,,0,0,0,,First line
Dialogue: 0,0:03:17.45,0:03:19.00,Default,,0,0,0,,Second line
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 dialogue lines
        assert len(dialogue_lines) == 2

        # Exact matches should not be changed (no overlap, just contiguous)
        assert "0:03:15.20,0:03:17.45,Default,,0,0,0,,First line" in dialogue_lines[0]
        assert "0:03:17.45,0:03:19.00,Default,,0,0,0,,Second line" in dialogue_lines[1]

        # No overlap fixes should be applied for exact matches
        assert stats.overlap_fixes == 0

        # Clean up
        Path(out_path).unlink()

    def test_large_gap_no_fix(self, temp_dir):
        """Test that large gaps between dialogues are not affected."""
        test_file = temp_dir / "large_gap_test.ass"
        content = """[Script Info]
Title: Large Gap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,First line
Dialogue: 0,0:01:05.00,0:01:07.00,Default,,0,0,0,,Second line
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 dialogue lines
        assert len(dialogue_lines) == 2

        # Large gaps should not be changed
        assert "0:01:00.00,0:01:02.00,Default,,0,0,0,,First line" in dialogue_lines[0]
        assert "0:01:05.00,0:01:07.00,Default,,0,0,0,,Second line" in dialogue_lines[1]

        # No overlap fixes should be applied
        assert stats.overlap_fixes == 0

        # Clean up
        Path(out_path).unlink()

    def test_integration_with_consecutive_merging(self, temp_dir):
        """Test that overlap fixing works correctly with consecutive dialogue merging."""
        test_file = temp_dir / "integration_test.ass"
        content = """[Script Info]
Title: Integration Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,Same text
Dialogue: 0,0:01:01.00,0:01:02.00,Default,,0,0,0,,Same text
Dialogue: 0,0:01:01.99,0:01:03.50,Default,,0,0,0,,Different text
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

        # Read the processed content
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 dialogue lines after consecutive merging:
        # 1. Merged "Same text" line (0:01:00.00 to 0:01:01.99 or 0:01:02.00 depending on merge logic)
        # 2. "Different text" line
        assert len(dialogue_lines) == 2

        # Check that the first line contains "Same text" and starts at 0:01:00.00
        first_line = dialogue_lines[0]
        assert "Same text" in first_line
        assert "0:01:00.00" in first_line

        # Check that the second line contains "Different text"
        second_line = dialogue_lines[1]
        assert "Different text" in second_line

        # The key point: after consecutive merging and overlap fixing,
        # there should be no remaining overlaps
        # Extract timestamps to verify
        first_end = first_line.split(",")[2]
        second_start = second_line.split(",")[1]

        # Convert to centiseconds and verify no overlap
        first_end_cs = ass_qafix.time_to_cs(first_end)
        second_start_cs = ass_qafix.time_to_cs(second_start)

        assert first_end_cs is not None
        assert second_start_cs is not None
        # First line should end at or before second line starts
        assert first_end_cs <= second_start_cs

        # Should have both consecutive merges and potentially overlap fixes
        assert stats.consecutive_merges > 0
        # overlap_fixes may be 0 or > 0 depending on how the merge algorithm works

        # Clean up
        Path(out_path).unlink()