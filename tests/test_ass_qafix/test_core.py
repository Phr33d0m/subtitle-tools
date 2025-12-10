"""
Test core functionality for ass_qafix.py.

This module tests the core processing logic and integration
functionality of the ass_qafix quality assurance and auto-fixer tool.
"""

from pathlib import Path

import ass_qafix


class TestCoreProcessing:
    """Test core processing functionality."""

    def test_process_ass_basic_functionality(self, sample_ass_file):
        """Test basic ASS file processing functionality."""
        # Process the sample file
        out_path, stats, report, canonical_block, have_canonical = ass_qafix.process_ass(
            str(sample_ass_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify output file was created
        out_path_obj = Path(out_path)
        assert out_path_obj.exists()
        assert out_path_obj != sample_ass_file  # Should be different file when not inplace

        # Verify stats are populated
        assert stats.dialogue_lines >= 0
        assert stats.fixed_lines >= 0

        # Verify report is generated
        assert "Processed" in report
        assert str(sample_ass_file.name) in report

    def test_process_ass_with_problems(self, problematic_ass_file):
        """Test processing of a file with known QA issues."""
        # Process the problematic file
        out_path, stats, report, canonical_block, have_canonical = ass_qafix.process_ass(
            str(problematic_ass_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify some fixes were applied
        assert stats.fixed_lines >= 0

        # Verify output file contains processed content
        processed_content = Path(out_path).read_text()
        assert "[Events]" in processed_content
        assert "Dialogue:" in processed_content

    def test_process_ass_dry_run(self, sample_ass_file):
        """Test dry-run mode doesn't modify files."""
        # Get original content
        original_content = sample_ass_file.read_text()
        original_mtime = sample_ass_file.stat().st_mtime

        # Process in dry-run mode
        out_path, stats, report, canonical_block, have_canonical = ass_qafix.process_ass(
            str(sample_ass_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=True,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify file is unchanged
        assert sample_ass_file.read_text() == original_content
        assert sample_ass_file.stat().st_mtime == original_mtime

        # Verify out_path is the original file
        assert out_path == str(sample_ass_file)

        # Verify report indicates dry run
        assert "[DRY RUN]" in report

    def test_process_ass_inplace(self, temp_dir):
        """Test inplace processing."""
        # Create a test file
        test_file = temp_dir / "inplace_test.ass"
        test_content = """[Script Info]
Title: Inplace Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:05.92,0:01:08.72,Default,,0,0,0,,Test inplace processing
"""
        test_file.write_text(test_content)

        # Process inplace
        out_path, stats, report, canonical_block, have_canonical = ass_qafix.process_ass(
            str(test_file),
            inplace=True,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify out_path is the original file
        assert out_path == str(test_file)

        # Verify file was modified (should have been processed)
        processed_content = test_file.read_text()
        assert "Dialogue:" in processed_content

        # Verify no .fixed file was created
        fixed_file = temp_dir / "inplace_test.fixed.ass"
        assert not fixed_file.exists()

    def test_load_and_save_ass(self, sample_ass_file):
        """Test loading and saving ASS files."""
        # Load the file
        doc = ass_qafix.load_ass(str(sample_ass_file))

        # Verify document structure
        assert hasattr(doc, 'lines')
        assert hasattr(doc, 'styles')
        assert hasattr(doc, 'events_format')
        assert len(doc.lines) > 0

        # Save to a new file
        temp_dir = sample_ass_file.parent
        saved_file = temp_dir / "saved_test.ass"

        ass_qafix.save_ass(str(saved_file), doc)

        # Verify saved file exists and has content
        assert saved_file.exists()
        saved_content = saved_file.read_text()
        assert len(saved_content) > 0

        # Clean up
        saved_file.unlink()

    def test_canonical_styles_handling(self, temp_dir):
        """Test canonical styles handling across multiple files."""
        # Create first file with custom styles
        file1 = temp_dir / "file1.ass"
        content1 = """[Script Info]
Title: File 1
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Custom,Arial,18,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,1,0,100,100,0,0,1,2,0,2,5,5,5,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Custom,,0,0,0,,Test with custom style
"""
        file1.write_text(content1)

        # Create second file with different styles
        file2 = temp_dir / "file2.ass"
        content2 = """[Script Info]
Title: File 2
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: AnotherStyle,Times New Roman,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:02:00.00,0:02:02.00,AnotherStyle,,0,0,0,,Test with another style
"""
        file2.write_text(content2)

        # Process first file to establish canonical styles
        out1, stats1, report1, canonical_block, have_canonical = ass_qafix.process_ass(
            str(file1),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Process second file using canonical styles from first
        out2, stats2, report2, _, _ = ass_qafix.process_ass(
            str(file2),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=canonical_block,
            have_canonical=True
        )

        # Verify both files were processed
        out1_path = Path(out1)
        out2_path = Path(out2)
        assert out1_path.exists()
        assert out2_path.exists()

        # Clean up
        out1_path.unlink()
        out2_path.unlink()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_dialogue_text_handling(self, temp_dir):
        """Test handling of empty dialogue text."""
        # Create file with empty text dialogues
        test_file = temp_dir / "empty_text.ass"
        content = """[Script Info]
Title: Empty Text Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,
Dialogue: 0,0:01:03.00,0:01:05.00,Default,,0,0,0,,Valid text
Dialogue: 0,0:01:06.00,0:01:08.00,Default,,0,0,0,,-
"""
        test_file.write_text(content)

        # Process with empty text removal (default behavior)
        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify empty text dialogues were removed
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should only have the dialogue with valid text
        assert len(dialogue_lines) == 1
        assert "Valid text" in dialogue_lines[0]

        # Clean up
        Path(out_path).unlink()

    def test_keep_empty_text_option(self, temp_dir):
        """Test keeping empty text when option is enabled."""
        # Create file with empty text dialogues
        test_file = temp_dir / "keep_empty.ass"
        content = """[Script Info]
Title: Keep Empty Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,
Dialogue: 0,0:01:03.00,0:01:05.00,Default,,0,0,0,,Valid text
"""
        test_file.write_text(content)

        # Process with keep empty text enabled
        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=True,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        # Verify empty text dialogues were kept
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have both dialogues
        assert len(dialogue_lines) == 2

        # Clean up
        Path(out_path).unlink()


class TestAlternatingOCRVariantMerge:
    """Test merging of alternating OCR variant patterns (e.g., traditional/simplified Chinese)."""

    def test_merge_alternating_trad_simp_chinese(self, temp_dir):
        """Test merging alternating traditional/simplified Chinese variants."""
        test_file = temp_dir / "alternating_variants.ass"
        content = """[Script Info]
Title: Alternating Variants Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:35.56,0:06:35.64,Default,,0,0,0,,沒本事就沒本事
Dialogue: 0,0:06:35.64,0:06:36.20,Default,,0,0,0,,没本事就没本事
Dialogue: 0,0:06:36.20,0:06:36.24,Default,,0,0,0,,沒本事就沒本事
Dialogue: 0,0:06:36.24,0:06:37.16,Default,,0,0,0,,没本事就没本事
Dialogue: 0,0:06:37.16,0:06:37.40,Default,,0,0,0,,沒本事就沒本事
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

        # Verify alternating merge happened
        assert stats.alternating_merges == 4  # 5 lines -> 1 line = 4 merges

        # Verify output has single merged line
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]
        assert len(dialogue_lines) == 1

        # Verify merged line uses first variant's text and spans full time range
        assert '沒本事就沒本事' in dialogue_lines[0]  # Traditional variant (first)
        assert '0:06:35.56' in dialogue_lines[0]  # Start time
        assert '0:06:37.40' in dialogue_lines[0]  # End time

        # Clean up
        Path(out_path).unlink()

    def test_no_merge_when_gap_exists(self, temp_dir):
        """Test that alternating patterns are NOT merged when there's a gap."""
        test_file = temp_dir / "alternating_with_gap.ass"
        content = """[Script Info]
Title: Alternating With Gap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:35.56,0:06:35.64,Default,,0,0,0,,沒本事就沒本事
Dialogue: 0,0:06:35.70,0:06:36.20,Default,,0,0,0,,没本事就没本事
Dialogue: 0,0:06:36.20,0:06:36.24,Default,,0,0,0,,沒本事就沒本事
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

        # Verify no alternating merge (gap between first and second line)
        assert stats.alternating_merges == 0

        # Clean up
        Path(out_path).unlink()

    def test_texts_are_ocr_variants_function(self):
        """Test the texts_are_ocr_variants helper function directly."""
        # Traditional/Simplified variants should match
        assert ass_qafix.texts_are_ocr_variants('沒本事就沒本事', '没本事就没本事') is True

        # Identical texts should match
        assert ass_qafix.texts_are_ocr_variants('hello', 'hello') is True

        # Very different texts should not match
        assert ass_qafix.texts_are_ocr_variants('hello', 'world') is False

        # Empty texts should not match
        assert ass_qafix.texts_are_ocr_variants('', 'hello') is False
        assert ass_qafix.texts_are_ocr_variants('hello', '') is False


class TestShortEchoMerge:
    """Test merging of short OCR echo lines paired with valid dialogue."""

    def test_merge_short_echo_after_long(self, temp_dir):
        """Test: long line followed by short echo → keep long's text."""
        test_file = temp_dir / "short_echo_after.ass"
        content = """[Script Info]
Title: Short Echo After Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:34.80,0:05:37.12,Default,,0,0,0,,嗯我也想去争一个名额
Dialogue: 0,0:05:37.12,0:05:37.16,Default,,0,0,0,,嗯我也想去爭 个名额
"""
        test_file.write_text(content)

        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 1 merged line
        assert len(dialogue_lines) == 1
        assert stats.consecutive_merges == 1

        # Verify kept the LONG line's text (first line)
        assert '嗯我也想去争一个名额' in dialogue_lines[0]
        # Verify time span covers both
        assert '0:05:34.80' in dialogue_lines[0]
        assert '0:05:37.16' in dialogue_lines[0]

        Path(out_path).unlink()

    def test_merge_short_echo_before_long(self, temp_dir):
        """Test: short echo followed by long line → keep long's text."""
        test_file = temp_dir / "short_echo_before.ass"
        content = """[Script Info]
Title: Short Echo Before Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:34.80,0:05:34.84,Default,,0,0,0,,嗯我也想去爭 个名额
Dialogue: 0,0:05:34.84,0:05:37.16,Default,,0,0,0,,嗯我也想去争一个名额
"""
        test_file.write_text(content)

        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 1 merged line
        assert len(dialogue_lines) == 1
        assert stats.consecutive_merges == 1

        # Verify kept the LONG line's text (second line)
        assert '嗯我也想去争一个名额' in dialogue_lines[0]
        # Verify time span covers both
        assert '0:05:34.80' in dialogue_lines[0]
        assert '0:05:37.16' in dialogue_lines[0]

        Path(out_path).unlink()

    def test_no_merge_with_gap(self, temp_dir):
        """Test: short echo with gap should NOT merge."""
        test_file = temp_dir / "short_echo_gap.ass"
        content = """[Script Info]
Title: Short Echo With Gap Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:34.80,0:05:37.12,Default,,0,0,0,,嗯我也想去争一个名额
Dialogue: 0,0:05:37.20,0:05:37.30,Default,,0,0,0,,嗯我也想去爭 个名额
"""
        test_file.write_text(content)

        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 lines (no merge due to gap)
        assert len(dialogue_lines) == 2

        Path(out_path).unlink()

    def test_no_merge_dissimilar_text(self, temp_dir):
        """Test: short line with very different text should NOT merge."""
        test_file = temp_dir / "short_dissimilar.ass"
        content = """[Script Info]
Title: Short Dissimilar Text Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:05:34.80,0:05:37.12,Default,,0,0,0,,这是第一句话
Dialogue: 0,0:05:37.12,0:05:37.22,Default,,0,0,0,,完全不同的内容
"""
        test_file.write_text(content)

        out_path, stats, report, _, _ = ass_qafix.process_ass(
            str(test_file),
            inplace=False,
            keep_empty_text=False,
            dry_run=False,
            canonical_styles_block=None,
            have_canonical=False
        )

        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have 2 lines (no merge due to dissimilar text)
        assert len(dialogue_lines) == 2

        Path(out_path).unlink()