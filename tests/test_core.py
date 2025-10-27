"""
Core function tests for submerge.

Tests core functionality including file discovery, subtitle matching,
and font collection without involving external dependencies.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock
import submerge


class TestVideoFileDiscovery:
    """Test video file discovery functionality."""

    def test_find_video_files_non_recursive(self, temp_dir):
        """Test finding video files without recursion."""
        # Create test video files
        (temp_dir / "video1.mkv").write_text("dummy video")
        (temp_dir / "video2.mp4").write_text("dummy video")
        (temp_dir / "subtitle1.srt").write_text("dummy subtitle")
        (temp_dir / "not_video.txt").write_text("dummy text")

        video_files = submerge.find_video_files(temp_dir, recursive=False)

        assert len(video_files) == 2
        assert video_files[0].name in ["video1.mkv", "video2.mp4"]
        assert video_files[1].name in ["video1.mkv", "video2.mp4"]
        assert all(video.suffix in submerge.DEFAULT_VIDEO_EXTENSIONS for video in video_files)

    def test_find_video_files_recursive(self, temp_dir):
        """Test finding video files with recursion."""
        # Create directory structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()

        (temp_dir / "video1.mkv").write_text("dummy video")
        (subdir / "video2.mp4").write_text("dummy video")
        (subdir / "subtitle.srt").write_text("dummy subtitle")

        video_files = submerge.find_video_files(temp_dir, recursive=True)

        assert len(video_files) == 2
        video_names = [v.name for v in video_files]
        assert "video1.mkv" in video_names
        assert "video2.mp4" in video_names

    def test_find_video_files_empty_directory(self, temp_dir):
        """Test finding video files in empty directory."""
        video_files = submerge.find_video_files(temp_dir, recursive=False)
        assert video_files == []

    def test_find_video_files_case_insensitive(self, temp_dir):
        """Test video file discovery is case insensitive."""
        (temp_dir / "video1.MKV").write_text("dummy video")
        (temp_dir / "video2.MP4").write_text("dummy video")

        video_files = submerge.find_video_files(temp_dir, recursive=False)

        assert len(video_files) == 2
        assert video_files[0].suffix in [".MKV", ".MP4"]
        assert video_files[1].suffix in [".MKV", ".MP4"]

    def test_find_video_files_supported_extensions(self, temp_dir):
        """Test that only supported video extensions are found."""
        supported_files = ["video.mkv", "movie.mp4", "clip.webm"]
        unsupported_files = ["video.avi", "movie.mov", "clip.flv"]

        for filename in supported_files:
            (temp_dir / filename).write_text("dummy video")

        for filename in unsupported_files:
            (temp_dir / filename).write_text("dummy video")

        video_files = submerge.find_video_files(temp_dir, recursive=False)

        assert len(video_files) == len(supported_files)
        for video_file in video_files:
            assert video_file.suffix.lower() in {".mkv", ".mp4", ".webm"}


class TestSubtitleFileDiscovery:
    """Test subtitle file discovery and matching."""

    def test_find_subtitle_files_basic_matching(self, temp_dir):
        """Test basic subtitle file matching."""
        video_path = temp_dir / "test_video.mkv"
        video_path.write_text("dummy video")

        # Create matching subtitle files
        (temp_dir / "test_video.eng.srt").write_text("English subtitle")
        (temp_dir / "test_video.fr.srt").write_text("French subtitle")
        (temp_dir / "test_video.ass").write_text("ASS subtitle")

        # Create non-matching files
        (temp_dir / "other_video.eng.srt").write_text("Other subtitle")
        (temp_dir / "test_video.txt").write_text("Not a subtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 3
        subtitle_names = [sub.path.name for sub in subtitle_files]
        assert "test_video.eng.srt" in subtitle_names
        assert "test_video.fr.srt" in subtitle_names
        assert "test_video.ass" in subtitle_names

    def test_find_subtitle_files_priority_ordering(self, temp_dir):
        """Test that ASS files have higher priority than SRT files."""
        video_path = temp_dir / "test_video.mkv"
        video_path.write_text("dummy video")

        (temp_dir / "test_video.eng.srt").write_text("SRT subtitle")
        (temp_dir / "test_video.eng.ass").write_text("ASS subtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 2
        # ASS file should come first due to higher priority
        assert subtitle_files[0].extension.lower() == ".ass"
        assert subtitle_files[1].extension.lower() == ".srt"

    def test_find_subtitle_files_no_matches(self, temp_dir):
        """Test when no matching subtitle files are found."""
        video_path = temp_dir / "test_video.mkv"
        video_path.write_text("dummy video")

        # Create non-matching files
        (temp_dir / "other_video.eng.srt").write_text("Other subtitle")
        (temp_dir / "test_video.txt").write_text("Not a subtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)
        assert subtitle_files == []

    def test_find_subtitle_files_complex_naming(self, temp_dir):
        """Test subtitle file discovery with complex naming patterns."""
        video_path = temp_dir / "The.Movie.2023.1080p.BluRay.x264.mkv"
        video_path.write_text("dummy video")

        # Create matching subtitle with complex naming
        subtitle_path = temp_dir / "The.Movie.2023.1080p.BluRay.x264.eng.srt"
        subtitle_path.write_text("English subtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].path == subtitle_path
        assert subtitle_files[0].language_code == "eng"

    def test_find_subtitle_files_special_characters(self, temp_dir):
        """Test subtitle file discovery with special characters."""
        video_path = temp_dir / "Movie [2023].mkv"
        video_path.write_text("dummy video")

        subtitle_path = temp_dir / "Movie [2023].eng.srt"
        subtitle_path.write_text("English subtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].path.name == "Movie [2023].eng.srt"

    def test_find_subtitle_files_swedish_mapping(self, temp_dir):
        """Test Swedish language code mapping in subtitle discovery."""
        video_path = temp_dir / "test_video.mkv"
        video_path.write_text("dummy video")

        subtitle_path = temp_dir / "test_video.se.srt"
        subtitle_path.write_text("Svensk text")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].language_code == "swe"  # Should be mapped

    def test_find_subtitle_files_multiple_same_language(self, temp_dir):
        """Test handling multiple subtitle files for same language."""
        video_path = temp_dir / "test_video.mkv"
        video_path.write_text("dummy video")

        (temp_dir / "test_video.eng.srt").write_text("English 1")
        (temp_dir / "test_video.eng.ass").write_text("English 2")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 2
        # Both should have same language code
        assert all(sub.language_code == "eng" for sub in subtitle_files)
        # ASS should come first due to priority
        assert subtitle_files[0].extension.lower() == ".ass"


class TestFontCollection:
    """Test font file collection functionality."""

    def test_collect_font_attachments_with_fonts_dir(self, temp_dir):
        """Test collecting fonts when Fonts directory exists."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create various font files
        (fonts_dir / "Arial.ttf").write_bytes(b"font data")
        (fonts_dir / "Times.otf").write_bytes(b"font data")
        (fonts_dir / "Custom.woff").write_bytes(b"font data")

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)

        assert len(font_attachments) == 3
        font_names = [font.path.name for font in font_attachments]
        assert "Arial.ttf" in font_names
        assert "Times.otf" in font_names
        assert "Custom.woff" in font_names

    def test_collect_font_attachments_recursive(self, temp_dir):
        """Test recursive font collection."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create nested font directories
        nested_dir = fonts_dir / "nested"
        nested_dir.mkdir()
        deep_nested = nested_dir / "deep"
        deep_nested.mkdir()

        (fonts_dir / "Arial.ttf").write_bytes(b"font data")
        (nested_dir / "Times.otf").write_bytes(b"font data")
        (deep_nested / "Custom.woff").write_bytes(b"font data")

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=True)

        assert len(font_attachments) == 3

    def test_collect_font_attachments_no_fonts_dir(self, temp_dir):
        """Test font collection when no Fonts directory exists."""
        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)
        assert font_attachments == []

    def test_collect_font_extensions_filtering(self, temp_dir):
        """Test that only valid font extensions are collected."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create valid font files
        (fonts_dir / "Arial.ttf").write_bytes(b"font data")
        (fonts_dir / "Times.otf").write_bytes(b"font data")
        (fonts_dir / "Script.woff2").write_bytes(b"font data")

        # Create invalid files (should be ignored)
        (fonts_dir / "readme.txt").write_text("not a font")
        (fonts_dir / "image.png").write_bytes(b"not a font")
        (fonts_dir / "data.json").write_text('{"not": "font"}')

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)

        assert len(font_attachments) == 3
        extension_names = [font.path.suffix for font in font_attachments]
        expected_extensions = {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.TTF', '.OTF', '.TTC', '.WOFF', '.WOFF2'}
        assert all(ext in expected_extensions for ext in extension_names)


class TestFileValidation:
    """Test file validation and filtering."""

    def test_is_video_file_supported_extensions(self, temp_dir):
        """Test video file validation with supported extensions."""
        # Create files with supported extensions
        for ext in submerge.DEFAULT_VIDEO_EXTENSIONS:
            file_path = temp_dir / f"test{ext}"
            file_path.write_text("dummy video")
            assert submerge.is_video_file(file_path) is True

    def test_is_video_file_unsupported_extensions(self, temp_dir):
        """Test video file validation with unsupported extensions."""
        unsupported_extensions = [".avi", ".mov", ".flv", ".wmv", ".txt", ".mp3"]

        for ext in unsupported_extensions:
            file_path = temp_dir / f"test{ext}"
            file_path.write_text("dummy content")
            assert submerge.is_video_file(file_path) is False

    def test_is_video_file_nonexistent_file(self):
        """Test video file validation with non-existent file."""
        non_existent = Path("/nonexistent/path/video.mkv")
        assert submerge.is_video_file(non_existent) is False

    def test_is_video_file_directory(self, temp_dir):
        """Test video file validation with directory."""
        assert submerge.is_video_file(temp_dir) is False

    @patch('subprocess.run')
    def test_get_mime_type_success(self, mock_run):
        """Test MIME type detection success."""
        mock_run.return_value = Mock(
            stdout="text/plain",
            returncode=0
        )

        file_path = Path("/test/file.txt")
        mime_type = submerge.get_mime_type(file_path)

        assert mime_type == "text/plain"
        mock_run.assert_called_once_with(
            ['file', '--brief', '--mime-type', str(file_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

    @patch('subprocess.run')
    def test_get_mime_type_timeout(self, mock_run):
        """Test MIME type detection timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('file', 10)

        file_path = Path("/test/file.txt")
        mime_type = submerge.get_mime_type(file_path)

        assert mime_type == "application/octet-stream"

    @patch('subprocess.run')
    def test_get_mime_type_failure(self, mock_run):
        """Test MIME type detection failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'file')

        file_path = Path("/test/file.txt")
        mime_type = submerge.get_mime_type(file_path)

        assert mime_type == "application/octet-stream"