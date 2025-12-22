"""
Test OCR artifact removal functionality for ass_qafix.py.

This module tests the detection and removal of OCR artifacts such as:
- Random numbers (e.g., "1", "42", "123")
- Single letters (e.g., "A", "b", "X")
- Other common OCR noise patterns
"""

from pathlib import Path

from tests.test_ass_qafix.conftest import ass_qafix


class TestOCRArtifactRemoval:
    """Test detection and removal of OCR artifacts."""

    def test_removal_of_random_numbers(self, temp_dir):
        """Test that dialogue lines with only random numbers are removed."""
        # Create test file with random number dialogues
        test_file = temp_dir / "random_numbers.ass"
        content = """[Script Info]
Title: Random Numbers Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:08:24.88,0:08:24.96,Default,,0,0,0,,1
Dialogue: 0,0:08:25.00,0:08:25.08,Default,,0,0,0,,42
Dialogue: 0,0:08:26.12,0:08:26.20,Default,,0,0,0,,123
Dialogue: 0,0:08:27.00,0:08:27.08,Default,,0,0,0,,This is valid text
Dialogue: 0,0:08:28.15,0:08:28.23,Default,,0,0,0,,9999
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

        # Verify random numbers were removed as fake text
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should only have the dialogue with valid text
        assert len(dialogue_lines) == 1
        assert "This is valid text" in dialogue_lines[0]

        # Verify fake text removal stats
        assert stats.fake_text_removed >= 4  # At least 4 random numbers removed

        # Clean up
        Path(out_path).unlink()

    def test_removal_of_invalid_letter_combos(self, temp_dir):
        """Test that invalid letter combinations (not in dictionary) are removed."""
        # Create test file with invalid letter combo dialogues
        # Note: Single letters like A, X are valid words in English dictionary
        # We test combos that are NOT valid words: fi, TT, rr, etc.
        test_file = temp_dir / "invalid_letters.ass"
        content = """[Script Info]
Title: Invalid Letter Combos Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:06:19.68,0:06:19.76,Default,,0,0,0,,fi
Dialogue: 0,0:06:20.00,0:06:20.08,Default,,0,0,0,,TT
Dialogue: 0,0:06:21.12,0:06:21.20,Default,,0,0,0,,rr
Dialogue: 0,0:06:22.00,0:06:22.08,Default,,0,0,0,,Another valid subtitle
Dialogue: 0,0:06:23.15,0:06:23.23,Default,,0,0,0,,qq
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

        # Verify invalid letter combos were removed as fake text
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should only have the dialogue with valid text
        assert len(dialogue_lines) == 1
        assert "Another valid subtitle" in dialogue_lines[0]

        # Verify fake text removal stats
        assert stats.fake_text_removed >= 4  # At least 4 invalid combos removed

        # Clean up
        Path(out_path).unlink()

    def test_mixed_ocr_artifacts(self, temp_dir):
        """Test removal of mixed OCR artifacts (numbers, invalid letters, punctuation)."""
        # Create test file with mixed OCR artifacts
        # Note: Single valid letters (A, x, M) are kept because they're in dictionary
        test_file = temp_dir / "mixed_artifacts.ass"
        content = """[Script Info]
Title: Mixed OCR Artifacts Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,1
Dialogue: 0,0:01:04.00,0:01:05.00,Default,,0,0,0,,42
Dialogue: 0,0:01:06.00,0:01:07.00,Default,,0,0,0,,fi
Dialogue: 0,0:01:08.00,0:01:09.00,Default,,0,0,0,,999
Dialogue: 0,0:01:10.00,0:01:11.00,Default,,0,0,0,,This should remain
Dialogue: 0,0:01:12.00,0:01:13.00,Default,,0,0,0,,TT
Dialogue: 0,0:01:14.00,0:01:15.00,Default,,0,0,0,,.
Dialogue: 0,0:01:16.00,0:01:17.00,Default,,0,0,0,,」
Dialogue: 0,0:01:18.00,0:01:19.00,Default,,0,0,0,,7
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

        # Verify only the valid text remains
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should only have the dialogue with valid text
        assert len(dialogue_lines) == 1
        assert "This should remain" in dialogue_lines[0]

        # Verify fake text removal stats (numbers, invalid letter combos, punctuation)
        assert stats.fake_text_removed >= 8

        # Clean up
        Path(out_path).unlink()

    def test_keep_valid_short_text(self, temp_dir):
        """Test that valid short text is not mistakenly removed."""
        # Create test file with valid but short text
        test_file = temp_dir / "valid_short.ass"
        content = """[Script Info]
Title: Valid Short Text Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,Hi
Dialogue: 0,0:01:03.00,0:01:05.00,Default,,0,0,0,,OK
Dialogue: 0,0:01:06.00,0:01:08.00,Default,,0,0,0,,Go!
Dialogue: 0,0:01:09.00,0:01:11.00,Default,,0,0,0,,Yes
Dialogue: 0,0:01:12.00,0:01:14.00,Default,,0,0,0,,No
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

        # Verify valid short text is preserved
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should have all the valid short text dialogues
        assert len(dialogue_lines) == 5
        texts = [line.split(',')[-1] for line in dialogue_lines]
        assert "Hi" in texts
        assert "OK" in texts
        assert "Go!" in texts
        assert "Yes" in texts
        assert "No" in texts

        # Verify no fake text was removed
        assert stats.fake_text_removed == 0

        # Clean up
        Path(out_path).unlink()

    def test_direct_is_fake_text_function(self):
        """Test the is_fake_text function directly with various inputs."""
        # Test random numbers - these should be detected as fake
        assert ass_qafix.is_fake_text("1") is True
        assert ass_qafix.is_fake_text("42") is True
        assert ass_qafix.is_fake_text("123") is True
        assert ass_qafix.is_fake_text("9999") is True

        # Test invalid letter combos (not in dictionary) - should be detected as fake
        assert ass_qafix.is_fake_text("fi") is True  # ligature fragment
        assert ass_qafix.is_fake_text("TT") is True  # double T
        assert ass_qafix.is_fake_text("rr") is True  # double r

        # Single letters are artifacts except "I" (for Chinese donghua context)
        assert ass_qafix.is_fake_text("A") is True  # Single letter = artifact
        assert ass_qafix.is_fake_text("r") is True  # Single letter = artifact
        assert ass_qafix.is_fake_text("I") is False  # Only "I" is valid (pronoun)

        # Valid two-letter words (in dictionary) - should NOT be fake
        assert ass_qafix.is_fake_text("hi") is False  # Valid word
        assert ass_qafix.is_fake_text("no") is False  # Valid word

        # Test single punctuation - these should be detected as fake
        assert ass_qafix.is_fake_text(".") is True
        assert ass_qafix.is_fake_text("」") is True

        # Test underscore OCR artifacts - these should be detected as fake
        assert ass_qafix.is_fake_text("_") is True  # Single underscore
        assert ass_qafix.is_fake_text("__") is True  # Repeated underscores (same character)
        assert ass_qafix.is_fake_text("_ ") is True  # Underscore with space (after trimming)

        # Test valid text that should NOT be detected as fake
        assert ass_qafix.is_fake_text("Hello") is False
        assert ass_qafix.is_fake_text("Hi") is False  # Valid 2-letter word
        assert ass_qafix.is_fake_text("OK") is False
        assert ass_qafix.is_fake_text("Go!") is False
        assert ass_qafix.is_fake_text("Yes?") is False
        assert ass_qafix.is_fake_text("") is False  # Empty text is not fake
        assert ass_qafix.is_fake_text("   ") is False  # Whitespace only is not fake

    def test_removal_of_underscore_artifacts(self, temp_dir):
        """Test that dialogue lines with only underscore artifacts are removed."""
        # Create test file with underscore dialogues
        test_file = temp_dir / "underscore_artifacts.ass"
        content = """[Script Info]
Title: Underscore Artifacts Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:08:24.88,0:08:24.96,Default,,0,0,0,,_
Dialogue: 0,0:08:25.00,0:08:25.08,Default,,0,0,0,,__
Dialogue: 0,0:08:26.12,0:08:26.20,Default,,0,0,0,,_
Dialogue: 0,0:08:27.00,0:08:27.08,Default,,0,0,0,,This is valid text
Dialogue: 0,0:08:28.15,0:08:28.23,Default,,0,0,0,,___
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

        # Verify underscores were removed as fake text
        processed_content = Path(out_path).read_text()
        dialogue_lines = [line for line in processed_content.split('\n') if line.startswith('Dialogue:')]

        # Should only have the dialogue with valid text
        assert len(dialogue_lines) == 1
        assert "This is valid text" in dialogue_lines[0]

        # Verify fake text removal stats
        assert stats.fake_text_removed >= 4  # At least 4 underscore artifacts removed

        # Clean up
        Path(out_path).unlink()


class TestDictionaryBasedOCRDetection:
    """Test dictionary-based OCR artifact detection (English + Chinese)."""

    def test_multi_dash_patterns(self):
        """Test that multi-dash patterns are detected as artifacts."""
        assert ass_qafix.is_fake_text("--") is True
        assert ass_qafix.is_fake_text("---") is True
        assert ass_qafix.is_fake_text("- -") is True
        assert ass_qafix.is_fake_text("-  -") is True
        # Single dash is also caught as single punctuation
        assert ass_qafix.is_fake_text("-") is True

    def test_backtick_patterns(self):
        """Test that backtick patterns are detected as artifacts."""
        assert ass_qafix.is_fake_text("`") is True
        assert ass_qafix.is_fake_text("``") is True
        assert ass_qafix.is_fake_text("```") is True

    def test_replacement_character(self):
        """Test that text with replacement character □ is detected as artifact."""
        assert ass_qafix.is_fake_text("□") is True
        assert ass_qafix.is_fake_text("□方") is True
        assert ass_qafix.is_fake_text("山口□") is True
        # Valid text with □ should still be artifact
        assert ass_qafix.is_fake_text("Hello□World") is True

    def test_english_dictionary_validation(self):
        """Test that English 1-2 letter words are validated against dictionary."""
        # Valid English words should pass
        assert ass_qafix.is_fake_text("hi") is False
        assert ass_qafix.is_fake_text("no") is False
        assert ass_qafix.is_fake_text("go") is False
        assert ass_qafix.is_fake_text("is") is False
        assert ass_qafix.is_fake_text("it") is False
        assert ass_qafix.is_fake_text("Hi") is False  # Case insensitive
        assert ass_qafix.is_fake_text("NO") is False

        # Invalid English letter combos should be detected as artifacts
        assert ass_qafix.is_fake_text("fi") is True  # ligature fragment
        assert ass_qafix.is_fake_text("TT") is True  # double T
        assert ass_qafix.is_fake_text("rr") is True  # double r

    def test_english_letter_with_punctuation(self):
        """Test letter+punctuation patterns like 'r.' or 'A -'."""
        # Single letter + punctuation is always artifact (except "I")
        assert ass_qafix.is_fake_text("r.") is True  # single letter + garbage
        assert ass_qafix.is_fake_text("A -") is True  # single letter + garbage
        assert ass_qafix.is_fake_text("X.") is True  # single letter + garbage
        # Two-letter invalid combos with punctuation
        assert ass_qafix.is_fake_text("rr.") is True
        assert ass_qafix.is_fake_text("fi.") is True
        assert ass_qafix.is_fake_text("TT ") is True

    def test_cjk_dictionary_validation(self):
        """Test that single CJK characters are validated against jieba3 dictionary."""
        # Valid CJK characters (in dictionary) should pass
        assert ass_qafix.is_fake_text("哼") is False  # interjection
        assert ass_qafix.is_fake_text("嗯") is False  # interjection
        assert ass_qafix.is_fake_text("啊") is False  # interjection
        assert ass_qafix.is_fake_text("是") is False  # common word
        assert ass_qafix.is_fake_text("好") is False  # common word
        assert ass_qafix.is_fake_text("一") is False  # common word

        # Multi-char CJK strings are not checked by single-char logic
        assert ass_qafix.is_fake_text("你好") is False
        assert ass_qafix.is_fake_text("谢谢") is False

    def test_valid_short_text_preserved(self):
        """Test that valid short text is preserved."""
        # These should all be valid
        assert ass_qafix.is_fake_text("Hi") is False
        assert ass_qafix.is_fake_text("OK") is False
        assert ass_qafix.is_fake_text("Go") is False
        assert ass_qafix.is_fake_text("No") is False
        assert ass_qafix.is_fake_text("哼") is False
        assert ass_qafix.is_fake_text("嗯") is False

    def test_integration_multi_dash_removal(self, temp_dir):
        """Test that multi-dash artifacts are removed in file processing."""
        test_file = temp_dir / "multi_dash.ass"
        content = """[Script Info]
Title: Multi-dash Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:01.00,Default,,0,0,0,,--
Dialogue: 0,0:01:02.00,0:01:03.00,Default,,0,0,0,,---
Dialogue: 0,0:01:04.00,0:01:05.00,Default,,0,0,0,,- -
Dialogue: 0,0:01:06.00,0:01:07.00,Default,,0,0,0,,Valid subtitle text
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

        assert len(dialogue_lines) == 1
        assert "Valid subtitle text" in dialogue_lines[0]
        assert stats.fake_text_removed >= 3

        Path(out_path).unlink()

    def test_short_duration_single_cjk_removal(self, temp_dir):
        """Test that single CJK characters with very short duration (<50ms) are removed."""
        test_file = temp_dir / "short_cjk.ass"
        content = """[Script Info]
Title: Short Duration CJK Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:04:49.20,0:04:49.24,Default,,0,0,0,,山
Dialogue: 0,0:09:07.00,0:09:07.04,Default,,0,0,0,,及
Dialogue: 0,0:09:08.56,0:09:08.60,Default,,0,0,0,,号
Dialogue: 0,0:10:00.00,0:10:00.10,Default,,0,0,0,,是
Dialogue: 0,0:11:00.00,0:11:00.10,Default,,0,0,0,,你好
Dialogue: 0,0:12:00.00,0:12:01.00,Default,,0,0,0,,Valid subtitle text
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

        # Should have 3 lines: 是 (100ms), 你好 (100ms multi-char), Valid subtitle text
        assert len(dialogue_lines) == 3

        # Verify 40ms single CJK chars were removed (山, 及, 号)
        assert stats.short_duration_removed == 3

        # Verify kept lines
        texts = [line.split(',,')[-1] for line in dialogue_lines]
        assert '是' in texts  # 100ms single CJK - kept
        assert '你好' in texts  # 100ms multi-char - kept
        assert 'Valid subtitle text' in texts

        Path(out_path).unlink()