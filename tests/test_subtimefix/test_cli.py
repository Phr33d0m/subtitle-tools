"""
CLI tests for subtimefix argument parsing and main function.

Tests command-line interface behavior including time shift validation,
path handling, and integration with timestamp fixing functionality.
"""

import pytest
import argparse
from unittest.mock import patch, Mock, call
import sys
from pathlib import Path
import subtimefix


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_parse_args_with_time_shift(self):
        """Test argument parsing with required time shift."""
        with patch('sys.argv', ['subtimefix', '--time', '5000']):
            args = subtimefix.parse_args()

            assert args.time == 5000
            assert args.path == '.'  # default value

    def test_parse_args_short_time_flag(self):
        """Test argument parsing with short time flag."""
        with patch('sys.argv', ['subtimefix', '-t', '-2000']):
            args = subtimefix.parse_args()

            assert args.time == -2000
            assert args.path == '.'

    def test_parse_args_negative_time_shift(self):
        """Test argument parsing with negative time shift."""
        with patch('sys.argv', ['subtimefix', '--time', '-3000']):
            args = subtimefix.parse_args()

            assert args.time == -3000
            assert args.path == '.'

    def test_parse_args_positive_time_shift(self):
        """Test argument parsing with positive time shift."""
        with patch('sys.argv', ['subtimefix', '--time', '6000']):
            args = subtimefix.parse_args()

            assert args.time == 6000
            assert args.path == '.'

    def test_parse_args_directory_path(self):
        """Test argument parsing with directory path."""
        with patch('sys.argv', ['subtimefix', '--time', '1000', '/path/to/subtitles']):
            args = subtimefix.parse_args()

            assert args.time == 1000
            assert args.path == '/path/to/subtitles'

    def test_parse_args_file_path(self):
        """Test argument parsing with specific file path."""
        with patch('sys.argv', ['subtimefix', '--time', '1500', 'subtitle.ass']):
            args = subtimefix.parse_args()

            assert args.time == 1500
            assert args.path == 'subtitle.ass'

    def test_parse_args_zero_time_shift(self):
        """Test argument parsing with zero time shift."""
        with patch('sys.argv', ['subtimefix', '--time', '0']):
            args = subtimefix.parse_args()

            assert args.time == 0
            assert args.path == '.'

    def test_parse_args_large_time_shift(self):
        """Test argument parsing with large time shift."""
        with patch('sys.argv', ['subtimefix', '--time', '3600000']):  # 1 hour
            args = subtimefix.parse_args()

            assert args.time == 3600000
            assert args.path == '.'

    def test_parse_args_missing_time(self):
        """Test argument parsing when required time is missing."""
        with patch('sys.argv', ['subtimefix']):
            with pytest.raises(SystemExit):
                subtimefix.parse_args()

    def test_parse_args_help(self):
        """Test help message display."""
        with patch('sys.argv', ['subtimefix', '--help']):
            with pytest.raises(SystemExit):
                subtimefix.parse_args()


class TestMainFunction:
    """Test main CLI function."""

    def test_main_single_file_success(self, temp_dir):
        """Test main function with single ASS file."""
        ass_file = temp_dir / "subtitle.ass"
        ass_content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Test subtitle line 1
Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,Test subtitle line 2
"""
        ass_file.write_text(ass_content)

        with patch('subtimefix.process_file') as mock_process:
            mock_process.return_value = (2, 4)  # 2 lines changed, 4 timestamps updated

            with patch('sys.argv', ['subtimefix', '--time', '5000', str(ass_file)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Verify success message was printed
                    mock_print.assert_any_call(f"[OK] {ass_file}: lines changed=2, timestamps updated=4")
                    mock_print.assert_any_call(
                        "\nProcessed 1 file(s). Shifted 5000 ms forward. "
                        "Lines changed: 2. Timestamps updated: 4."
                    )

    def test_main_directory_processing(self, temp_dir):
        """Test main function with directory processing."""
        subs_dir = temp_dir / "subtitles"
        subs_dir.mkdir()

        # Create multiple ASS files
        for i in range(3):
            ass_file = subs_dir / f"subtitle{i}.ass"
            ass_file.write_text(f"[Events]\nDialogue: 0,0:00:0{i}.00,0:00:0{i+1}.00,Default,,Test")

        with patch('subtimefix.process_file') as mock_process:
            mock_process.return_value = (1, 2)  # 1 line changed, 2 timestamps updated per file

            with patch('sys.argv', ['subtimefix', '--time', '2000', str(subs_dir)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should process all 3 files
                    assert mock_process.call_count == 3
                    # Should print final summary
                    mock_print.assert_any_call(
                        "\nProcessed 3 file(s). Shifted 2000 ms forward. "
                        "Lines changed: 3. Timestamps updated: 6."
                    )

    def test_main_negative_shift(self, temp_dir):
        """Test main function with negative time shift."""
        ass_file = temp_dir / "subtitle.ass"
        ass_file.write_text("[Events]\nDialogue: 0,0:00:05.00,0:00:06.00,Default,,Test")

        with patch('subtimefix.process_file') as mock_process:
            mock_process.return_value = (1, 2)

            with patch('sys.argv', ['subtimefix', '--time', '-1000', str(ass_file)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should report backward shift
                    mock_print.assert_any_call(
                        "\nProcessed 1 file(s). Shifted 1000 ms backward. "
                        "Lines changed: 1. Timestamps updated: 2."
                    )

    def test_main_zero_shift(self, temp_dir):
        """Test main function with zero time shift."""
        ass_file = temp_dir / "subtitle.ass"
        ass_file.write_text("[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,,Test")

        with patch('subtimefix.process_file') as mock_process:
            mock_process.return_value = (0, 0)  # No changes for zero shift

            with patch('sys.argv', ['subtimefix', '--time', '0', str(ass_file)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should report forward shift (even for zero)
                    mock_print.assert_any_call(
                        "\nProcessed 1 file(s). Shifted 0 ms forward. "
                        "Lines changed: 0. Timestamps updated: 0."
                    )

    def test_main_no_ass_files_found(self, temp_dir):
        """Test main function when no ASS files are found."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        with patch('sys.argv', ['subtimefix', '--time', '1000', str(empty_dir)]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    mock_print.assert_any_call(
                        "No .ass files found in the current directory.",
                        file=sys.stderr
                    )
                    mock_exit.assert_called_once_with(1)

    def test_main_processing_error(self, temp_dir):
        """Test main function when processing fails."""
        ass_file = temp_dir / "subtitle.ass"
        ass_file.write_text("test content")

        with patch('subtimefix.process_file') as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            with patch('sys.argv', ['subtimefix', '--time', '1000', str(ass_file)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should print error message
                    mock_print.assert_any_call(
                        f"[ERR] {ass_file}: Processing failed",
                        file=sys.stderr
                    )

    def test_main_non_ass_file_warning(self, temp_dir):
        """Test main function with non-ASS file (should warn and skip)."""
        txt_file = temp_dir / "subtitle.txt"
        txt_file.write_text("not an ass file")

        with patch('sys.argv', ['subtimefix', '--time', '1000', str(txt_file)]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should warn about non-ASS file
                    mock_print.assert_any_call(f"[WARN] Skipping non-.ass file: {txt_file}")
                    mock_exit.assert_called_once_with(1)

    def test_main_path_not_found(self, temp_dir):
        """Test main function when specified path doesn't exist."""
        non_existent = temp_dir / "nonexistent"

        with patch('sys.argv', ['subtimefix', '--time', '1000', str(non_existent)]):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should print error about missing path
                    mock_print.assert_any_call(
                        f"[ERR] Path not found: {non_existent}",
                        file=sys.stderr
                    )
                    mock_exit.assert_called_once_with(1)

    def test_main_mixed_success_and_failure(self, temp_dir):
        """Test main function with mixed successful and failed processing."""
        subs_dir = temp_dir / "subtitles"
        subs_dir.mkdir()

        good_file = subs_dir / "good.ass"
        bad_file = subs_dir / "bad.ass"
        good_file.write_text("[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,,Good")
        bad_file.write_text("bad content")

        with patch('subtimefix.process_file') as mock_process:
            # First call succeeds, second fails
            mock_process.side_effect = [(1, 2), Exception("Bad file")]

            with patch('sys.argv', ['subtimefix', '--time', '1000', str(subs_dir)]):
                with patch('builtins.print') as mock_print:
                    subtimefix.main()

                    # Should have one success and one error
                    assert mock_process.call_count == 2
                    # Should still print summary with successful processing
                    mock_print.assert_any_call(
                        "\nProcessed 1 file(s). Shifted 1000 ms forward. "
                        "Lines changed: 1. Timestamps updated: 2."
                    )

    def test_main_default_current_directory(self, temp_dir):
        """Test main function when no path is specified (uses current directory)."""
        # Change to temp_dir for testing
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)

            # Create ASS file in current directory
            ass_file = Path("subtitle.ass")
            ass_file.write_text("[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,,Test")

            with patch('subtimefix.process_file') as mock_process:
                mock_process.return_value = (1, 2)

                with patch('sys.argv', ['subtimefix', '--time', '3000']):
                    with patch('builtins.print') as mock_print:
                        subtimefix.main()

                        # Should process the file in current directory
                        mock_process.assert_called_once()
                        mock_print.assert_any_call(
                            "\nProcessed 1 file(s). Shifted 3000 ms forward. "
                            "Lines changed: 1. Timestamps updated: 2."
                        )
        finally:
            os.chdir(original_cwd)