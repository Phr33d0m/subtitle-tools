"""
CLI tests for subextract argument parsing and main function.

Tests command-line interface behavior including path handling,
parallel worker validation, and integration with extraction functionality.
"""

from unittest.mock import patch, MagicMock
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
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (1, 0, 0)

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    result = subextract.main()

                    # Verify process_files was called with the correct file
                    mock_processor.process_files.assert_called_once()
                    call_args = mock_processor.process_files.call_args
                    assert call_args[0][0] == [mkv_file]  # mkv_files list
                    assert result == 0

    def test_main_function_parallel_parsing(self, temp_dir):
        """Test that main function correctly parses parallel argument."""
        # Create multiple MKV files
        for i in range(2):
            mkv_file = temp_dir / f"test{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (2, 0, 0)

                with patch('sys.argv', ['subextract', str(temp_dir), '--parallel', '4']):
                    result = subextract.main()

                    # Verify parallel argument was parsed correctly
                    mock_processor.process_files.assert_called_once()
                    call_args = mock_processor.process_files.call_args
                    assert call_args[0][2] == 4  # max_workers should be 4
                    assert result == 0


class TestMainFunction:
    """Test main CLI function."""

    def test_main_single_file_success(self, temp_dir):
        """Test main function with single MKV file."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subextract.need') as mock_need:
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (1, 0, 0)

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    result = subextract.main()

                    mock_need.assert_any_call('mkvmerge')
                    mock_need.assert_any_call('mkvextract')
                    mock_processor.process_files.assert_called_once()
                    assert result == 0

    def test_main_single_file_failure(self, temp_dir):
        """Test main function with failed extraction."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subextract.need'):
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (0, 1, 0)  # 1 failed

                with patch('sys.argv', ['subextract', str(mkv_file)]):
                    result = subextract.main()

                    assert result == 1

    def test_main_directory_with_files(self, temp_dir):
        """Test main function with directory containing MKV files."""
        # Create multiple MKV files
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (3, 0, 0)

                with patch('sys.argv', ['subextract', str(temp_dir)]):
                    result = subextract.main()

                    mock_processor.process_files.assert_called_once()
                    assert result == 0

    def test_main_directory_with_failures(self, temp_dir):
        """Test main function with directory processing failures."""
        # Create MKV files
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (2, 1, 0)  # 1 failed

                with patch('sys.argv', ['subextract', str(temp_dir)]):
                    result = subextract.main()

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
                    result = subextract.main()

                    # No MKV files should return 0
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
                with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                    mock_processor = mock_processor_class.return_value
                    mock_processor.process_files.return_value = (2, 0, 0)

                    with patch('sys.argv', ['subextract']):
                        result = subextract.main()

                        mock_processor.process_files.assert_called_once()
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
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (4, 0, 0)

                with patch('sys.argv', ['subextract', str(temp_dir), '--parallel', '4']):
                    result = subextract.main()

                    mock_processor.process_files.assert_called_once()
                    call_args = mock_processor.process_files.call_args
                    assert call_args[0][2] == 4  # max_workers
                    assert result == 0

    def test_main_directory_no_mkv_files(self, temp_dir):
        """Test main function with directory containing no MKV files."""
        # Create non-MKV files
        (temp_dir / "movie.mp4").write_bytes(b"video content")
        (temp_dir / "movie.srt").write_bytes(b"subtitle content")

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(temp_dir)]):
                result = subextract.main()

                # No MKV files should return 0
                assert result == 0

    def test_main_invalid_parallel_value(self, temp_dir):
        """Test main function with invalid parallel worker count."""
        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', '--parallel', '0']):
                result = subextract.main()

                assert result == 1

    def test_main_negative_parallel_value(self, temp_dir):
        """Test main function with negative parallel worker count."""
        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', '--parallel', '-5']):
                result = subextract.main()

                assert result == 1

    def test_main_non_mkv_file(self, temp_dir):
        """Test main function with non-MKV file."""
        txt_file = temp_dir / "document.txt"
        txt_file.write_text("not an mkv file")

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(txt_file)]):
                result = subextract.main()

                assert result == 1

    def test_main_nonexistent_path(self, temp_dir):
        """Test main function with non-existent path."""
        non_existent = temp_dir / "nonexistent"

        with patch('subextract.need'):
            with patch('sys.argv', ['subextract', str(non_existent)]):
                result = subextract.main()

                assert result == 1

    def test_main_custom_argv(self, temp_dir):
        """Test main function with custom argv argument."""
        mkv_file = temp_dir / "custom.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subextract.need'):
            with patch('subextract.SubtitleExtractProcessor') as mock_processor_class:
                mock_processor = mock_processor_class.return_value
                mock_processor.process_files.return_value = (1, 0, 0)

                # Pass custom argv without program name (main() expects just arguments)
                result = subextract.main([str(mkv_file)])

                mock_processor.process_files.assert_called_once()
                assert result == 0
