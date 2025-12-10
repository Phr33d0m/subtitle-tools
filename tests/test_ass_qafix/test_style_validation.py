"""
Test style validation functionality.

This module tests the feature that validates all styles used in Dialogue lines
against the styles defined in the [V4+ Styles] section.
"""

from pathlib import Path

import ass_qafix


class TestStyleValidation:
    """Test validation of dialogue styles against defined styles."""

    def test_valid_styles_in_styles_section(self, temp_dir):
        """Test that dialogues use only styles that exist in the Styles section."""
        test_file = temp_dir / "valid_styles.ass"
        content = """[Script Info]
Title: Valid Styles Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: Title,Times New Roman,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1
Style: Subtitle,Arial,18,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,This uses Default style
Dialogue: 0,0:01:03.00,0:01:05.00,Title,,0,0,0,,This uses Title style
Dialogue: 0,0:01:06.00,0:01:08.00,Subtitle,,0,0,0,,This uses Subtitle style
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

        # All styles are valid, so no style fixes should be applied
        assert stats.style_fixes == 0

        # All dialogues should be preserved with their original styles
        assert len(dialogue_lines) == 3
        assert ",Default,," in dialogue_lines[0]
        assert ",Title,," in dialogue_lines[1]
        assert ",Subtitle,," in dialogue_lines[2]

        # Clean up
        Path(out_path).unlink()

    def test_invalid_styles_get_fixed(self, temp_dir):
        """Test that dialogues with invalid styles get fixed to Default."""
        test_file = temp_dir / "invalid_styles.ass"
        content = """[Script Info]
Title: Invalid Styles Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: Title,Times New Roman,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,Default,,0,0,0,,This uses valid Default style
Dialogue: 0,0:01:03.00,0:01:05.00,NonExistentStyle,,0,0,0,,This uses invalid style
Dialogue: 0,0:01:06.00,0:01:08.00,AnotherBadStyle,,0,0,0,,This also uses invalid style
Dialogue: 0,0:01:09.00,0:01:11.00,Title,,0,0,0,,This uses valid Title style
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

        # Should have fixed 2 invalid styles
        assert stats.style_fixes == 2

        # All dialogues should be preserved, but invalid styles changed to Default
        assert len(dialogue_lines) == 4

        # Check that valid styles are preserved
        assert ",Default,," in dialogue_lines[0]
        assert ",Title,," in dialogue_lines[3]

        # Check that invalid styles were changed to Default
        for line in dialogue_lines[1:3]:  # The two lines with invalid styles
            assert ",Default,," in line

        # Clean up
        Path(out_path).unlink()

    def test_no_styles_section_defaults_all(self, temp_dir):
        """Test that when no Styles section exists, all dialogues get Default style."""
        test_file = temp_dir / "no_styles.ass"
        content = """[Script Info]
Title: No Styles Test
ScriptType: v4.00+

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,SomeStyle,,0,0,0,,This will become Default
Dialogue: 0,0:01:03.00,0:01:05.00,AnotherStyle,,0,0,0,,This will also become Default
Dialogue: 0,0:01:06.00,0:01:08.00,ThirdStyle,,0,0,0,,This will also become Default
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

        # Should have fixed all 3 styles since no styles section exists
        assert stats.style_fixes == 3

        # All dialogues should have Default style
        assert len(dialogue_lines) == 3
        for line in dialogue_lines:
            assert ",Default,," in line

        # Clean up
        Path(out_path).unlink()

    def test_mixed_valid_and_invalid_case_insensitive(self, temp_dir):
        """Test style validation with mixed case and case-insensitive matching."""
        test_file = temp_dir / "mixed_case.ass"
        content = """[Script Info]
Title: Mixed Case Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: customstyle,Times New Roman,22,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,15,15,15,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,default,,0,0,0,,Lowercase default should match
Dialogue: 0,0:01:03.00,0:01:05.00,CUSTOMSTYLE,,0,0,0,,Uppercase should match
Dialogue: 0,0:01:06.00,0:01:08.00,CustomStyle,,0,0,0,,Mixed case should match
Dialogue: 0,0:01:09.00,0:01:11.00,NonExistent,,0,0,0,,This should become Default
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

        # Should have fixed only 1 invalid style
        assert stats.style_fixes == 1

        # All dialogues should be preserved
        assert len(dialogue_lines) == 4

        # Check that valid styles (case-insensitive) are preserved as Default
        # (the script normalizes them to the exact style name from the Styles section)
        for line in dialogue_lines[:3]:  # First three should have valid styles
            # The first should be "Default" (case normalized)
            assert ",Default,," in line or ",customstyle,," in line

        # The last one should be changed to Default
        assert ",Default,," in dialogue_lines[3]

        # Clean up
        Path(out_path).unlink()

    def test_empty_style_name_gets_fixed(self, temp_dir):
        """Test that empty style names get fixed to Default."""
        test_file = temp_dir / "empty_style.ass"
        content = """[Script Info]
Title: Empty Style Test
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:01:00.00,0:01:02.00,,,0,0,0,,Empty style
Dialogue: 0,0:01:03.00,0:01:05.00,Default,,0,0,0,,Valid style
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

        # Should have fixed 1 empty style
        assert stats.style_fixes == 1

        # All dialogues should have Default style
        assert len(dialogue_lines) == 2
        for line in dialogue_lines:
            assert ",Default," in line

        # Clean up
        Path(out_path).unlink()