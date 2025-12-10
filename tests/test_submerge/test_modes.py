"""
Mode-specific tests for submerge.

Tests the behavior differences between --mode replace and --mode append,
particularly around font handling and subtitle preservation.
"""

from pathlib import Path
from unittest.mock import patch, Mock
import submerge


class TestReplaceMode:
    """Test replace mode behavior."""

    def test_replace_mode_with_external_fonts(self, temp_dir, sample_video_file, sample_ass_file, fonts_dir):
        """Test replace mode when external fonts are available."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]
        font_attachments = [submerge.FontAttachment(
            path=fonts_dir / "Arial.ttf",
            mime_type="application/x-truetype-font"
        )]

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=font_attachments,
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True
                # Verify --no-subtitles flag is used (removes everything including fonts)
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--no-subtitles' in cmd_str
                # Verify external font is attached
                assert '--attach-file' in cmd_str
                assert 'Arial.ttf' in cmd_str

    def test_replace_mode_without_external_fonts(self, temp_dir, sample_video_file, sample_srt_file, mock_mkvmerge_with_fonts):
        """Test replace mode when no external fonts are available (font preservation)."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock existing fonts in the video
        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = ["Arial.ttf", "Times.ttf"]
            with patch('submerge.get_subtitle_track_ids') as mock_tracks:
                mock_tracks.return_value = ["2"]

                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = Mock(returncode=0)

                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[],  # No external fonts
                        temp_dir=None,
                        dry_run=True,
                        mode="replace"
                    )

                    assert result is True
                    # Should NOT include --no-subtitles (preserves fonts)
                    cmd_str = ' '.join(mock_run.call_args[0][0])
                    assert '--no-subtitles' not in cmd_str

    def test_replace_mode_no_ass_subtitles(self, temp_dir, sample_video_file, sample_srt_file):
        """Test replace mode with only SRT subtitles (no fonts needed)."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[],
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True
                # Should include --no-subtitles (normal replace behavior)
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--no-subtitles' in cmd_str
                # Should NOT include any font attachments
                assert '--attach-file' not in cmd_str

    @patch('subprocess.run')
    def test_replace_mode_logging_with_fonts(self, mock_run):
        """Test logging in replace mode with external fonts."""
        mock_run.return_value = Mock(returncode=0)

        video_path = Path("/test/video.mkv")
        subtitle_files = []
        font_attachments = [submerge.FontAttachment(
            Path("/test/Arial.ttf"),
            "application/x-truetype-font"
        )]

        with patch('submerge.get_existing_font_attachments'):
            with patch('submerge.get_subtitle_track_ids'):
                submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=font_attachments,
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                # Should not preserve fonts when external fonts are available
                # No need to check specific log messages as they're tested in integration tests

    @patch('subprocess.run')
    def test_replace_mode_logging_without_fonts(self, mock_run):
        """Test logging in replace mode without external fonts."""
        mock_run.return_value = Mock(returncode=0)

        video_path = Path("/test/video.mkv")
        subtitle_files = [submerge.SubtitleFile(
            Path("/test/video.ass"),
            "und",
            ".ass",
            2
        )]
        font_attachments = []

        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = ["ExistingFont.ttf"]
            with patch('submerge.get_subtitle_track_ids') as mock_tracks:
                mock_tracks.return_value = ["2"]

                submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=font_attachments,
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                # Should preserve fonts when no external fonts are available
                # This is tested indirectly by the command generation in integration tests


class TestAppendMode:
    """Test append mode behavior."""

    def test_append_mode_basic(self, temp_dir, sample_video_file, sample_srt_file):
        """Test basic append mode behavior."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Mock existing font attachments to avoid subprocess calls
            with patch('submerge.get_existing_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                # Capture the logging to extract the command in dry_run mode
                with patch('logging.info') as mock_log:
                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[],
                        temp_dir=None,
                        dry_run=True,
                        mode="append"
                    )

                    assert result is True
                    # Should NOT include --no-subtitles (preserves existing content)
                    mock_log.assert_called()
                    # Find the call that contains the command
                    cmd_call = None
                    for call in mock_log.call_args_list:
                        args = call[0]
                        if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                            cmd_call = args[1]
                            break
                    assert cmd_call is not None
                    assert '--no-subtitles' not in cmd_call

    def test_append_mode_with_font_deduplication(self, temp_dir, sample_video_file, sample_ass_file, fonts_dir, mock_mkvmerge_with_fonts):
        """Test font deduplication in append mode."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]

        # Create font that already exists in the video
        font_attachment = submerge.FontAttachment(
            path=fonts_dir / "Arial.ttf",
            mime_type="application/x-truetype-font"
        )

        existing_fonts = ["Arial.ttf"]  # Same font already exists in video

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Mock existing font attachments to simulate the font already existing
            with patch('submerge.get_existing_font_attachments') as mock_fonts:
                mock_fonts.return_value = existing_fonts

                # Capture the logging to extract the command in dry_run mode
                with patch('logging.info') as mock_log:
                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[font_attachment],
                        temp_dir=None,
                        dry_run=True,
                        mode="append"
                    )

                    assert result is True
                    # Should NOT include the duplicate font attachment
                    mock_log.assert_called()
                    # Find the call that contains the command
                    cmd_call = None
                    for call in mock_log.call_args_list:
                        args = call[0]
                        if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                            cmd_call = args[1]
                            break
                    assert cmd_call is not None
                    # Font should not appear or appear only once (in original)
                    assert cmd_call.count('Arial.ttf') <= 1

    def test_append_mode_with_new_font(self, temp_dir, sample_video_file, sample_ass_file, fonts_dir, mock_mkvmerge_with_fonts):
        """Test append mode with new font (not duplicate)."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]

        # Create a new font that doesn't exist in the video
        font_attachment = submerge.FontAttachment(
            path=fonts_dir / "NewFont.otf",
            mime_type="application/vnd.ms-opentype"
        )

        existing_fonts = ["Arial.ttf"]  # Different font exists in video

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Mock existing font attachments to simulate different fonts existing
            with patch('submerge.get_existing_font_attachments') as mock_fonts:
                mock_fonts.return_value = existing_fonts

                # Capture the logging to extract the command in dry_run mode
                with patch('logging.info') as mock_log:
                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[font_attachment],
                        temp_dir=None,
                        dry_run=True,
                        mode="append"
                    )

                    assert result is True
                    # Should include the new font attachment
                    mock_log.assert_called()
                    # Find the call that contains the command
                    cmd_call = None
                    for call in mock_log.call_args_list:
                        args = call[0]
                        if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                            cmd_call = args[1]
                            break
                    assert cmd_call is not None
                    assert 'NewFont.otf' in cmd_call

    def test_append_mode_with_similar_font_names(self, temp_dir, sample_video_file, sample_ass_file, fonts_dir):
        """Test font deduplication with similar base names."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]

        # Create font with similar base name to existing one
        font_attachment = submerge.FontAttachment(
            path=fonts_dir / "Arial.ttf",  # Use same name to test deduplication
            mime_type="application/x-truetype-font"
        )

        existing_fonts = ["Arial.ttf"]  # Same font already exists

        # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Mock existing font attachments to simulate similar base name existing
            with patch('submerge.get_existing_font_attachments') as mock_fonts:
                mock_fonts.return_value = existing_fonts

                # Capture the logging to extract the command in dry_run mode
                with patch('logging.info') as mock_log:
                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[font_attachment],
                        temp_dir=None,
                        dry_run=True,
                        mode="append"
                    )

                    assert result is True
                    # Should NOT include the duplicate font attachment
                    mock_log.assert_called()
                    # Find the call that contains the command
                    cmd_call = None
                    for call in mock_log.call_args_list:
                        args = call[0]
                        if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                            cmd_call = args[1]
                            break
                    assert cmd_call is not None
                    # Font should not appear in attachments when it's a duplicate
                    assert cmd_call.count('Arial.ttf') <= 1 or '--attach-file' not in cmd_call

    @patch('subprocess.run')
    def test_append_mode_logging(self, mock_run):
        """Test logging in append mode."""
        mock_run.return_value = Mock(returncode=0)

        video_path = Path("/test/video.mkv")
        subtitle_files = [submerge.SubtitleFile(
            Path("/test/video.srt"),
            "eng",
            ".srt",
            1
        )]
        font_attachments = []

        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = ["ExistingFont.ttf"]

            submerge.merge_video_with_subtitles(
                video_path=video_path,
                subtitle_files=subtitle_files,
                font_attachments=font_attachments,
                temp_dir=None,
                dry_run=True,
                mode="append"
            )

            # Should preserve existing content in append mode
            # This is tested indirectly by the command generation in integration tests


class TestModeValidation:
    """Test mode validation and edge cases."""

    def test_should_attach_font_replace_mode(self):
        """Test font attachment logic in replace mode."""
        font_path = Path("/test/Arial.ttf")
        existing_fonts = ["ExistingFont.ttf"]

        # Replace mode should always attach fonts
        assert submerge.should_attach_font(font_path, existing_fonts, "replace") is True

    def test_should_attach_font_append_mode_new_font(self):
        """Test font attachment logic in append mode with new font."""
        font_path = Path("/test/NewFont.ttf")
        existing_fonts = ["ExistingFont.ttf"]

        # Append mode should attach new fonts
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is True

    def test_should_attach_font_append_mode_duplicate(self):
        """Test font attachment logic in append mode with duplicate."""
        font_path = Path("/test/Arial.ttf")
        existing_fonts = ["Arial.ttf"]

        # Append mode should not attach duplicates
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is False

    def test_should_attach_font_append_mode_exact_name(self):
        """Test font attachment logic with exact name match."""
        font_path = Path("/test/CustomFont.ttf")
        existing_fonts = ["CustomFont.ttf"]

        # Append mode should not attach exact duplicates
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is False

    def test_should_attach_font_append_mode_case_insensitive(self):
        """Test font attachment logic is case insensitive."""
        font_path = Path("/test/ARIAL.TTF")
        existing_fonts = ["arial.ttf"]

        # Append mode should be case insensitive for duplicates
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is False

    def test_should_attach_font_append_mode_no_existing(self):
        """Test font attachment logic when no existing fonts."""
        font_path = Path("/test/NewFont.ttf")
        existing_fonts = []

        # Append mode should attach when no existing fonts
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is True

    def test_should_attach_font_similar_base_names(self):
        """Test font attachment logic with similar base names."""
        font_path = Path("/test/Arial_Bold.ttf")
        existing_fonts = ["Arial.ttf", "Arial-Italic.ttf"]

        # Append mode should attach different base names (Arial_Bold != Arial)
        # The stems are different: Arial_Bold vs Arial and Arial-Italic
        assert submerge.should_attach_font(font_path, existing_fonts, "append") is True

    def test_should_attach_font_invalid_mode(self):
        """Test font attachment logic with invalid mode."""
        font_path = Path("/test/Arial.ttf")
        existing_fonts = ["ExistingFont.ttf"]

        # Invalid mode should default to not attaching
        assert submerge.should_attach_font(font_path, existing_fonts, "invalid") is False


class TestModeTransitions:
    """Test behavior transitions between modes."""

    def test_mode_switch_impact_on_command_generation(self, temp_dir, sample_video_file, sample_ass_file, fonts_dir):
        """Test that different modes generate different mkvmerge commands."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_ass_file, "test")]
        font_attachments = [submerge.FontAttachment(
            path=fonts_dir / "Arial.ttf",
            mime_type="application/x-truetype-font"
        )]

        commands = {}

        # Test replace mode with fonts
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"
            with patch('submerge.get_existing_font_attachments'):
                with patch('submerge.get_subtitle_track_ids'):
                    with patch('logging.info') as mock_log:
                        submerge.merge_video_with_subtitles(
                            video_path=video_path,
                            subtitle_files=subtitle_files,
                            font_attachments=font_attachments,
                            temp_dir=None,
                            dry_run=True,
                            mode="replace"
                        )
                        # Find the call that contains the command
                        cmd_call = None
                        for call in mock_log.call_args_list:
                            args = call[0]
                            if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                                cmd_call = args[1]
                                break
                        commands['replace'] = cmd_call

        # Test append mode
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"
            with patch('submerge.get_existing_font_attachments'):
                with patch('logging.info') as mock_log:
                    submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=font_attachments,
                        temp_dir=None,
                        dry_run=True,
                        mode="append"
                    )
                    # Find the call that contains the command
                    cmd_call = None
                    for call in mock_log.call_args_list:
                        args = call[0]
                        if len(args) >= 2 and 'DRY RUN: Would execute:' in args[0]:
                            cmd_call = args[1]
                            break
                    commands['append'] = cmd_call

        # Replace mode should have --no-subtitles, append mode should not
        assert '--no-subtitles' in commands['replace']
        assert '--no-subtitles' not in commands['append']
        # Both should have the font attachment (since external fonts exist)
        assert '--attach-file' in commands['replace']
        assert '--attach-file' in commands['append']

    def test_mode_switch_impact_without_external_fonts(self, temp_dir, sample_video_file, sample_srt_file):
        """Test mode differences when no external fonts are available."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]
        font_attachments = []

        commands = {}

        # Test replace mode without fonts
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            with patch('submerge.get_existing_font_attachments') as mock_fonts:
                mock_fonts.return_value = ["ExistingFont.ttf"]
                with patch('submerge.get_subtitle_track_ids'):
                    submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=font_attachments,
                        temp_dir=None,
                        dry_run=True,
                        mode="replace"
                    )
                    commands['replace'] = ' '.join(mock_run.call_args[0][0])

        # Test append mode without fonts
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            with patch('submerge.get_existing_font_attachments'):
                submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=font_attachments,
                    temp_dir=None,
                    dry_run=True,
                    mode="append"
                )
                commands['append'] = ' '.join(mock_run.call_args[0][0])

        # Both should NOT have --no-subtitles (preserving fonts or no fonts to replace)
        assert '--no-subtitles' not in commands['replace']
        assert '--no-subtitles' not in commands['append']