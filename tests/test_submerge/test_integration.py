"""
Integration tests for submerge merge functionality.

Tests the complete merge workflow including subtitle processing,
font handling, and mkvmerge command generation.
"""

import subprocess
from unittest.mock import patch, Mock
import submerge


class TestMergeVideoWithSubtitles:
    """Test the main merge_video_with_subtitles function."""

    def test_merge_video_with_subtitles_replace_mode_with_fonts(self, temp_dir, sample_video_file, sample_srt_file, sample_ass_file, fonts_dir, mock_subprocess_success):
        """Test replace mode with external fonts available."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [
            submerge.SubtitleFile.from_path(sample_srt_file, "test"),
            submerge.SubtitleFile.from_path(sample_ass_file, "test")
        ]

        # Mock font detection to return our test font
        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = []

            # Mock encoding detection to avoid subprocess calls interfering with mkvmerge mock
            with patch('submerge.detect_subtitle_encoding') as mock_encoding:
                mock_encoding.return_value = "UTF-8"

                # Capture the logging to extract the command in dry_run mode
                with patch('logging.info') as mock_log:
                    result = submerge.merge_video_with_subtitles(
                        video_path=video_path,
                        subtitle_files=subtitle_files,
                        font_attachments=[submerge.FontAttachment(
                            path=fonts_dir / "Arial.ttf",
                            mime_type="application/x-truetype-font"
                        )],
                        temp_dir=None,
                        dry_run=True,
                        mode="replace"
                    )

                    assert result is True

                    # Verify the logged command includes --no-subtitles for replace mode with fonts
                    mock_log.assert_called()
                    log_call_args = mock_log.call_args
                    cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                    assert '--no-subtitles' in cmd_str
                    assert '--attach-file' in cmd_str

    def test_merge_video_with_subtitles_replace_mode_no_fonts(self, temp_dir, sample_video_file, sample_srt_file, mock_mkvmerge_with_fonts):
        """Test replace mode without external fonts - should still use --no-subtitles."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock encoding detection
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            # Capture the logging to extract the command in dry_run mode
            with patch('logging.info') as mock_log:
                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[],  # No external fonts
                    temp_dir=None,
                    dry_run=True,
                    mode="replace"
                )

                assert result is True

                # Should include --no-subtitles in replace mode (removes existing subs, preserves fonts)
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--no-subtitles' in cmd_str

    def test_merge_video_with_subtitles_append_mode(self, temp_dir, sample_video_file, sample_srt_file, fonts_dir, mock_subprocess_success):
        """Test append mode behavior."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock existing fonts detection
        with patch('submerge.get_existing_font_attachments') as mock_fonts:
            mock_fonts.return_value = ["ExistingFont.ttf"]

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[submerge.FontAttachment(
                        path=fonts_dir / "Arial.ttf",
                        mime_type="application/x-truetype-font"
                    )],
                    temp_dir=None,
                    dry_run=True,
                    mode="append"
                )

                assert result is True

                # Should NOT include --no-subtitles in append mode
                cmd_str = ' '.join(mock_run.call_args[0][0])
                assert '--no-subtitles' not in cmd_str

    def test_merge_video_with_subtitles_no_subtitles(self, temp_dir, sample_video_file):
        """Test merge behavior when no subtitle files are provided."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        result = submerge.merge_video_with_subtitles(
            video_path=video_path,
            subtitle_files=[],
            font_attachments=[],
            temp_dir=None,
            dry_run=True,
            mode="replace"
        )

        assert result is False

    def test_merge_video_with_subtitles_encoding_handling(self, temp_dir, sample_video_file, sample_srt_file, mock_encoding_iso8859):
        """Test that encoding handling is applied to subtitle files."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        # Mock encoding detection to return ISO-8859-1
        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "ISO-8859-1"

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
                # Verify charset parameter is included for ISO-8859-1 encoding
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--subtitle-charset' in cmd_str
            assert 'ISO-8859-1' in cmd_str

    def test_merge_video_with_subtitles_utf8_no_charset(self, temp_dir, sample_video_file, sample_srt_file, mock_encoding_utf8):
        """Test that no charset parameter is added for UTF-8 files."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = submerge.merge_video_with_subtitles(
                video_path=video_path,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=True,
                mode="replace"
            )

            assert result is True
            # Verify charset parameter is NOT included for UTF-8 encoding
            cmd_str = ' '.join(mock_run.call_args[0][0])
            assert '--subtitle-charset' not in cmd_str

    def test_merge_video_with_subtitles_multiple_subtitles(self, temp_dir, sample_video_file, complex_subtitle_setup):
        """Test merging multiple subtitle tracks."""
        video_path = temp_dir / "complex_video.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [
            submerge.SubtitleFile.from_path(
                complex_subtitle_setup['subtitles']['eng.srt'], "complex_video"
            ),
            submerge.SubtitleFile.from_path(
                complex_subtitle_setup['subtitles']['fr.srt'], "complex_video"
            ),
            submerge.SubtitleFile.from_path(
                complex_subtitle_setup['subtitles']['se.srt'], "complex_video"
            ),
        ]

        font_attachments = [
            submerge.FontAttachment(
                path=complex_subtitle_setup['fonts_dir'] / "Arial.ttf",
                mime_type="application/x-truetype-font"
            )
        ]

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

                # Verify multiple language codes are set
                mock_log.assert_called()
                log_call_args = mock_log.call_args
                cmd_str = log_call_args[0][1] if len(log_call_args[0]) > 1 else str(log_call_args[0][0])
                assert '--language 0:eng' in cmd_str
                assert '--language 0:fre' in cmd_str
                assert '--language 0:swe' in cmd_str

                # Verify track naming
                assert '--track-name 0:English' in cmd_str
                assert '--track-name 0:French' in cmd_str
                assert '--track-name 0:Swedish' in cmd_str

                # Verify default track flag (first subtitle should be default)
                assert '--default-track-flag 0:yes' in cmd_str
                assert '--default-track-flag 0:no' in cmd_str  # Subsequent ones should not be default

    def test_merge_video_with_subtitles_mkvmerge_failure(self, temp_dir):
        """Test handling of mkvmerge failure."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(
            temp_dir / "test.eng.srt", "test"
        )]
        (temp_dir / "test.eng.srt").write_text("test subtitle")

        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(
                    returncode=1,
                    stderr="mkvmerge error: something went wrong"
                )

                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[],
                    temp_dir=None,
                    dry_run=False,
                    mode="replace"
                )

                assert result is False

    def test_merge_video_with_subtitles_timeout(self, temp_dir):
        """Test handling of mkvmerge timeout."""
        video_path = temp_dir / "test.mkv"
        video_path.write_text("dummy video content")

        subtitle_files = [submerge.SubtitleFile.from_path(
            temp_dir / "test.eng.srt", "test"
        )]
        (temp_dir / "test.eng.srt").write_text("test subtitle")

        with patch('submerge.detect_subtitle_encoding') as mock_encoding:
            mock_encoding.return_value = "UTF-8"

            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired('mkvmerge', 300)

                result = submerge.merge_video_with_subtitles(
                    video_path=video_path,
                    subtitle_files=subtitle_files,
                    font_attachments=[],
                    temp_dir=None,
                    dry_run=False,
                    mode="replace"
                )

                assert result is False


class TestProcessSingleVideo:
    """Test the process_single_video function."""

    def test_process_single_video_success(self, temp_dir, sample_video_file, sample_srt_file, mock_subprocess_success):
        """Test successful single video processing."""
        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        with patch('submerge.merge_video_with_subtitles') as mock_merge:
            mock_merge.return_value = True

            success, message = submerge.process_single_video(
                video_path=sample_video_file,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=False,
                mode="replace"
            )

            assert success is True
            assert "Successfully merged" in message
            mock_merge.assert_called_once()

    def test_process_single_video_no_subtitles(self, sample_video_file):
        """Test processing when no subtitle files are found."""
        success, message = submerge.process_single_video(
            video_path=sample_video_file,
            subtitle_files=[],
            font_attachments=[],
            temp_dir=None,
            dry_run=False,
            mode="replace"
        )

        assert success is False
        assert "No matching subtitle files found" in message

    def test_process_single_video_merge_failure(self, temp_dir, sample_video_file, sample_srt_file, mock_subprocess_failure):
        """Test processing when merge fails."""
        subtitle_files = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

        with patch('submerge.merge_video_with_subtitles') as mock_merge:
            mock_merge.return_value = False

            success, message = submerge.process_single_video(
                video_path=sample_video_file,
                subtitle_files=subtitle_files,
                font_attachments=[],
                temp_dir=None,
                dry_run=False,
                mode="replace"
            )

            assert success is False
            assert "Failed to merge" in message


class TestProcessVideos:
    """Test the process_videos function for batch processing."""

    def test_process_videos_sequential(self, temp_dir, mock_subprocess_success):
        """Test sequential processing of multiple videos."""
        # Create multiple video files
        video1 = temp_dir / "video1.mkv"
        video2 = temp_dir / "video2.mkv"
        video1.write_text("dummy video 1")
        video2.write_text("dummy video 2")

        # Create subtitle files
        srt1 = temp_dir / "video1.eng.srt"
        srt2 = temp_dir / "video2.eng.srt"
        srt1.write_text("subtitle 1")
        srt2.write_text("subtitle 2")

        video_files = [video1, video2]

        with patch('submerge.find_subtitle_files') as mock_find:
            with patch('submerge.process_single_video') as mock_process:
                mock_find.side_effect = [
                    [submerge.SubtitleFile.from_path(srt1, "video1")],
                    [submerge.SubtitleFile.from_path(srt2, "video2")]
                ]
                mock_process.return_value = (True, "Success")

                stats = submerge.process_videos(
                    video_files=video_files,
                    font_attachments=[],
                    max_workers=1,
                    dry_run=False,
                    mode="replace"
                )

                assert stats.total_videos == 2
                assert stats.processed_videos == 2
                assert stats.skipped_videos == 0
                assert stats.failed_videos == 0

    def test_process_videos_parallel(self, temp_dir, mock_subprocess_success):
        """Test parallel processing of multiple videos."""
        # Create multiple video files
        video_files = []
        for i in range(3):
            video = temp_dir / f"video{i}.mkv"
            video.write_text(f"dummy video {i}")
            video_files.append(video)

        with patch('submerge.find_subtitle_files') as mock_find:
            with patch('submerge.process_single_video') as mock_process:
                # Create mock subtitle file so videos aren't skipped
                mock_subtitle = submerge.SubtitleFile(
                    path=temp_dir / "subtitle.eng.srt",
                    language_code="eng",
                    extension=".srt",
                    priority=1
                )
                mock_find.return_value = [mock_subtitle]
                mock_process.return_value = (True, "Success")

                stats = submerge.process_videos(
                    video_files=video_files,
                    font_attachments=[],
                    max_workers=3,
                    dry_run=False,
                    mode="replace"
                )

                assert stats.total_videos == 3
                assert mock_process.call_count == 3

    def test_process_videos_empty_list(self):
        """Test processing with no video files."""
        stats = submerge.process_videos(
            video_files=[],
            font_attachments=[],
            max_workers=1,
            dry_run=False,
            mode="replace"
        )

        assert stats.total_videos == 0
        assert stats.processed_videos == 0
        assert stats.skipped_videos == 0
        assert stats.failed_videos == 0

    def test_process_videos_with_skipped_files(self, temp_dir):
        """Test processing with files that have no matching subtitles."""
        video1 = temp_dir / "video1.mkv"
        video2 = temp_dir / "video2.mkv"
        video1.write_text("dummy video 1")
        video2.write_text("dummy video 2")

        video_files = [video1, video2]

        with patch('submerge.find_subtitle_files') as mock_find:
            mock_find.return_value = []  # No subtitles found for any video

            stats = submerge.process_videos(
                video_files=video_files,
                font_attachments=[],
                max_workers=1,
                dry_run=False,
                mode="replace"
            )

            assert stats.total_videos == 2
            assert stats.processed_videos == 0
            assert stats.skipped_videos == 2
            assert stats.failed_videos == 0

    def test_process_videos_with_failures(self, temp_dir):
        """Test processing with some failed merges."""
        video1 = temp_dir / "video1.mkv"
        video2 = temp_dir / "video2.mkv"
        video1.write_text("dummy video 1")
        video2.write_text("dummy video 2")

        video_files = [video1, video2]

        with patch('submerge.find_subtitle_files') as mock_find:
            with patch('submerge.process_single_video') as mock_process:
                # Create mock subtitle files for both videos
                mock_subtitle1 = submerge.SubtitleFile(
                    path=temp_dir / "video1.eng.srt",
                    language_code="eng",
                    extension=".srt",
                    priority=1
                )
                submerge.SubtitleFile(
                    path=temp_dir / "video2.eng.srt",
                    language_code="eng",
                    extension=".srt",
                    priority=1
                )
                mock_find.return_value = [mock_subtitle1]  # Same return for both videos
                mock_process.side_effect = [(True, "Success"), (False, "Failed")]

                stats = submerge.process_videos(
                    video_files=video_files,
                    font_attachments=[],
                    max_workers=1,
                    dry_run=False,
                    mode="replace"
                )

                assert stats.total_videos == 2
                assert stats.processed_videos == 1
                assert stats.skipped_videos == 0
                assert stats.failed_videos == 1