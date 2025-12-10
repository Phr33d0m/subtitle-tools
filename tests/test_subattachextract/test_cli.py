"""
CLI tests for subattachextract argument parsing and main function.

Tests command-line interface behavior including path handling,
dry-run mode, verbose/quiet options, and parallel processing.
"""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import subattachextract


class TestArgumentParsing:
    """Test command-line argument parsing (handled in main function)."""

    def test_main_function_argument_parsing_defaults(self, temp_dir):
        """Test main function with default argument values."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]

            # Create a proper stats object instead of Mock
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify default arguments were used
                    mock_extractor_class.assert_called_once_with(
                        dry_run=False,
                        verbose=True,
                        max_workers=4
                    )

    def test_main_function_argument_parsing_dry_run(self, temp_dir):
        """Test main function with dry-run argument."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--dry-run', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify dry-run argument was parsed
                    mock_extractor_class.assert_called_once_with(
                        dry_run=True,
                        verbose=True,
                        max_workers=4
                    )

    def test_main_function_argument_parsing_quiet(self, temp_dir):
        """Test main function with quiet argument."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--quiet', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify quiet argument was parsed (verbose=False)
                    mock_extractor_class.assert_called_once_with(
                        dry_run=False,
                        verbose=False,
                        max_workers=4
                    )

    def test_main_function_argument_parsing_parallel(self, temp_dir):
        """Test main function with parallel argument."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--parallel', '8', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify parallel argument was parsed
                    mock_extractor_class.assert_called_once_with(
                        dry_run=False,
                        verbose=True,
                        max_workers=8
                    )

    def test_main_function_all_arguments(self, temp_dir):
        """Test main function with all arguments combined."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--dry-run', '--quiet', '--parallel', '6', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify all arguments were parsed correctly
                    mock_extractor_class.assert_called_once_with(
                        dry_run=True,
                        verbose=False,
                        max_workers=6
                    )

    def test_main_function_help(self):
        """Test help message display."""
        with patch('sys.argv', ['subattachextract', '--help']):
            with pytest.raises(SystemExit):
                subattachextract.main()


class TestMainFunction:
    """Test main CLI function."""

    def test_main_single_file_success(self, temp_dir):
        """Test main function with single MKV file."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', str(mkv_file)]):
                with patch('builtins.print'):
                    with patch('time.time', side_effect=[0, 1.5]):  # Mock timing
                        subattachextract.main()

                        # Verify extractor was created with correct parameters
                        mock_extractor_class.assert_called_once_with(
                            dry_run=False,
                            verbose=True,
                            max_workers=4
                        )

                        # Verify dependencies were checked
                        mock_extractor.check_dependencies.assert_called_once()

                        # Verify files were found and processed
                        mock_extractor.find_mkv_files.assert_called_once()
                        mock_extractor.process_files.assert_called_once()

                        # Verify stats were printed
                        mock_extractor.print_stats.assert_called_once()

    def test_main_directory_processing(self, temp_dir):
        """Test main function with directory containing MKV files."""
        # Create multiple MKV files
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [
                temp_dir / "movie0.mkv",
                temp_dir / "movie1.mkv",
                temp_dir / "movie2.mkv"
            ]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=3)

            with patch('sys.argv', ['subattachextract', str(temp_dir)]):
                with patch('builtins.print'):
                    with patch('time.time', side_effect=[0, 2.0]):
                        subattachextract.main()

                        # Verify correct output directory was used
                        process_files_call = mock_extractor.process_files.call_args[0]
                        assert process_files_call[1] == temp_dir  # outroot should be the input directory

    def test_main_dry_run_mode(self, temp_dir):
        """Test main function in dry-run mode."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--dry-run', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify extractor was created with dry_run=True
                    mock_extractor_class.assert_called_once_with(
                        dry_run=True,
                        verbose=True,
                        max_workers=4
                    )

                    # Verify dry-run message was printed
                    mock_extractor.log.assert_any_call(
                        "DRY RUN MODE - No files will be extracted", force=True
                    )

    def test_main_quiet_mode(self, temp_dir):
        """Test main function in quiet mode."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--quiet', str(mkv_file)]):
                with patch('builtins.print'):
                    with patch('time.time', side_effect=[0, 1.0]):
                        subattachextract.main()

                        # Verify extractor was created with verbose=False
                        mock_extractor_class.assert_called_once_with(
                            dry_run=False,
                            verbose=False,
                            max_workers=4
                        )

    def test_main_custom_parallel_workers(self, temp_dir):
        """Test main function with custom parallel worker count."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--parallel', '8', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Verify extractor was created with custom worker count
                    mock_extractor_class.assert_called_once_with(
                        dry_run=False,
                        verbose=True,
                        max_workers=8
                    )

    def test_main_no_mkv_files_found(self, temp_dir):
        """Test main function when no MKV files are found."""
        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = []
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=0)

            with patch('sys.argv', ['subattachextract', str(temp_dir)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Should always log "Done." at the end
                    mock_extractor.log.assert_any_call("Done.", force=True)

                    # Should print stats (even when no files processed)
                    mock_extractor.print_stats.assert_called_once()

                    # process_files should be called with empty list
                    mock_extractor.process_files.assert_called_once_with([], temp_dir)

    def test_main_default_current_directory(self, temp_dir):
        """Test main function when no path is specified (uses current directory)."""
        # Change to temp_dir for testing
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)

            # Create MKV file in temp_dir
            mkv_file = Path("test.mkv")
            mkv_file.write_bytes(b"mkv content")

            with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
                mock_extractor = Mock()
                mock_extractor_class.return_value = mock_extractor
                mock_extractor.find_mkv_files.return_value = [mkv_file]
                mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

                with patch('sys.argv', ['subattachextract']):
                    with patch('builtins.print'):
                        subattachextract.main()

                        # Should find files in current directory
                        mock_extractor.find_mkv_files.assert_called_once_with(Path('.'))

        finally:
            os.chdir(original_cwd)

    def test_main_timing_display(self, temp_dir):
        """Test main function displays processing time."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=2)

            with patch('sys.argv', ['subattachextract', str(mkv_file)]):
                with patch('builtins.print'):
                    # Mock timing: start=0, end=3.5 seconds
                    with patch('time.time', side_effect=[0, 3.5]):
                        subattachextract.main()

                        # Should display completion time
                        mock_extractor.log.assert_any_call(
                            "Completed in 3.50 seconds", force=True
                        )

    def test_main_dependency_check_failure(self, temp_dir):
        """Test main function when dependency check fails."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.check_dependencies.side_effect = SystemExit(1)

            with patch('sys.argv', ['subattachextract', str(mkv_file)]):
                with pytest.raises(SystemExit) as exc_info:
                    subattachextract.main()

                assert exc_info.value.code == 1

    def test_main_error_handling_during_processing(self, temp_dir):
        """Test main function handles errors during processing gracefully."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            # Mock process_files to raise exception internally but handle it gracefully
            def mock_process_files_with_error(paths, outroot):
                # Simulate the exception handling in process_files
                mock_extractor.log("Error processing test.mkv: Processing error", force=True)
                mock_extractor.stats.errors += 1

            mock_extractor.process_files.side_effect = mock_process_files_with_error
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=0)

            with patch('sys.argv', ['subattachextract', str(mkv_file)]):
                with patch('builtins.print'):
                    subattachextract.main()

                    # Should still print stats even after error
                    mock_extractor.print_stats.assert_called_once()

    def test_main_all_flags_combined(self, temp_dir):
        """Test main function with all command-line flags combined."""
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        with patch('subattachextract.AttachmentExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            mock_extractor.find_mkv_files.return_value = [mkv_file]
            mock_extractor.stats = subattachextract.ExtractionStats(files_processed=1)

            with patch('sys.argv', ['subattachextract', '--dry-run', '--quiet', '--parallel', '6', str(mkv_file)]):
                with patch('builtins.print'):
                    with patch('time.time', side_effect=[0, 0.5]):
                        subattachextract.main()

                        # Verify all flags were passed correctly
                        mock_extractor_class.assert_called_once_with(
                            dry_run=True,
                            verbose=False,
                            max_workers=6
                        )

                        # Verify dry-run message was still printed even in quiet mode (force=True)
                        mock_extractor.log.assert_any_call(
                            "DRY RUN MODE - No files will be extracted", force=True
                        )