"""
CLI tests for subextract argument parsing and main function.

Tests command-line interface behavior including path handling,
parallel worker validation, and integration with extraction functionality.
"""

from unittest.mock import patch
import sys
from pathlib import Path
import subextract


class TestArgumentParsing:
    """Test command-line argument parsing (handled in main function)."""

    def test_main_function_argument_parsing(self, temp_dir):
        """Test that main function correctly parses arguments."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.extract_subs_for_file') as mock_extract:
                mock_extract.return_value = (True, "Success")

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    with patch('builtins.print'):
                        result = subextract.main()

                        # Verify arguments were parsed correctly
                        mock_extract.assert_called_once_with(mkv_file, Path.cwd())
                        assert result == 0

    def test_main_function_parallel_parsing(self, temp_dir):
        """Test that main function correctly parses parallel argument."""
        # Create multiple MKV files
        for i in range(2):
            mkv_file = temp_dir / f"test{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.process_mkvs') as mock_process:
                mock_process.return_value = (2, 0)

                with patch('sys.argv', ['subextract', str(temp_dir), '--parallel', '4']):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        # Verify parallel argument was parsed correctly
                        mock_process.assert_called_once()
                        called_args = mock_process.call_args[0]
                        assert len(called_args) == 3  # mkv_files, outdir, max_workers
                        assert called_args[2] == 4  # max_workers should be 4
                        mock_print.assert_any_call("Processed with 4 workers:")
                        assert result == 0


class TestMainFunction:
    """Test main CLI function."""

    def test_main_single_file_success(self, temp_dir):
        """Test main function with single MKV file."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subextract.need') as mock_need:
            with patch('subextract.extract_subs_for_file') as mock_extract:
                mock_extract.return_value = (True, "Success")

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_need.assert_any_call('mkvmerge')
                        mock_need.assert_any_call('mkvextract')
                        mock_extract.assert_called_once_with(mkv_file, Path.cwd())
                        mock_print.assert_any_call("Done.")
                        assert result == 0

    def test_main_single_file_failure(self, temp_dir):
        """Test main function with failed extraction."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subextract.need'):
            with patch('subextract.extract_subs_for_file') as mock_extract:
                mock_extract.return_value = (False, "Extraction failed")

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_print.assert_any_call("Done with errors.", file=sys.stderr)
                        assert result == 1

    def test_main_directory_with_files(self, temp_dir):
        """Test main function with directory containing MKV files."""
        # Create multiple MKV files
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.process_mkvs') as mock_process:
                mock_process.return_value = (3, 0)  # 3 successful, 0 failed

                with patch('sys.argv', ['subextract', str(temp_dir)]):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_process.assert_called_once()
                        mock_print.assert_any_call("Successful: 3, Failed: 0")
                        mock_print.assert_any_call("Done.")
                        assert result == 0

    def test_main_directory_with_failures(self, temp_dir):
        """Test main function with directory processing failures."""
        # Create MKV files
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.process_mkvs') as mock_process:
                mock_process.return_value = (2, 1)  # 2 successful, 1 failed

                with patch('sys.argv', ['subextract', str(temp_dir)]):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_print.assert_any_call("Successful: 2, Failed: 1")
                        mock_print.assert_any_call("Done with errors.", file=sys.stderr)
                        assert result == 1

    def test_main_current_directory_no_files(self, temp_dir):
        """Test main function in current directory with no MKV files."""
        # Change to temp_dir for testing
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)

            with patch('subextract.need'):
                with patch('sys.argv', ['subextract']):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_print.assert_any_call("No .mkv files found in current directory.")
                        assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_main_current_directory_with_files(self, temp_dir):
        """Test main function in current directory with MKV files."""
        # Create MKV files in temp_dir
        for i in range(2):
            mkv_file = temp_dir / f"test{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        # Change to temp_dir for testing
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)

            with patch('subextract.need'):
                with patch('subextract.process_mkvs') as mock_process:
                    mock_process.return_value = (2, 0)

                    with patch('sys.argv', ['subextract']):
                        with patch('builtins.print') as mock_print:
                            result = subextract.main()

                            mock_process.assert_called_once()
                            mock_print.assert_any_call("Successful: 2, Failed: 0")
                            mock_print.assert_any_call("Done.")
                            assert result == 0
        finally:
            os.chdir(original_cwd)

    def test_main_parallel_processing(self, temp_dir):
        """Test main function with parallel processing."""
        # Create MKV files
        for i in range(4):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.process_mkvs') as mock_process:
                mock_process.return_value = (4, 0)

                with patch('sys.argv', ['subextract', str(temp_dir), '--parallel', '4']):
                    with patch('builtins.print') as mock_print:
                        result = subextract.main()

                        mock_process.assert_called_once()
                        mock_print.assert_any_call("Processed with 4 workers:")
                        mock_print.assert_any_call("Successful: 4, Failed: 0")
                        assert result == 0

    def test_main_directory_no_mkv_files(self, temp_dir):
        """Test main function with directory containing no MKV files."""
        # Create non-MKV files
        (temp_dir / "movie.mp4").write_bytes(b"video content")
        (temp_dir / "movie.srt").write_bytes(b"subtitle content")

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(temp_dir)]):
                with patch('builtins.print') as mock_print:
                    result = subextract.main()

                    mock_print.assert_any_call(f"No .mkv files found in '{temp_dir.name}'.")
                    assert result == 0

    def test_main_invalid_parallel_value(self, temp_dir):
        """Test main function with invalid parallel worker count."""
        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', '--parallel', '0']):
                with patch('builtins.print') as mock_print:
                    result = subextract.main()

                    mock_print.assert_any_call(
                        "Error: Number of parallel workers must be at least 1.",
                        file=sys.stderr
                    )
                    assert result == 1

    def test_main_negative_parallel_value(self, temp_dir):
        """Test main function with negative parallel worker count."""
        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', '--parallel', '-5']):
                with patch('builtins.print') as mock_print:
                    result = subextract.main()

                    mock_print.assert_any_call(
                        "Error: Number of parallel workers must be at least 1.",
                        file=sys.stderr
                    )
                    assert result == 1

    def test_main_non_mkv_file(self, temp_dir):
        """Test main function with non-MKV file."""
        txt_file = temp_dir / "document.txt"
        txt_file.write_text("not an mkv file")

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(txt_file)]):
                with patch('builtins.print') as mock_print:
                    result = subextract.main()

                    mock_print.assert_any_call(
                        "Error: argument must be a directory, a .mkv file, or omitted.",
                        file=sys.stderr
                    )
                    assert result == 1

    def test_main_nonexistent_path(self, temp_dir):
        """Test main function with non-existent path."""
        non_existent = temp_dir / "nonexistent"

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(non_existent)]):
                with patch('builtins.print') as mock_print:
                    result = subextract.main()

                    mock_print.assert_any_call(
                        "Error: argument must be a directory, a .mkv file, or omitted.",
                        file=sys.stderr
                    )
                    assert result == 1

    def test_main_custom_argv(self, temp_dir):
        """Test main function with custom argv argument."""
        mkv_file = temp_dir / "custom.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.extract_subs_for_file') as mock_extract:
                mock_extract.return_value = (True, "Success")

                with patch('builtins.print') as mock_print:
                    # Pass custom argv without program name (main() expects just arguments)
                    result = subextract.main([str(mkv_file)])

                    mock_extract.assert_called_once_with(mkv_file, Path.cwd())
                    mock_print.assert_any_call("Done.")
                    assert result == 0