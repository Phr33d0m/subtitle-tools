"""
Core functionality tests for sub_attachment_extract.

Tests attachment extraction from MKV files, MIME type categorization,
filename sanitization, and batch processing with parallel execution.
"""

import pytest
import json
import subprocess
from unittest.mock import patch
from pathlib import Path
from tests.test_subattachextract.conftest import sub_attachment_extract


class TestAttachment:
    """Test Attachment dataclass."""

    def test_attachment_creation_minimal(self):
        """Test creating Attachment with minimal required fields."""
        attachment = sub_attachment_extract.Attachment(
            id=1,
            filename="font.ttf",
            mime_type="font/ttf"
        )

        assert attachment.id == 1
        assert attachment.filename == "font.ttf"
        assert attachment.mime_type == "font/ttf"
        assert attachment.size is None

    def test_attachment_creation_with_size(self):
        """Test creating Attachment with all fields including size."""
        attachment = sub_attachment_extract.Attachment(
            id=2,
            filename="cover.jpg",
            mime_type="image/jpeg",
            size=123456
        )

        assert attachment.id == 2
        assert attachment.filename == "cover.jpg"
        assert attachment.mime_type == "image/jpeg"
        assert attachment.size == 123456

    def test_attachment_equality(self):
        """Test Attachment equality comparison."""
        att1 = sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000)
        att2 = sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf", 1000)
        att3 = sub_attachment_extract.Attachment(2, "font.ttf", "font/ttf", 1000)

        assert att1 == att2
        assert att1 != att3


class TestExtractionStats:
    """Test ExtractionStats dataclass."""

    def test_stats_default_values(self):
        """Test ExtractionStats with default values."""
        stats = sub_attachment_extract.ExtractionStats()

        assert stats.files_processed == 0
        assert stats.attachments_found == 0
        assert stats.attachments_extracted == 0
        assert stats.attachments_skipped == 0
        assert stats.errors == 0

    def test_stats_custom_values(self):
        """Test ExtractionStats with custom values."""
        stats = sub_attachment_extract.ExtractionStats(
            files_processed=5,
            attachments_found=15,
            attachments_extracted=10,
            attachments_skipped=3,
            errors=2
        )

        assert stats.files_processed == 5
        assert stats.attachments_found == 15
        assert stats.attachments_extracted == 10
        assert stats.attachments_skipped == 3
        assert stats.errors == 2


class TestAttachmentExtractor:
    """Test AttachmentExtractor class."""

    def test_extractor_initialization_defaults(self):
        """Test AttachmentExtractor initialization with default parameters."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert extractor.dry_run is False
        assert extractor.verbose is True
        assert extractor.max_workers == 4
        assert isinstance(extractor.stats, sub_attachment_extract.ExtractionStats)
        assert isinstance(extractor.existing_files, set)

    def test_extractor_initialization_custom_params(self):
        """Test AttachmentExtractor initialization with custom parameters."""
        custom_stats = sub_attachment_extract.ExtractionStats(files_processed=1)
        extractor = sub_attachment_extract.AttachmentExtractor(
            dry_run=True,
            verbose=False,
            max_workers=8,
            stats=custom_stats
        )

        assert extractor.dry_run is True
        assert extractor.verbose is False
        assert extractor.max_workers == 8
        assert extractor.stats is custom_stats
        assert extractor.stats.files_processed == 1

    def test_log_verbose_mode(self):
        """Test log method in verbose mode."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=True)

        with patch('builtins.print') as mock_print:
            extractor.log("Test message")
            mock_print.assert_called_once_with("Test message")

    def test_log_quiet_mode(self):
        """Test log method in quiet mode."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)

        with patch('builtins.print') as mock_print:
            extractor.log("Test message")
            mock_print.assert_not_called()

    def test_log_force_override(self):
        """Test log method with force=True override."""
        extractor = sub_attachment_extract.AttachmentExtractor(verbose=False)

        with patch('builtins.print') as mock_print:
            extractor.log("Test message", force=True)
            mock_print.assert_called_once_with("Test message")

    def test_check_dependencies_success(self):
        """Test successful dependency checking."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0

            # Should not raise any exception
            extractor.check_dependencies()

            # Should check both tools
            assert mock_run.call_count == 2
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert ['mkvmerge', '--version'] in calls
            assert ['mkvextract', '--version'] in calls

    def test_check_dependencies_tool_not_found(self):
        """Test dependency checking when tool is not found."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    extractor.check_dependencies()

                assert exc_info.value.code == 1
                # Should print error message
                mock_print.assert_called()

    def test_check_dependencies_command_fails(self):
        """Test dependency checking when command returns non-zero exit."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'mkvmerge')

            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    extractor.check_dependencies()

                assert exc_info.value.code == 1

    def test_category_for_fonts(self):
        """Test MIME type categorization for fonts."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Test font MIME types
        assert extractor.category_for("font/ttf", "font.ttf") == "Fonts"
        assert extractor.category_for("font/otf", "font.otf") == "Fonts"
        assert extractor.category_for("application/vnd.ms-opentype", "font.ttf") == "Fonts"
        assert extractor.category_for("application/x-font-otf", "font.otf") == "Fonts"

        # Test font file extensions
        assert extractor.category_for("application/octet-stream", "font.ttf") == "Fonts"
        assert extractor.category_for("application/octet-stream", "font.otf") == "Fonts"
        assert extractor.category_for("application/octet-stream", "font.ttc") == "Fonts"
        assert extractor.category_for("application/octet-stream", "font.woff") == "Fonts"
        assert extractor.category_for("application/octet-stream", "font.woff2") == "Fonts"

    def test_category_for_images(self):
        """Test MIME type categorization for images."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Test image MIME types
        assert extractor.category_for("image/jpeg", "cover.jpg") == "Covers"
        assert extractor.category_for("image/png", "poster.png") == "Covers"
        assert extractor.category_for("image/webp", "image.webp") == "Covers"

        # Test image file extensions
        assert extractor.category_for("application/octet-stream", "cover.jpg") == "Covers"
        assert extractor.category_for("application/octet-stream", "poster.jpeg") == "Covers"
        assert extractor.category_for("application/octet-stream", "image.png") == "Covers"
        assert extractor.category_for("application/octet-stream", "banner.webp") == "Covers"
        assert extractor.category_for("application/octet-stream", "screenshot.bmp") == "Covers"

        # Test cover/poster keywords in filename
        assert extractor.category_for("application/octet-stream", "movie_cover.png") == "Covers"
        assert extractor.category_for("application/octet-stream", "series_poster.jpg") == "Covers"

    def test_category_for_others(self):
        """Test MIME type categorization for other files."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert extractor.category_for("application/octet-stream", "data.bin") == "Others"
        assert extractor.category_for("text/plain", "readme.txt") == "Others"
        assert extractor.category_for("application/zip", "archive.zip") == "Others"

    def test_category_for_case_insensitive(self):
        """Test MIME type categorization is case insensitive."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert extractor.category_for("FONT/TTF", "FONT.TTF") == "Fonts"
        assert extractor.category_for("IMAGE/JPEG", "COVER.JPG") == "Covers"
        assert extractor.category_for("Application/Octet-Stream", "FILE.TTF") == "Fonts"

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert extractor.sanitize_filename("normal.ttf") == "normal.ttf"
        assert extractor.sanitize_filename("font with spaces.ttf") == "font with spaces.ttf"

    def test_sanitize_filename_problematic_chars(self):
        """Test filename sanitization with problematic characters."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Test character replacements (note: os.path.basename strips path components first)
        assert extractor.sanitize_filename("file/name.ttf") == "name.ttf"

        # On Unix, backslashes are not path separators, so they get replaced with underscores
        import os
        if os.name == 'nt':  # Windows
            assert extractor.sanitize_filename("file\\name.ttf") == "name.ttf"
        else:  # Unix/Linux/macOS
            assert extractor.sanitize_filename("file\\name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file:name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file*name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file?name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename('file"name.ttf') == "file_name.ttf"
        assert extractor.sanitize_filename("file<name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file>name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file|name.ttf") == "file_name.ttf"

        # Test with filenames that have problematic chars but no path
        assert extractor.sanitize_filename("file:name.ttf") == "file_name.ttf"
        assert extractor.sanitize_filename("file*name.ttf") == "file_name.ttf"

    def test_sanitize_filename_long_name(self):
        """Test filename sanitization with long names."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Create a very long filename
        long_name = "a" * 300 + ".ttf"
        sanitized = extractor.sanitize_filename(long_name)

        # Should be truncated to 255 characters max
        assert len(sanitized) <= 255
        assert sanitized.endswith(".ttf")

    def test_sanitize_filename_path_components(self):
        """Test filename sanitization removes path components."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert extractor.sanitize_filename("path/to/font.ttf") == "font.ttf"
        assert extractor.sanitize_filename("/absolute/path/font.ttf") == "font.ttf"

        # On Unix, backslashes are not path separators, so they get replaced with underscores
        import os
        if os.name == 'nt':  # Windows
            assert extractor.sanitize_filename("relative\\path\\font.ttf") == "font.ttf"
        else:  # Unix/Linux/macOS
            assert extractor.sanitize_filename("relative\\path\\font.ttf") == "relative_path_font.ttf"

    def test_build_existing_name_set(self, temp_dir):
        """Test building existing filename set from directories."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Create test directory structure
        covers_dir = temp_dir / "Covers"
        fonts_dir = temp_dir / "Fonts"
        others_dir = temp_dir / "Others"

        covers_dir.mkdir()
        fonts_dir.mkdir()
        others_dir.mkdir()

        # Create test files
        (covers_dir / "cover1.jpg").write_text("cover")
        (covers_dir / "poster.png").write_text("poster")
        (fonts_dir / "font1.ttf").write_text("font")
        (others_dir / "data.bin").write_text("data")

        # Create subdirectory (should be ignored)
        (covers_dir / "subdir").mkdir()

        extractor.build_existing_name_set(temp_dir)

        # Should have collected all file names
        assert "cover1.jpg" in extractor.existing_files
        assert "poster.png" in extractor.existing_files
        assert "font1.ttf" in extractor.existing_files
        assert "data.bin" in extractor.existing_files
        assert len(extractor.existing_files) == 4

    def test_build_existing_name_set_missing_dirs(self, temp_dir):
        """Test building existing name set when directories don't exist."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Don't create any directories
        extractor.build_existing_name_set(temp_dir)

        # Should not error and should have empty set
        assert len(extractor.existing_files) == 0

    def test_remember_existing(self):
        """Test remembering existing filenames."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        assert "test.ttf" not in extractor.existing_files
        extractor.remember_existing("test.ttf")
        assert "test.ttf" in extractor.existing_files

    def test_get_mkv_attachments_success(self, temp_dir):
        """Test successful attachment identification from MKV."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "attachments": [
                {
                    "id": 1,
                    "file_name": "font.ttf",
                    "content_type": "font/ttf",
                    "size": 12345
                },
                {
                    "id": 2,
                    "file_name": "cover.jpg",
                    "content_type": "image/jpeg",
                    "size": 67890
                }
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            attachments = extractor.get_mkv_attachments(mkv_file)

            assert len(attachments) == 2

            # Check first attachment
            assert attachments[0].id == 1
            assert attachments[0].filename == "font.ttf"
            assert attachments[0].mime_type == "font/ttf"
            assert attachments[0].size == 12345

            # Check second attachment
            assert attachments[1].id == 2
            assert attachments[1].filename == "cover.jpg"
            assert attachments[1].mime_type == "image/jpeg"
            assert attachments[1].size == 67890

    def test_get_mkv_attachments_no_attachments(self, temp_dir):
        """Test attachment identification when no attachments present."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "attachments": []
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            attachments = extractor.get_mkv_attachments(mkv_file)

            assert len(attachments) == 0

    def test_get_mkv_attachments_missing_filename(self, temp_dir):
        """Test attachment identification with missing filename."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "attachments": [
                {
                    "id": 1,
                    "content_type": "font/ttf"
                    # Missing file_name
                }
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            attachments = extractor.get_mkv_attachments(mkv_file)

            assert len(attachments) == 1
            assert attachments[0].id == 1
            assert attachments[0].filename == "attachment-1"  # Default name

    def test_get_mkv_attachments_subprocess_failure(self, temp_dir):
        """Test attachment identification when subprocess fails."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'mkvmerge')

            with patch('builtins.print') as mock_print:
                attachments = extractor.get_mkv_attachments(mkv_file)

                assert len(attachments) == 0
                # Should log warning
                mock_print.assert_called()

    def test_get_mkv_attachments_json_error(self, temp_dir):
        """Test attachment identification with invalid JSON."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "invalid json"

            with patch('builtins.print') as mock_print:
                attachments = extractor.get_mkv_attachments(mkv_file)

                assert len(attachments) == 0
                # Should log warning
                mock_print.assert_called()

    def test_extract_one_attachment_dry_run(self, temp_dir):
        """Test single attachment extraction in dry-run mode."""
        extractor = sub_attachment_extract.AttachmentExtractor(dry_run=True)
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        attachment = sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf")
        dest_path = temp_dir / "font.ttf"

        result = extractor.extract_one_attachment(mkv_file, attachment, dest_path)

        assert result is True  # Dry-run always succeeds
        assert not dest_path.exists()  # No file should be created

    def test_extract_one_attachment_success(self, temp_dir):
        """Test successful single attachment extraction."""
        extractor = sub_attachment_extract.AttachmentExtractor(dry_run=False)
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        attachment = sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf")
        dest_path = temp_dir / "font.ttf"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            # Mock that the file was created
            with open(dest_path, 'w') as f:
                f.write("font content")

            result = extractor.extract_one_attachment(mkv_file, attachment, dest_path)

            assert result is True
            assert dest_path.exists()

            # Verify mkvextract was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'mkvextract'
            assert call_args[1] == 'attachments'
            assert str(mkv_file) in call_args
            assert f"1:{dest_path}" in call_args

    def test_extract_one_attachment_failure(self, temp_dir):
        """Test failed single attachment extraction."""
        extractor = sub_attachment_extract.AttachmentExtractor(dry_run=False)
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        attachment = sub_attachment_extract.Attachment(1, "font.ttf", "font/ttf")
        dest_path = temp_dir / "font.ttf"

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'mkvextract')

            result = extractor.extract_one_attachment(mkv_file, attachment, dest_path)

            assert result is False
            assert not dest_path.exists()

    def test_find_mkv_files_single_file(self, temp_dir):
        """Test finding MKV files when path is a single file."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        mkv_file = temp_dir / "movie.mkv"
        mkv_file.write_bytes(b"mkv content")

        files = extractor.find_mkv_files(mkv_file)

        assert len(files) == 1
        assert files[0] == mkv_file

    def test_find_mkv_files_non_mkv_file(self, temp_dir):
        """Test finding MKV files when path is non-MKV file."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        txt_file = temp_dir / "movie.txt"
        txt_file.write_text("not mkv")

        files = extractor.find_mkv_files(txt_file)

        assert len(files) == 0

    def test_find_mkv_files_directory(self, temp_dir):
        """Test finding MKV files in directory."""
        extractor = sub_attachment_extract.AttachmentExtractor()

        # Create test files
        (temp_dir / "movie1.mkv").write_bytes(b"mkv1")
        (temp_dir / "movie2.MKV").write_bytes(b"mkv2")
        (temp_dir / "movie3.mp4").write_bytes(b"mp4")
        (temp_dir / "subtitle.srt").write_text("subtitle")

        files = extractor.find_mkv_files(temp_dir)

        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "movie1.mkv" in file_names
        assert "movie2.MKV" in file_names

    def test_find_mkv_files_nonexistent_path(self):
        """Test finding MKV files with non-existent path."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        nonexistent = Path("/nonexistent/path")

        files = extractor.find_mkv_files(nonexistent)

        assert len(files) == 0

    def test_print_stats(self):
        """Test statistics printing."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        extractor.stats.files_processed = 5
        extractor.stats.attachments_found = 15
        extractor.stats.attachments_extracted = 10
        extractor.stats.attachments_skipped = 3
        extractor.stats.errors = 2

        with patch('builtins.print') as mock_print:
            extractor.print_stats()

            # Should print summary with separator lines
            assert mock_print.call_count >= 7  # Separator + header + 5 stats + separator
            calls = [str(call[0][0]) for call in mock_print.call_args_list]
            assert any("Extraction Summary:" in call for call in calls)
            assert any("Files processed: 5" in call for call in calls)
            assert any("Attachments found: 15" in call for call in calls)
            assert any("Attachments extracted: 10" in call for call in calls)
            assert any("Attachments skipped: 3" in call for call in calls)
            assert any("Errors encountered: 2" in call for call in calls)

    def test_print_stats_no_errors(self):
        """Test statistics printing when no errors."""
        extractor = sub_attachment_extract.AttachmentExtractor()
        extractor.stats.files_processed = 3
        extractor.stats.attachments_found = 6
        extractor.stats.attachments_extracted = 5
        extractor.stats.attachments_skipped = 1
        extractor.stats.errors = 0

        with patch('builtins.print') as mock_print:
            extractor.print_stats()

            calls = [str(call[0][0]) for call in mock_print.call_args_list]
            # Should not include errors line when no errors
            assert not any("Errors encountered" in call for call in calls)