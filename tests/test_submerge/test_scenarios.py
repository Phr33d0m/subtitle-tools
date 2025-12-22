"""
Real-world scenario tests for submerge.

Tests edge cases and practical scenarios that users commonly encounter,
including Swedish language mapping, encoding issues, and complex file naming.
"""

import subprocess
from unittest.mock import patch, Mock
import submerge


class TestSwedishLanguageMapping:
    """Test Swedish language code mapping scenarios."""

    def test_swedish_se_to_swe_mapping(self, temp_dir):
        """Test that 'se' language code is properly mapped to 'swe'."""
        video_path = temp_dir / "film.mkv"
        video_path.write_text("dummy video content")

        # Create subtitle with Swedish 'se' code
        subtitle_path = temp_dir / "film.se.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nSvensk text")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].language_code == "swe"  # Should be mapped
        assert subtitle_files[0].path == subtitle_path

    def test_swedish_sv_to_swe_mapping(self, temp_dir):
        """Test that 'sv' language code is properly mapped to 'swe'."""
        video_path = temp_dir / "film.mkv"
        video_path.write_text("dummy video content")

        # Create subtitle with Swedish 'sv' code
        subtitle_path = temp_dir / "film.sv.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nSvensk text")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].language_code == "swe"  # Should be mapped
        assert subtitle_files[0].path == subtitle_path

    def test_mixed_swedish_subtitles(self, temp_dir):
        """Test mixing Swedish subtitles with other languages."""
        video_path = temp_dir / "movie.mkv"
        video_path.write_text("dummy video content")

        # Create multiple Swedish subtitle files with different codes
        (temp_dir / "movie.se.srt").write_text("Swedish SE")
        (temp_dir / "movie.sv.srt").write_text("Swedish SV")
        (temp_dir / "movie.eng.srt").write_text("English")
        (temp_dir / "movie.swe.srt").write_text("Swedish proper")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 4

        # Check that all Swedish variants are mapped to 'swe'
        swedish_subs = [sub for sub in subtitle_files if sub.language_code == "swe"]
        assert len(swedish_subs) == 3  # se, sv, and swe should all map to 'swe'

        # Check English subtitle
        english_subs = [sub for sub in subtitle_files if sub.language_code == "eng"]
        assert len(english_subs) == 1

    def test_swedish_ass_subtitles(self, temp_dir):
        """Test Swedish language mapping with ASS subtitles."""
        video_path = temp_dir / "anime.mkv"
        video_path.write_text("dummy video content")

        # Create Swedish ASS subtitle
        subtitle_path = temp_dir / "anime.se.ass"
        subtitle_path.write_text("[V4+ Styles]\nFormat: Name, Fontname\nStyle: Default,Arial\n\n[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,Svensk text")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].language_code == "swe"
        assert subtitle_files[0].extension == ".ass"
        assert subtitle_files[0].priority == 2  # ASS has higher priority


class TestEncodingScenarios:
    """Test subtitle encoding scenarios."""

    def test_utf8_subtitle_handling(self, temp_dir, sample_video_file, mock_encoding_utf8):
        """Test handling of UTF-8 encoded subtitles."""
        subtitle_path = temp_dir / "video.eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nUTF-8 content: ñáéíóú")

        subtitle_files = [submerge.SubtitleFile.from_path(subtitle_path, "video")]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = submerge.merge_video_with_subtitles(
                video_path=sample_video_file,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=True,
                mode="replace"
            )

            assert result is True
            # UTF-8 files should not include charset parameter
            cmd_str = ' '.join(mock_run.call_args[0][0])
            assert '--subtitle-charset' not in cmd_str

    def test_iso8859_subtitle_handling(self, temp_dir, sample_video_file, mock_encoding_iso8859):
        """Test handling of ISO-8859-1 encoded subtitles."""
        subtitle_path = temp_dir / "video.eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nLatin-1 content: àèìòù")

        subtitle_files = [submerge.SubtitleFile.from_path(subtitle_path, "video")]

        # Mock encoding detection to return ISO-8859-1
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "ISO-8859-1"

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=sample_video_file,
                    subtitle_files=subtitle_files,
                    font_attachments=[],
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True
                # ISO-8859-1 files should include charset parameter
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--subtitle-charset' in cmd_str
                assert 'ISO-8859-1' in cmd_str

    def test_unknown_encoding_fallback(self, temp_dir, sample_video_file, mock_encoding_unknown):
        """Test fallback behavior for unknown encoding."""
        subtitle_path = temp_dir / "video.eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nUnknown encoding")

        subtitle_files = [submerge.SubtitleFile.from_path(subtitle_path, "video")]

        # Mock encoding detection to return mapped unknown encoding
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "ISO-8859-1"  # unknown-8bit maps to ISO-8859-1

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=sample_video_file,
                    subtitle_files=subtitle_files,
                    font_attachments=[],
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True
                # unknown-8bit should map to ISO-8859-1
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--subtitle-charset' in cmd_str
                assert 'ISO-8859-1' in cmd_str

    def test_encoding_detection_failure(self, temp_dir, sample_video_file):
        """Test behavior when encoding detection fails."""
        subtitle_path = temp_dir / "video.eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nTest content")

        subtitle_files = [submerge.SubtitleFile.from_path(subtitle_path, "video")]

        with patch('subprocess.run') as mock_run:
            # Mock encoding detection failure
            mock_run.side_effect = [
                Mock(side_effect=Exception("Encoding detection failed")),  # file command fails
                Mock(returncode=0)  # mkvmerge succeeds
            ]

            result = submerge.merge_video_with_subtitles(
                video_path=sample_video_file,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=True,
                mode="replace"
            )

            assert result is True
            # Should fall back to UTF-8 when detection fails


class TestComplexFileNaming:
    """Test scenarios with complex file naming patterns."""

    def test_movie_with_year_and_quality(self, temp_dir):
        """Test movie files with complex naming including year and quality."""
        video_path = temp_dir / "The.Matrix.1999.1080p.BluRay.x264.mkv"
        video_path.write_text("dummy video content")

        # Create matching subtitle with same complex name
        subtitle_path = temp_dir / "The.Matrix.1999.1080p.BluRay.x264.eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nSubtitle")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].path == subtitle_path
        assert subtitle_files[0].language_code == "eng"

    def test_tv_series_naming(self, temp_dir):
        """Test TV series episode naming patterns."""
        video_path = temp_dir / "Game.of.Thrones.S01E01.Winter.Is.Coming.mkv"
        video_path.write_text("dummy video content")

        # Create multiple language subtitles for the episode
        subtitle_files_created = [
            ("Game.of.Thrones.S01E01.Winter.Is.Coming.eng.srt", "eng"),
            ("Game.of.Thrones.S01E01.Winter.Is.Coming.spa.srt", "spa"),
            ("Game.of.Thrones.S01E01.Winter.Is.Coming.se.srt", "swe"),  # Swedish mapping
        ]

        for filename, expected_lang in subtitle_files_created:
            subtitle_path = temp_dir / filename
            subtitle_path.write_text(f"Subtitle in {expected_lang}")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 3
        found_languages = {sub.language_code for sub in subtitle_files}
        expected_languages = {"eng", "spa", "swe"}
        assert found_languages == expected_languages

    def test_special_characters_in_filenames(self, temp_dir):
        """Test filenames with special characters."""
        video_path = temp_dir / "Movie [2023] (Director's Cut).mkv"
        video_path.write_text("dummy video content")

        subtitle_path = temp_dir / "Movie [2023] (Director's Cut).eng.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nSpecial characters")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].path.name == "Movie [2023] (Director's Cut).eng.srt"

    def test_unicode_filenames(self, temp_dir):
        """Test filenames with Unicode characters."""
        video_path = temp_dir / "Amélie.mkv"
        video_path.write_text("dummy video content")

        subtitle_path = temp_dir / "Amélie.fra.srt"
        subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nFilm français")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 1
        assert subtitle_files[0].path.name == "Amélie.fra.srt"
        assert subtitle_files[0].language_code == "fra"

    def test_mixed_extensions_and_languages(self, temp_dir):
        """Test mixing different subtitle formats and languages."""
        video_path = temp_dir / "complex.mkv"
        video_path.write_text("dummy video content")

        # Create various subtitle formats
        subtitle_variants = [
            ("complex.eng.srt", "eng", ".srt", 1),
            ("complex.eng.ass", "eng", ".ass", 2),  # Higher priority
            ("complex.se.srt", "swe", ".srt", 1),   # Swedish mapping
            ("complex.fra.ass", "fra", ".ass", 2),
        ]

        for filename, expected_lang, ext, priority in subtitle_variants:
            subtitle_path = temp_dir / filename
            if ext == ".ass":
                subtitle_path.write_text("[V4+ Styles]\nFormat: Name\nStyle: Default,Arial\n\n[Events]\nDialogue: 0,0:00:01.00,0:00:02.00,Default,Test")
            else:
                subtitle_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nTest")

        subtitle_files = submerge.find_subtitle_files(video_path)

        assert len(subtitle_files) == 4

        # Check that ASS files come before SRT files for same language
        english_subs = [sub for sub in subtitle_files if sub.language_code == "eng"]
        assert len(english_subs) == 2
        # ASS should have higher priority (come first)
        assert english_subs[0].extension == ".ass"
        assert english_subs[1].extension == ".srt"


class TestFontScenarios:
    """Test font-related scenarios."""

    def test_missing_fonts_folder_replace_mode(self, temp_dir, sample_video_file, sample_ass_file):
        """Test replace mode behavior when no Fonts folder exists - should still use --no-subtitles."""
        video_path = sample_video_file
        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]

        # No fonts directory exists
        assert not (temp_dir / "Fonts").exists()

        # Mock encoding detection
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[],  # No external fonts
                    temp_dir=temp_dir,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True
                # Should include --no-subtitles in replace mode (removes subs, preserves font attachments)
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--no-subtitles' in cmd_str

    def test_fonts_folder_with_various_formats(self, temp_dir, sample_video_file, sample_ass_file):
        """Test fonts directory with various font formats."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create various font files
        font_files = {
            "Arial.ttf": b"ttf content",
            "Times.otf": b"otf content",
            "Custom.woff": b"woff content",
            "Script.woff2": b"woff2 content",
            "readme.txt": b"not a font",  # Should be ignored
            "image.png": b"not a font",    # Should be ignored
        }

        for filename, content in font_files.items():
            (fonts_dir / filename).write_bytes(content)

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)

        # Should only include valid font files
        assert len(font_attachments) == 4
        font_names = [font.path.name for font in font_attachments]
        assert "Arial.ttf" in font_names
        assert "Times.otf" in font_names
        assert "Custom.woff" in font_names
        assert "Script.woff2" in font_names
        assert "readme.txt" not in font_names
        assert "image.png" not in font_names

    def test_nested_fonts_directory(self, temp_dir):
        """Test recursive font collection from nested directories."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create nested structure
        nested_dir = fonts_dir / "nested"
        nested_dir.mkdir()
        deep_nested = nested_dir / "deep"
        deep_nested.mkdir()

        # Place fonts at different levels
        (fonts_dir / "Arial.ttf").write_bytes(b"arial")
        (nested_dir / "Times.otf").write_bytes(b"times")
        (deep_nested / "Custom.woff").write_bytes(b"custom")

        # Test non-recursive
        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)
        assert len(font_attachments) == 1
        assert font_attachments[0].path.name == "Arial.ttf"

        # Test recursive
        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=True)
        assert len(font_attachments) == 3
        font_names = {font.path.name for font in font_attachments}
        assert font_names == {"Arial.ttf", "Times.otf", "Custom.woff"}

    def test_font_deduplication_real_world(self, temp_dir, sample_video_file, sample_ass_file):
        """Test font deduplication with realistic font names."""
        [submerge.SubtitleFile.from_path(sample_ass_file, "test")]

        # Create fonts directory with variations of similar fonts
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        font_variants = [
            "Arial.ttf",
            "Arial_Bold.ttf",
            "Arial-Italic.ttf",
            "Times.ttf",
            "Times_New_Roman.ttf",
        ]

        for font_name in font_variants:
            (fonts_dir / font_name).write_bytes(f"content of {font_name}".encode())

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)

        # Mock existing fonts in video
        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = ["Arial.ttf", "Times.ttf"]

            # Filter fonts for append mode (should deduplicate)
            filtered_fonts = [
                font for font in font_attachments
                if submerge.should_attach_font(font.path, mock_fonts.return_value, "append")
            ]

            # Should exclude Arial.ttf (exists) and Times.ttf (exists)
            # But include variants (Arial_Bold.ttf, Arial-Italic.ttf, Times_New_Roman.ttf)
            assert len(filtered_fonts) == 3
            filtered_names = {font.path.name for font in filtered_fonts}
            assert filtered_names == {"Arial_Bold.ttf", "Arial-Italic.ttf", "Times_New_Roman.ttf"}


class TestErrorRecoveryScenarios:
    """Test error recovery and edge case scenarios."""

    def test_mkvmerge_timeout_recovery(self, temp_dir, sample_video_file, sample_srt_file):
        """Test behavior when mkvmerge times out."""
        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired('mkvmerge', 300)

            result = submerge.merge_video_with_subtitles(
                video_path=sample_video_file,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=False,
                mode="replace"
            )

            assert result is False

    def test_partial_font_collection(self, temp_dir):
        """Test font collection when some files are corrupted."""
        fonts_dir = temp_dir / "Fonts"
        fonts_dir.mkdir()

        # Create mix of valid and potentially problematic files
        (fonts_dir / "GoodFont.ttf").write_bytes(b"valid font")
        (fonts_dir / "ZeroSize.ttf").write_bytes(b"")  # Empty file
        (fonts_dir / "NoPermissions.otf").write_bytes(b"font content")

        # Make one file unreadable (if we can)
        try:
            no_perms = fonts_dir / "NoPermissions.otf"
            no_perms.chmod(0o000)
        except Exception:
            # Skip permission test if we can't set permissions
            pass

        font_attachments = submerge.collect_font_attachments(temp_dir, recursive=False)

        # Should still find the valid font
        valid_fonts = [font for font in font_attachments if font.path.name == "GoodFont.ttf"]
        assert len(valid_fonts) >= 1

    def test_mixed_video_formats_in_directory(self, temp_dir):
        """Test directory with multiple video formats."""
        # Create video files with different extensions
        supported_videos = [
            "movie.mkv",
            "clip.mp4",
            "animation.webm"
        ]
        unsupported_videos = [
            "video.avi",
            "movie.mov",
            "clip.flv"
        ]

        # Create supported videos
        for video_name in supported_videos:
            (temp_dir / video_name).write_text("dummy video")

        # Create unsupported videos
        for video_name in unsupported_videos:
            (temp_dir / video_name).write_text("dummy video")

        video_files = submerge.find_video_files(temp_dir, recursive=False)

        # Should only find supported formats
        assert len(video_files) == len(supported_videos)
        found_names = {v.name for v in video_files}
        expected_names = set(supported_videos)
        assert found_names == expected_names

    def test_large_batch_processing_simulation(self, temp_dir):
        """Test behavior with many files to simulate batch processing."""
        # Create many video files
        video_files = []
        for i in range(10):
            video = temp_dir / f"video_{i:03d}.mkv"
            video.write_text(f"video content {i}")
            video_files.append(video)

        # Create subtitles for some of them
        for i in range(0, 10, 2):  # Every other video
            subtitle = temp_dir / f"video_{i:03d}.eng.srt"
            subtitle.write_text(f"subtitle {i}")

        found_videos = submerge.find_video_files(temp_dir, recursive=False)
        assert len(found_videos) == 10

        # Test subtitle finding for each video
        videos_with_subs = 0
        for video in found_videos:
            subs = submerge.find_subtitle_files(video)
            if subs:
                videos_with_subs += 1

        # Should find subtitles for every other video (5 total)
        assert videos_with_subs == 5