"""
Unit tests for submerge utility functions.

Tests individual functions and classes in isolation to ensure
correct behavior of core utilities.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock
import submerge


class TestSubtitleFile:
    """Test SubtitleFile dataclass and from_path method."""

    def test_subtitle_file_creation(self):
        """Test SubtitleFile object creation."""
        path = Path("/test/video.eng.srt")
        subtitle = submerge.SubtitleFile(
            path=path,
            language_code="eng",
            extension=".srt",
            priority=1
        )

        assert subtitle.path == path
        assert subtitle.language_code == "eng"
        assert subtitle.extension == ".srt"
        assert subtitle.priority == 1

    def test_from_path_with_language_code(self, sample_video_file):
        """Test SubtitleFile.from_path with compound extension."""
        subtitle_path = sample_video_file.parent / "video.eng.srt"
        subtitle_path.write_text("test subtitle")

        subtitle = submerge.SubtitleFile.from_path(subtitle_path, "video")

        assert subtitle is not None
        assert subtitle.language_code == "eng"
        assert subtitle.extension == ".srt"
        assert subtitle.priority == 1

    def test_from_path_without_base_name(self, temp_dir):
        """Test SubtitleFile.from_path without base name."""
        subtitle_path = temp_dir / "random.eng.srt"
        subtitle_path.write_text("test subtitle")

        subtitle = submerge.SubtitleFile.from_path(subtitle_path, None)

        # Should return None when no base name provided and doesn't match pattern
        assert subtitle is not None  # Falls back to general compound extension case

    def test_from_path_swedish_code(self, sample_video_file):
        """Test SubtitleFile.from_path with Swedish 'se' code."""
        subtitle_path = sample_video_file.parent / "video.se.srt"
        subtitle_path.write_text("test subtitle")

        subtitle = submerge.SubtitleFile.from_path(subtitle_path, "video")

        assert subtitle is not None
        assert subtitle.language_code == "swe"  # Should be mapped to swe

    def test_from_path_invalid_extension(self):
        """Test SubtitleFile.from_path with invalid file extension."""
        video_path = Path("/test/video.mp4")
        subtitle = submerge.SubtitleFile.from_path(video_path, "video")
        assert subtitle is None

    def test_from_path_invalid_language_code(self, sample_video_file):
        """Test SubtitleFile.from_path with invalid language code."""
        subtitle_path = sample_video_file.parent / "video.xx.srt"  # 2-char invalid code
        subtitle_path.write_text("test subtitle")

        subtitle = submerge.SubtitleFile.from_path(subtitle_path, "video")

        assert subtitle is not None  # Falls back to 2-letter code
        assert subtitle.language_code == "xx"


class TestLanguageDetection:
    """Test language code detection and normalization."""

    def test_detect_language_code_swedish(self):
        """Test Swedish language code detection."""
        assert submerge.detect_language_code("se") == "swe"
        assert submerge.detect_language_code("sv") == "swe"

    def test_detect_language_code_english(self):
        """Test English language code detection."""
        assert submerge.detect_language_code("en") == "eng"
        assert submerge.detect_language_code("eng") == "eng"

    def test_detect_language_code_empty(self):
        """Test empty language code."""
        assert submerge.detect_language_code("") == "und"
        assert submerge.detect_language_code(None) == "und"

    def test_detect_language_code_three_letter(self):
        """Test 3-letter language codes."""
        assert submerge.detect_language_code("jpn") == "jpn"
        assert submerge.detect_language_code("kor") == "kor"

    def test_detect_language_code_ietf_tag(self):
        """Test IETF language tags."""
        assert submerge.detect_language_code("zh-Hans") == "zh-Hans"
        assert submerge.detect_language_code("pt-BR") == "pt-BR"

    def test_detect_language_code_unrecognized_2letter(self):
        """Test unrecognized 2-letter codes."""
        result = submerge.detect_language_code("xx")
        assert result == "xx"  # Falls back to lowercase 2-letter code

    def test_get_language_name_english(self):
        """Test getting language name for English."""
        assert submerge.get_language_name("eng") == "English"

    def test_get_language_name_swedish(self):
        """Test getting language name for Swedish."""
        assert submerge.get_language_name("swe") == "Swedish"

    def test_get_language_name_unknown(self):
        """Test getting language name for unknown code."""
        assert submerge.get_language_name("und") == "Unknown"
        assert submerge.get_language_name("invalid") == "Invalid"

    def test_get_language_name_ietf_tag(self):
        """Test getting language name for IETF tag."""
        assert submerge.get_language_name("zh-Hans") == "Chinese (Simplified)"


class TestEncodingDetection:
    """Test subtitle file encoding detection."""

    def test_detect_subtitle_encoding_utf8(self, mock_encoding_utf8):
        """Test UTF-8 encoding detection."""
        subtitle_path = Path("/test/subtitle.srt")
        encoding = submerge.detect_subtitle_encoding(subtitle_path)
        assert encoding == "UTF-8"

    def test_detect_subtitle_encoding_iso8859(self, mock_encoding_iso8859):
        """Test ISO-8859-1 encoding detection."""
        subtitle_path = Path("/test/subtitle.srt")
        encoding = submerge.detect_subtitle_encoding(subtitle_path)
        assert encoding == "ISO-8859-1"

    def test_detect_subtitle_encoding_unknown(self, mock_encoding_unknown):
        """Test unknown encoding detection."""
        subtitle_path = Path("/test/subtitle.srt")
        encoding = submerge.detect_subtitle_encoding(subtitle_path)
        assert encoding == "ISO-8859-1"  # unknown-8bit maps to ISO-8859-1

    def test_detect_subtitle_encoding_failure(self):
        """Test encoding detection when subprocess fails."""
        subtitle_path = Path("/test/subtitle.srt")
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'file')
            encoding = submerge.detect_subtitle_encoding(subtitle_path)
            assert encoding == "UTF-8"  # Falls back to UTF-8 on failure


class TestFontHandling:
    """Test font handling functions."""

    def test_should_attach_font_replace_mode(self):
        """Test font attachment in replace mode."""
        font_path = Path("/test/Arial.ttf")
        existing_fonts = ["existing_font.ttf"]

        # Replace mode should always attach
        assert submerge.should_attach_font(font_path, existing_fonts, "replace") is True

    def test_should_attach_font_append_mode_new_font(self):
        """Test font attachment in append mode with new font."""
        font_path = Path("/test/NewFont.ttf")
        existing_fonts = ["existing_font.ttf"]

        # Append mode should attach if not duplicate
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is True

    def test_should_attach_font_append_mode_duplicate(self):
        """Test font attachment in append mode with duplicate font."""
        font_path = Path("/test/Arial.ttf")
        existing_fonts = ["Arial.ttf"]

        # Append mode should not attach duplicates
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is False

    def test_should_attach_font_append_mode_similar_name(self):
        """Test font attachment in append mode with similar but not identical base names."""
        font_path = Path("/test/Arial_Bold.ttf")  # Similar but different name
        existing_fonts = ["Arial.ttf"]

        # Append mode should attach fonts with similar but not identical base names
        # (current implementation only checks exact base name matches)
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is True

    @patch('subprocess.run')
    def test_get_existing_font_attachments_success(self, mock_run):
        """Test successful existing font attachment detection."""
        mock_run.return_value = Mock(
            stdout="File ID 0: video\nFile ID 1: attachment ID 1: application/x-truetype-font:Arial.ttf",
            returncode=0
        )

        video_path = Path("/test/video.mkv")
        fonts = submerge.get_existing_font_attachments(video_path)

        assert fonts == ["Arial.ttf"]
        mock_run.assert_called_once_with(
            ['mkvmerge', '--identify', str(video_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30
        )

    @patch('subprocess.run')
    def test_get_existing_font_attachments_no_fonts(self, mock_run):
        """Test existing font attachment detection with no fonts."""
        mock_run.return_value = Mock(
            stdout="Track ID 1: video (AVC/H.264)",
            returncode=0
        )

        video_path = Path("/test/video.mkv")
        fonts = submerge.get_existing_font_attachments(video_path)

        assert fonts == []

    @patch('subprocess.run')
    def test_get_existing_font_attachments_failure(self, mock_run):
        """Test existing font attachment detection failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'mkvmerge')

        video_path = Path("/test/video.mkv")
        fonts = submerge.get_existing_font_attachments(video_path)

        assert fonts == []

    @patch('subprocess.run')
    def test_get_subtitle_track_ids_success(self, mock_run):
        """Test successful subtitle track ID detection."""
        mock_run.return_value = Mock(
            stdout="Track ID 2: subtitles (SubRip)\nTrack ID 3: subtitles (SubRip)",
            returncode=0
        )

        video_path = Path("/test/video.mkv")
        track_ids = submerge.get_subtitle_track_ids(video_path)

        assert track_ids == ["2", "3"]

    @patch('subprocess.run')
    def test_get_subtitle_track_ids_no_subtitles(self, mock_run):
        """Test subtitle track ID detection with no subtitles."""
        mock_run.return_value = Mock(
            stdout="Track ID 1: video (AVC/H.264)\nTrack ID 2: audio (AAC)",
            returncode=0
        )

        video_path = Path("/test/video.mkv")
        track_ids = submerge.get_subtitle_track_ids(video_path)

        assert track_ids == []


class TestUtilityFunctions:
    """Test general utility functions."""

    def test_is_video_file_supported_extensions(self, temp_dir):
        """Test video file detection with supported extensions."""
        video_path = temp_dir / "video.mkv"
        video_path.write_text("dummy video content")
        assert submerge.is_video_file(video_path) is True

        mp4_path = temp_dir / "video.mp4"
        mp4_path.write_text("dummy video content")
        assert submerge.is_video_file(mp4_path) is True

        mkv_path = temp_dir / "video.MKV"
        mkv_path.write_text("dummy video content")
        assert submerge.is_video_file(mkv_path) is True

    def test_is_video_file_unsupported_extensions(self):
        """Test video file detection with unsupported extensions."""
        assert submerge.is_video_file(Path("/test/video.txt")) is False
        assert submerge.is_video_file(Path("/test/video.avi")) is False

    def test_is_video_file_nonexistent(self):
        """Test video file detection with non-existent file."""
        assert submerge.is_video_file(Path("/nonexistent/video.mkv")) is False

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

    @patch('subprocess.run')
    def test_get_mime_type_failure(self, mock_run):
        """Test MIME type detection failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'file')

        file_path = Path("/test/file.txt")
        mime_type = submerge.get_mime_type(file_path)

        assert mime_type == "application/octet-stream"

    def test_normalize_language_code(self):
        """Test language code normalization."""
        assert submerge.normalize_language_code("eng") == "eng"
        assert submerge.normalize_language_code(" zh-Hans ") == "zh-Hans"
        assert submerge.normalize_language_code("PT-BR") == "PT-BR"


class TestProcessingStats:
    """Test ProcessingStats dataclass."""

    def test_processing_stats_creation(self):
        """Test ProcessingStats object creation."""
        stats = submerge.ProcessingStats()
        assert stats.total_videos == 0
        assert stats.processed_videos == 0
        assert stats.skipped_videos == 0
        assert stats.failed_videos == 0
        assert stats.total_subtitle_tracks == 0
        assert stats.fonts_embedded == 0

    def test_processing_stats_string_representation(self):
        """Test ProcessingStats string representation."""
        stats = submerge.ProcessingStats(
            total_videos=5,
            processed_videos=3,
            skipped_videos=1,
            failed_videos=1,
            total_subtitle_tracks=6,
            fonts_embedded=2
        )

        stats_str = str(stats)
        assert "Total videos found: 5" in stats_str
        assert "Successfully processed: 3" in stats_str
        assert "Skipped: 1" in stats_str
        assert "Failed: 1" in stats_str
        assert "Total subtitle tracks merged: 6" in stats_str
        assert "Fonts embedded: 2" in stats_str

    def test_processing_stats_default_values(self):
        """Test ProcessingStats with default values."""
        stats = submerge.ProcessingStats()

        # Should not raise any errors
        str(stats)
        assert stats.total_videos == 0