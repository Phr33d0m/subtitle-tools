"""
Integration tests for sub_attachment_extract.

Tests end-to-end processing workflows, parallel execution,
file handling, and complex extraction scenarios.
"""

import time
from unittest.mock import patch
from tests.test_subattachextract.conftest import sub_attachment_extract


class TestProcessingWorkflows:
    """Test complete attachment processing workflows."""

    def test_process_attachments_for_file_success(self, temp_dir):
        """Test successful attachment processing for a single MKV file."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        # Mock successful attachment identification and extraction
        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000),
            sub_attachment_extract.Attachment(2, "cover.jpg", "image/jpeg", 5000)
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Verify stats were updated
                assert extractor.stats.files_processed == 1
                assert extractor.stats.attachments_found == 2
                assert extractor.stats.attachments_extracted == 2
                assert extractor.stats.attachments_skipped == 0

                # Verify files were remembered
                assert "font.ttf" in extractor.existing_files
                assert "cover.jpg" in extractor.existing_files

    def test_process_attachments_for_file_no_attachments(self, temp_dir):
        """Test processing file with no attachments."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        with patch.object(extractor, 'get_mkv_attachments', return_value=[]):
            extractor.process_attachments_for_file(mkv_file, outroot)

            # Should increment files processed but no attachments
            assert extractor.stats.files_processed == 1
            assert extractor.stats.attachments_found == 0
            assert extractor.stats.attachments_extracted == 0

    def test_process_attachments_for_file_skipping_existing(self, temp_dir):
        """Test processing with existing filename skipping."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        # Pre-populate existing files set
        extractor.existing_files.add("font.ttf")

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000),  # Should be skipped
            sub_attachment_extract.Attachment(2, "cover.jpg", "image/jpeg", 5000)  # Should be processed
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # One skipped, one extracted
                assert extractor.stats.attachments_found == 2
                assert extractor.stats.attachments_extracted == 1
                assert extractor.stats.attachments_skipped == 1

    def test_process_attachments_for_file_extraction_failure(self, temp_dir):
        """Test processing with extraction failures."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000)
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=False):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Should be counted as skipped
                assert extractor.stats.attachments_found == 1
                assert extractor.stats.attachments_extracted == 0
                assert extractor.stats.attachments_skipped == 1

    def test_process_attachments_for_file_race_condition(self, temp_dir):
        """Test handling race condition when file exists during processing."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000)
        ]
        dest_path = outroot / "Fonts" / "font.ttf"

        # Simulate race condition: file already exists before processing
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("existing")

        def mock_extract(mkv_file, attachment, dest_path):
            # This should not be called due to race condition check
            return True

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', side_effect=mock_extract):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Should be skipped due to race condition
                assert extractor.stats.attachments_found == 1
                assert extractor.stats.attachments_extracted == 0
                assert extractor.stats.attachments_skipped == 1

    def test_process_attachments_for_file_invalid_file(self, temp_dir):
        """Test processing non-existent or empty file."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "nonexistent.mkv"
        outroot = temp_dir / "output"

        extractor.process_attachments_for_file(mkv_file, outroot)

        # Should count as error, but files_processed is 0 because file was never actually processed
        assert extractor.stats.files_processed == 0
        assert extractor.stats.errors == 1

    def test_process_attachments_for_file_empty_file(self, temp_dir):
        """Test processing empty file."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "empty.mkv"
        mkv_file.write_bytes(b"")  # Empty file
        outroot = temp_dir / "output"

        extractor.process_attachments_for_file(mkv_file, outroot)

        # Should count as error, but files_processed is 0 because file was never actually processed
        assert extractor.stats.files_processed == 0
        assert extractor.stats.errors == 1

    def test_process_files_single_file(self, temp_dir):
        """Test processing a single file."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'process_attachments_for_file'):
                extractor.process_files([mkv_file], outroot)

                # Should build existing files set first
                extractor.build_existing_name_set.assert_called_once_with(outroot)
                extractor.process_attachments_for_file.assert_called_once_with(mkv_file, outroot)

    def test_process_files_no_files(self, temp_dir):
        """Test processing with no files."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        outroot = temp_dir / "output"

        with patch.object(extractor, 'log') as mock_log:
            extractor.process_files([], outroot)

            mock_log.assert_called_once_with("No .mkv files found.", force=True)

    def test_process_files_parallel_execution(self, temp_dir):
        """Test parallel processing of multiple files."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False, max_workers=2)

        # Create multiple MKV files
        mkv_files = []
        for i in range(3):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")
            mkv_files.append(mkv_file)

        outroot = temp_dir / "output"

        # Mock the method and manually increment stats to avoid recursion
        call_count = 0
        def mock_process(mkv_file, outroot):
            nonlocal call_count
            call_count += 1
            # Simulate the real method's stats incrementing
            extractor.stats.files_processed += 1

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'process_attachments_for_file', side_effect=mock_process):
                extractor.process_files(mkv_files, outroot)

                # All files should be processed
                assert call_count == 3
                assert extractor.stats.files_processed == 3

    def test_process_files_with_progress_display(self, temp_dir):
        """Test progress display during parallel processing."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=True, max_workers=2)

        # Create multiple files
        mkv_files = []
        for i in range(2):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")
            mkv_files.append(mkv_file)

        outroot = temp_dir / "output"

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'process_attachments_for_file'):
                with patch('builtins.print') as mock_print:
                    extractor.process_files(mkv_files, outroot)

                    # Should show progress for multiple files
                    progress_calls = [call for call in mock_print.call_args_list
                                    if "Progress:" in str(call)]
                    assert len(progress_calls) >= 1

    def test_process_files_with_errors(self, temp_dir):
        """Test error handling during parallel processing."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False, max_workers=2)

        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"

        def mock_process_with_error(mkv_file, outroot):
            if mkv_file.name == "movie.mkv":
                raise Exception("Processing error")

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'process_attachments_for_file',
                             side_effect=mock_process_with_error):
                with patch.object(extractor, 'log') as mock_log:
                    extractor.process_files([mkv_file], outroot)

                    # Should log the error
                    error_calls = [call for call in mock_log.call_args_list
                                  if "Error processing" in str(call)]
                    assert len(error_calls) >= 1

                    # Should increment error count
                    assert extractor.stats.errors == 1


class TestMimeAndCategoryHandling:
    """Test MIME type detection and categorization edge cases."""

    def test_process_various_mime_types(self, temp_dir):
        """Test processing files with various MIME types."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000),
            sub_attachment_extract.Attachment(2, "cover.jpg", "image/jpeg", 5000),
            sub_attachment_extract.Attachment(3, "data.bin", "application/octet-stream", 2000),
            sub_attachment_extract.Attachment(4, "script.js", "text/javascript", 1500)
        ]

        extracted_paths = []

        def mock_extract(mkv_file, attachment, dest_path):
            extracted_paths.append(dest_path)
            return True

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', side_effect=mock_extract):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Verify files were categorized correctly
                font_path = outroot / "Fonts" / "font.ttf"
                cover_path = outroot / "Covers" / "cover.jpg"
                data_path = outroot / "Others" / "data.bin"
                script_path = outroot / "Others" / "script.js"

                assert font_path in extracted_paths
                assert cover_path in extracted_paths
                assert data_path in extracted_paths
                assert script_path in extracted_paths

    def test_filename_based_categorization(self, temp_dir):
        """Test categorization based on filename when MIME is generic."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        attachments = [
            sub_attachment_extract.Attachment(1, "movie_font.ttf", "application/octet-stream", 1000),
            sub_attachment_extract.Attachment(2, "movie_cover.jpg", "application/octet-stream", 5000),
            sub_attachment_extract.Attachment(3, "cover.png", "application/octet-stream", 3000),
            sub_attachment_extract.Attachment(4, "poster.webp", "application/octet-stream", 4000)
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Should categorize based on filename patterns
                assert extractor.stats.attachments_found == 4
                assert extractor.stats.attachments_extracted == 4


class TestDryRunMode:
    """Test dry-run mode functionality."""

    def test_dry_run_mode_workflow(self, temp_dir):
        """Test complete dry-run workflow."""
        extractor = sub_attachment_extract.AttachmentExtractor(dry_run=True, verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000),
            sub_attachment_extract.Attachment(2, "cover.jpg", "image/jpeg", 5000)
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True) as mock_extract:
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Should report extractions but not actually create files
                assert extractor.stats.attachments_found == 2
                assert extractor.stats.attachments_extracted == 2
                assert extractor.stats.attachments_skipped == 0

                # extract_one_attachment should have been called
                assert mock_extract.call_count == 2

                # Verify no files were actually created
                assert not (outroot / "Fonts" / "font.ttf").exists()
                assert not (outroot / "Covers" / "cover.jpg").exists()

    def test_dry_run_with_existing_files(self, temp_dir):
        """Test dry-run mode with existing files."""
        extractor = sub_attachment_extract.AttachmentExtractor(dry_run=True, verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"

        # Pre-populate existing files
        extractor.existing_files.add("font.ttf")

        attachments = [
            sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000),  # Should be skipped
            sub_attachment_extract.Attachment(2, "cover.jpg", "image/jpeg", 5000)  # Should be "extracted"
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # One skipped, one "extracted" (in dry-run mode)
                assert extractor.stats.attachments_found == 2
                assert extractor.stats.attachments_extracted == 1
                assert extractor.stats.attachments_skipped == 1


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_mixed_attachment_types_single_file(self, temp_dir):
        """Test single MKV file with mixed attachment types."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        # Mix of fonts, covers, and other files
        attachments = [
            sub_attachment_extract.Attachment(1, "arial.ttf", "font/ttf", 1000),
            sub_attachment_extract.Attachment(2, "movie_cover.jpg", "image/jpeg", 5000),
            sub_attachment_extract.Attachment(3, "chapter_info.txt", "text/plain", 500),
            sub_attachment_extract.Attachment(4, "subtitle_font.woff", "font/woff", 2000),
            sub_attachment_extract.Attachment(5, "backdrop.png", "image/png", 8000),
            sub_attachment_extract.Attachment(6, "metadata.xml", "application/xml", 1500)
        ]

        # Simulate one extraction failure
        extraction_results = [True, True, True, False, True, True]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', side_effect=extraction_results):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Verify statistics
                assert extractor.stats.files_processed == 1
                assert extractor.stats.attachments_found == 6
                assert extractor.stats.attachments_extracted == 5  # One failed
                assert extractor.stats.attachments_skipped == 1

    def test_batch_processing_multiple_files(self, temp_dir):
        """Test processing multiple MKV files in batch."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False, max_workers=3)
        outroot = temp_dir / "output"

        # Create multiple MKV files with different attachment counts
        mkv_files = []
        for i in range(4):
            mkv_file = temp_dir / f"movie{i}.mkv"
            mkv_file.write_bytes(b"mkv content")
            mkv_files.append(mkv_file)

        # Different attachment counts for each file
        attachment_counts = [2, 0, 3, 1]  # File 1 has 2, File 2 has 0, etc.

        def mock_get_attachments(mkv_file):
            file_index = int(mkv_file.stem[-1])  # Extract number from filename
            count = attachment_counts[file_index]
            # Use unique filenames to avoid conflicts between files
            return [sub_attachment_extract.Attachment(j, f"file{file_index}_att{j}.bin", "application/octet-stream")
                   for j in range(count)]

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'get_mkv_attachments', side_effect=mock_get_attachments):
                with patch.object(extractor, 'extract_one_attachment', return_value=True):
                    extractor.process_files(mkv_files, outroot)

                    # Total attachments: 2 + 0 + 3 + 1 = 6
                    assert extractor.stats.files_processed == 4
                    assert extractor.stats.attachments_found == 6
                    assert extractor.stats.attachments_extracted == 6

    def test_large_scale_processing(self, temp_dir):
        """Test processing many files to test performance and robustness."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False, max_workers=4)
        outroot = temp_dir / "output"

        # Create 10 MKV files
        mkv_files = []
        for i in range(10):
            mkv_file = temp_dir / f"movie{i:02d}.mkv"
            mkv_file.write_bytes(b"mkv content")
            mkv_files.append(mkv_file)

        # Each file has 2 attachments with unique filenames to avoid conflicts
        def mock_get_attachments(mkv_file):
            file_index = int(mkv_file.stem[-2:])  # Extract number from filename
            return [sub_attachment_extract.Attachment(1, f"font_{file_index}.ttf", "font/ttf"),
                   sub_attachment_extract.Attachment(2, f"cover_{file_index}.jpg", "image/jpeg")]

        with patch.object(extractor, 'build_existing_name_set'):
            with patch.object(extractor, 'get_mkv_attachments', side_effect=mock_get_attachments):
                with patch.object(extractor, 'extract_one_attachment', return_value=True):
                    start_time = time.time()
                    extractor.process_files(mkv_files, outroot)
                    elapsed = time.time() - start_time

                    # Verify all files processed
                    assert extractor.stats.files_processed == 10
                    assert extractor.stats.attachments_found == 20
                    assert extractor.stats.attachments_extracted == 20

                    # Should complete reasonably quickly (mock processing)
                    assert elapsed < 2.0

    def test_unicode_and_special_filenames(self, temp_dir):
        """Test handling of unicode and special characters in filenames."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")
        outroot = temp_dir / "output"
        outroot.mkdir()

        attachments = [
            sub_attachment_extract.Attachment(1, "café.ttf", "font/ttf", 1000),
            sub_attachment_extract.Attachment(2, "movie_cover.jpg", "image/jpeg", 5000),
            sub_attachment_extract.Attachment(3, "привет.ttf", "font/ttf", 2000),
            sub_attachment_extract.Attachment(4, "file:with*special?chars.ttf", "font/ttf", 1500)
        ]

        with patch.object(extractor, 'get_mkv_attachments', return_value=attachments):
            with patch.object(extractor, 'extract_one_attachment', return_value=True):
                extractor.process_attachments_for_file(mkv_file, outroot)

                # Should process all attachments
                assert extractor.stats.attachments_found == 4
                assert extractor.stats.attachments_extracted == 4

                # Verify all original filenames are remembered (remember_existing doesn't sanitize)
                assert "café.ttf" in extractor.existing_files
                assert "movie_cover.jpg" in extractor.existing_files
                assert "привет.ttf" in extractor.existing_files
                assert "file:with*special?chars.ttf" in extractor.existing_files