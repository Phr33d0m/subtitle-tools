"""
Test consecutive dialogue line merging functionality.

This module tests the feature that merges consecutive dialogue lines
with the same text and contiguous timestamps into a single line.
"""

from pathlib import Path

from tests.test_ass_qafix.conftest import ass_qafix


class TestConsecutiveDialogueMerging:
    """Test merging of consecutive dialogue lines with same text and contiguous timestamps."""

    def test_merge_consecutive_dialogues_with_same_text(self, temp_dir):
        """Test merging consecutive dialogues with identical text and contiguous timestamps."""
        # Create test file with consecutive dialogues that should be merged
        test_file = temp_dir / "consecutive_test.ass"
        content = """[Script Info]
Title: Consecutive Dialogue Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:06.16,0:06:06.32,Default,,0,0,0,,Ten-Meridian Divine Sword
Dialogue: 0,0:06:06.32,0:06:06.56,Default,,0,0,0,,Ten-Meridian Divine Sword
Dialogue: 0,0:06:06.56,0:06:07.28,Default,,0,0,0,,Ten-Meridian Divine Sword
Dialogue: 0,0:06:08.00,0:06:09.00,Default,,0,0,0,,Different text
Dialogue: 0,0:06:10.00,0:06:10.50,Default,,0,0,0,,Another phrase
Dialogue: 0,0:06:10.50,0:06:11.00,Default,,0,0,0,,Another phrase
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

        # Should have 3 dialogue lines after merging:
        # 1. Merged line from 0:06:06.16 to 0:06:07.28
        # 2. "Different text" line
        # 3. Merged line from 0:06:10.00 to 0:06:11.00
        assert len(dialogue_lines) == 3

        # Check the first merged line
        first_line = dialogue_lines[0]
        assert "0:06:06.16,0:06:07.28,Default,,0,0,0,,Ten-Meridian Divine Sword" in first_line

        # Check the different text line is preserved
        second_line = dialogue_lines[1]
        assert "0:06:08.00,0:06:09.00,Default,,0,0,0,,Different text" in second_line

        # Check the second merged line
        third_line = dialogue_lines[2]
        assert "0:06:10.00,0:06:11.00,Default,,0,0,0,,Another phrase" in third_line

        # Verify stats show some dialogues were merged
        assert stats.consecutive_merges > 0  # This should be incremented when dialogues are merged

        # Clean up
        Path(out_path).unlink()

    def test_no_merge_when_text_differs(self, temp_dir):
        """Test that dialogues are not merged when text differs even with contiguous timestamps."""
        test_file = temp_dir / "different_text_test.ass"
        content = """[Script Info]
Title: Different Text Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:06.16,0:06:06.32,Default,,0,0,0,,First text
Dialogue: 0,0:06:06.32,0:06:06.56,Default,,0,0,0,,Second text
Dialogue: 0,0:06:06.56,0:06:07.28,Default,,0,0,0,,Third text
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

        # Should have all 3 original dialogues since text differs
        assert len(dialogue_lines) == 3

        # Verify all three different text lines are preserved
        assert "First text" in dialogue_lines[0]
        assert "Second text" in dialogue_lines[1]
        assert "Third text" in dialogue_lines[2]

        # Clean up
        Path(out_path).unlink()

    def test_no_merge_when_timestamps_not_contiguous(self, temp_dir):
        """Test that dialogues are merged when gaps are within 500ms but not when gaps exceed 500ms."""
        test_file = temp_dir / "non_contiguous_test.ass"
        content = """[Script Info]
Title: Non-Contiguous Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:06.16,0:06:06.32,Default,,0,0,0,,Same text
Dialogue: 0,0:06:07.00,0:06:07.20,Default,,0,0,0,,Same text
Dialogue: 0,0:06:07.40,0:06:08.00,Default,,0,0,0,,Same text
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

        # Should have 2 dialogue lines after merging:
        # Gap 1: 6:06.32 to 6:07.00 = 680ms (> 500ms, no merge)
        # Gap 2: 6:07.20 to 6:07.40 = 200ms (<= 500ms, merge lines 2 and 3)
        assert len(dialogue_lines) == 2

        # Check the first line (unchanged)
        first_line = dialogue_lines[0]
        assert "0:06:06.16,0:06:06.32,Default,,0,0,0,,Same text" in first_line

        # Check the merged line (lines 2 and 3 merged)
        second_line = dialogue_lines[1]
        assert "0:06:07.00,0:06:08.00,Default,,0,0,0,,Same text" in second_line

        # Clean up
        Path(out_path).unlink()

    def test_merge_multiple_consecutive_groups(self, temp_dir):
        """Test merging multiple groups of consecutive dialogues in the same file."""
        test_file = temp_dir / "multiple_groups_test.ass"
        content = """[Script Info]
Title: Multiple Groups Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,Phrase A
Dialogue: 0,0:01:01.00,0:01:02.00,Default,,0,0,0,,Phrase A
Dialogue: 0,0:01:05.00,0:01:06.00,Default,,0,0,0,,Phrase B
Dialogue: 0,0:01:06.00,0:01:07.00,Default,,0,0,0,,Phrase B
Dialogue: 0,0:01:07.00,0:01:08.50,Default,,0,0,0,,Phrase B
Dialogue: 0,0:02:00.00,0:02:01.00,Default,,0,0,0,,Phrase C
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

        # Should have 3 dialogue lines after merging:
        # 1. Phrase A merged (2 lines -> 1)
        # 2. Phrase B merged (3 lines -> 1)
        # 3. Phrase C (unchanged)
        assert len(dialogue_lines) == 3

        # Check merged phrase A line
        assert "0:01:00.00,0:01:02.00,Default,,0,0,0,,Phrase A" in dialogue_lines[0]

        # Check merged phrase B line
        assert "0:01:05.00,0:01:08.50,Default,,0,0,0,,Phrase B" in dialogue_lines[1]

        # Check phrase C line unchanged
        assert "0:02:00.00,0:02:01.00,Default,,0,0,0,,Phrase C" in dialogue_lines[2]

        # Clean up
        Path(out_path).unlink()

    def test_merge_dialogues_with_500ms_gap(self, temp_dir):
        """Test merging dialogues with identical text within 500ms gap (not necessarily contiguous)."""
        # Create test file with dialogues that should be merged due to small gap
        test_file = temp_dir / "gap_merging_test.ass"
        content = """[Script Info]
Title: Gap Merging Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:03:24.88,0:03:25.04,Default,,0,0,0,,Could it be
Dialogue: 0,0:03:25.44,0:03:25.60,Default,,0,0,0,,Could it be
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

        # Should have 1 dialogue line after merging the two lines
        assert len(dialogue_lines) == 1

        # Check the merged line spans from earliest start to latest end
        merged_line = dialogue_lines[0]
        assert "0:03:24.88,0:03:25.60,Default,,0,0,0,,Could it be" in merged_line

        # Verify stats show dialogues were merged
        assert stats.consecutive_merges > 0

        # Clean up
        Path(out_path).unlink()

    def test_merge_multiple_dialogues_with_mixed_gaps(self, temp_dir):
        """Test merging multiple dialogues where some gaps are within 500ms and some are not."""
        # Create test file with the specific example from the user request
        test_file = temp_dir / "mixed_gap_test.ass"
        content = """[Script Info]
Title: Mixed Gap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:04:49.60,0:04:50.48,Default,,0,0,0,,Gods' Fiery Abyss
Dialogue: 0,0:04:50.72,0:04:51.52,Default,,0,0,0,,Gods' Fiery Abyss
Dialogue: 0,0:04:51.81,0:04:52.20,Default,,0,0,0,,Gods' Fiery Abyss
Dialogue: 0,0:04:52.20,0:04:52.65,Default,,0,0,0,,Gods' Fiery Abyss
Dialogue: 0,0:04:53.72,0:04:54.52,Default,,0,0,0,,Gods' Fiery Abyss
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

        # Should have 2 dialogue lines after merging:
        # - First 4 lines merged (gaps are within 500ms): 0:04:49.60 to 0:04:52.65
        # - Last line remains separate (gap from 4:52.65 to 4:53.72 is 1070ms > 500ms)
        assert len(dialogue_lines) == 2

        # Check the first merged line
        first_line = dialogue_lines[0]
        assert "0:04:49.60,0:04:52.65,Default,,0,0,0,,Gods' Fiery Abyss" in first_line

        # Check the second line (unchanged)
        second_line = dialogue_lines[1]
        assert "0:04:53.72,0:04:54.52,Default,,0,0,0,,Gods' Fiery Abyss" in second_line

        # Verify stats show dialogues were merged
        assert stats.consecutive_merges > 0

        # Clean up
        Path(out_path).unlink()

    def test_no_merge_when_gap_exceeds_500ms(self, temp_dir):
        """Test that dialogues are not merged when gap exceeds 500ms."""
        # Create test file with dialogues that have gaps > 500ms
        test_file = temp_dir / "large_gap_test.ass"
        content = """[Script Info]
Title: Large Gap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,Same text
Dialogue: 0,0:01:02.00,0:01:02.50,Default,,0,0,0,,Same text
Dialogue: 0,0:01:03.10,0:01:03.50,Default,,0,0,0,,Same text
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

        # Should have all 3 original dialogues since gaps exceed 500ms
        # Gap 1: 1:01.00 to 1:02.00 = 1000ms
        # Gap 2: 1:02.50 to 1:03.10 = 600ms
        assert len(dialogue_lines) == 3

        # Clean up
        Path(out_path).unlink()

    def test_edge_case_exactly_500ms_gap(self, temp_dir):
        """Test that dialogues are merged when gap is exactly 500ms."""
        # Create test file with dialogues that have exactly 500ms gap
        test_file = temp_dir / "exact_500ms_test.ass"
        content = """[Script Info]
Title: Exact 500ms Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,Same text
Dialogue: 0,0:01:01.50,0:01:02.00,Default,,0,0,0,,Same text
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

        # Should have 1 dialogue line after merging (gap is exactly 500ms)
        assert len(dialogue_lines) == 1

        # Check the merged line spans from earliest start to latest end
        merged_line = dialogue_lines[0]
        assert "0:01:00.00,0:01:02.00,Default,,0,0,0,,Same text" in merged_line

        # Verify stats show dialogues were merged
        assert stats.consecutive_merges > 0

        # Clean up
        Path(out_path).unlink()


class TestFuzzyMerging:
    """Test fuzzy merging of consecutive dialogues with single-character differences (OCR correction)."""

    def test_merge_with_single_char_substitution_short_duration(self, temp_dir):
        """Test merging when texts differ by one substituted character and duration is short."""
        # This simulates OCR artifacts like 是又如何 vs 是叉如何
        test_file = temp_dir / "fuzzy_merge_test.ass"
        content = """[Script Info]
Title: Fuzzy Merge Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:08:13.92,0:08:13.96,Default,,0,0,0,,是又如何
Dialogue: 0,0:08:13.96,0:08:14.00,Default,,0,0,0,,是叉如何
Dialogue: 0,0:08:14.00,0:08:14.04,Default,,0,0,0,,是又如何
Dialogue: 0,0:08:14.04,0:08:14.08,Default,,0,0,0,,是叉如何
Dialogue: 0,0:08:14.08,0:08:14.16,Default,,0,0,0,,是又如何
Dialogue: 0,0:08:14.16,0:08:14.20,Default,,0,0,0,,是叉如何
Dialogue: 0,0:08:14.20,0:08:14.88,Default,,0,0,0,,是又如何
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

        # All lines should be merged since:
        # - They all have short duration (< 250ms)
        # - Texts differ by only 1 character (又 vs 叉)
        # - Gaps are within 500ms
        assert len(dialogue_lines) == 1

        # Check the merged line uses the first occurrence's text
        merged_line = dialogue_lines[0]
        assert "0:08:13.92" in merged_line
        assert "0:08:14.88" in merged_line
        assert "是又如何" in merged_line  # First occurrence's text preserved

        # Clean up
        Path(out_path).unlink()

    def test_no_fuzzy_merge_for_normal_duration(self, temp_dir):
        """Test that texts differing by one character are NOT merged when duration is normal."""
        # This simulates legitimate dialogue like "first layer" vs "second layer"
        test_file = temp_dir / "no_fuzzy_test.ass"
        content = """[Script Info]
Title: No Fuzzy Merge Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,突破一重
Dialogue: 0,0:01:02.00,0:01:04.00,Default,,0,0,0,,突破二重
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

        # Should NOT merge because duration is 2 seconds (> 250ms threshold)
        # even though texts differ by only 1 character (一 vs 二)
        assert len(dialogue_lines) == 2

        # Both original lines should be preserved
        assert "突破一重" in dialogue_lines[0]
        assert "突破二重" in dialogue_lines[1]

        # Clean up
        Path(out_path).unlink()

    def test_no_merge_with_two_char_difference(self, temp_dir):
        """Test that texts differing by 2+ characters are NOT merged even with consecutive timestamps."""
        test_file = temp_dir / "two_char_diff_test.ass"
        content = """[Script Info]
Title: Two Char Diff Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:08:13.90,0:08:14.00,Default,,0,0,0,,ABCD
Dialogue: 0,0:08:14.00,0:08:14.10,Default,,0,0,0,,AXYZ
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

        # Should NOT merge because texts differ by 3 characters (BCD vs XYZ)
        assert len(dialogue_lines) == 2

        # Clean up
        Path(out_path).unlink()

    def test_fuzzy_merge_preserves_first_text(self, temp_dir):
        """Test that the first occurrence's text is preserved when fuzzy merging."""
        test_file = temp_dir / "preserve_first_test.ass"
        content = """[Script Info]
Title: Preserve First Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:08:13.92,0:08:13.96,Default,,0,0,0,,HelloX
Dialogue: 0,0:08:13.96,0:08:14.00,Default,,0,0,0,,HelloY
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

        # Should merge and keep first text "HelloX"
        assert len(dialogue_lines) == 1
        assert "HelloX" in dialogue_lines[0]
        assert "HelloY" not in dialogue_lines[0]

        # Clean up
        Path(out_path).unlink()


class TestTextsMatchForMerge:
    """Unit tests for the texts_match_for_merge function."""

    def test_exact_match_always_matches(self):
        """Test that identical texts always match regardless of duration."""
        assert ass_qafix.texts_match_for_merge("hello", "hello", None) is True
        assert ass_qafix.texts_match_for_merge("hello", "hello", 100) is True
        assert ass_qafix.texts_match_for_merge("hello", "hello", 5) is True

    def test_single_char_diff_matches_only_for_short_duration(self):
        """Test that single-char diff only matches for short duration lines."""
        # Short duration (< 25cs) - should match
        assert ass_qafix.texts_match_for_merge("hello", "hallo", 5) is True
        assert ass_qafix.texts_match_for_merge("是又如何", "是叉如何", 4) is True

        # Normal duration (>= 25cs) - should NOT match
        assert ass_qafix.texts_match_for_merge("hello", "hallo", 100) is False
        assert ass_qafix.texts_match_for_merge("是又如何", "是叉如何", 200) is False

    def test_two_char_diff_never_matches(self):
        """Test that two-char diffs never match even with short duration."""
        assert ass_qafix.texts_match_for_merge("hello", "hxxlo", 5) is False
        assert ass_qafix.texts_match_for_merge("ABCD", "AXYZ", 4) is False

    def test_none_duration_only_allows_exact_match(self):
        """Test that None duration only allows exact matches."""
        assert ass_qafix.texts_match_for_merge("hello", "hello", None) is True
        assert ass_qafix.texts_match_for_merge("hello", "hallo", None) is False