"""
CLI tests for submerge argument parsing and main function.

Tests command-line interface behavior including argument validation,
help messages, and integration with core functionality.
"""

import pytest
from unittest.mock import patch
import submerge


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_parse_args_basic(self):
        """Test basic argument parsing."""
        with patch('sys.argv', ['submerge', 'video.mkv']):
            args = submerge.parse_arguments()

            assert args.path == 'video.mkv'
            assert args.mode == 'replace'  # default value
            assert args.recursive is False
            assert args.dry_run is False
            assert args.parallel == 1  # default value

    def test_parse_args_with_mode(self):
        """Test argument parsing with mode specified."""
        with patch('sys.argv', ['submerge', '--mode', 'append', 'video.mkv']):
            args = submerge.parse_arguments()

            assert args.path == 'video.mkv'
            assert args.mode == 'append'

    def test_parse_args_directory_path(self):
        """Test argument parsing with directory path."""
        with patch('sys.argv', ['submerge', '/path/to/videos']):
            args = submerge.parse_arguments()

            assert args.path == '/path/to/videos'
            assert args.mode == 'replace'  # default value

    def test_parse_args_recursive(self):
        """Test recursive directory argument."""
        with patch('sys.argv', ['submerge', '--recursive', '/path/to/videos']):
            args = submerge.parse_arguments()

            assert args.recursive is True

    def test_parse_args_dry_run(self):
        """Test dry-run argument."""
        with patch('sys.argv', ['submerge', '--dry-run', 'video.mkv']):
            args = submerge.parse_arguments()

            assert args.dry_run is True

    def test_parse_args_parallel_workers(self):
        """Test parallel workers argument."""
        with patch('sys.argv', ['submerge', '-p', '4', 'video.mkv']):
            args = submerge.parse_arguments()

            assert args.parallel == 4

    def test_parse_args_verbose(self):
        """Test verbose argument."""
        with patch('sys.argv', ['submerge', '-v', 'video.mkv']):
            args = submerge.parse_arguments()

            assert args.verbose is True

    def test_parse_args_invalid_mode(self):
        """Test argument parsing with invalid mode."""
        with patch('sys.argv', ['submerge', '--mode', 'invalid', 'video.mkv']):
            with pytest.raises(SystemExit):
                submerge.parse_arguments()

    def test_parse_args_no_path(self):
        """Test argument parsing with no path (defaults to current directory)."""
        with patch('sys.argv', ['submerge']):  # Only script name, defaults to current directory
            args = submerge.parse_arguments()

            assert args.path == '.'  # Should default to current directory

    def test_parse_args_help(self):
        """Test help message generation."""
        with patch('sys.argv', ['submerge', '--help']):
            with pytest.raises(SystemExit):
                submerge.parse_arguments()

    def test_parse_args_version(self):
        """Test version argument."""
        with patch('sys.argv', ['submerge', '--version']):
            with pytest.raises(SystemExit):
                submerge.parse_arguments()


class TestMainFunction:
    """Test main function behavior."""

    @patch('submerge.process_videos')
    def test_main_single_video_success(self, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with single video processing success."""
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0  # Success exit code
                # For single video files, find_video_files is NOT called
                mock_process_videos.assert_called_once()

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_main_directory_processing(self, mock_find_videos, mock_process_videos, temp_dir):
        """Test main function with directory processing."""
        video_files = []
        for i in range(3):
            video = temp_dir / f"video{i}.mkv"
            video.write_text(f"dummy video {i}")
            video_files.append(video)

        mock_find_videos.return_value = video_files
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=3,
            processed_videos=2,
            skipped_videos=1,
            failed_videos=0,
            total_subtitle_tracks=4,
            fonts_embedded=2
        )

        with patch('sys.argv', ['submerge', str(temp_dir)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0  # Success exit code

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_main_with_failures(self, mock_find_videos, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with processing failures."""
        mock_find_videos.return_value = [sample_video_file]
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=1,
            processed_videos=0,
            skipped_videos=0,
            failed_videos=1,
            total_subtitle_tracks=0,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 1  # Failure exit code

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_main_append_mode(self, mock_find_videos, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with append mode."""
        mock_find_videos.return_value = [sample_video_file]
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '--mode', 'append', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0
                # Verify process_videos was called with mode="append"
                mock_process_videos.assert_called_once()
                call_args = mock_process_videos.call_args
                assert call_args.kwargs['mode'] == 'append'

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_main_dry_run(self, mock_find_videos, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with dry run."""
        mock_find_videos.return_value = [sample_video_file]
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '--dry-run', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0
                # Verify process_videos was called with dry_run=True
                call_args = mock_process_videos.call_args
                assert call_args.kwargs['dry_run'] is True

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_main_custom_max_workers(self, mock_find_videos, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with custom max_workers."""
        mock_find_videos.return_value = [sample_video_file]
        mock_process_videos.return_value = submerge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '-p', '2', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0
                # Verify process_videos was called with max_workers=2
                call_args = mock_process_videos.call_args
                assert call_args.kwargs['max_workers'] == 2

    def test_main_no_mkvmerge(self):
        """Test main function when mkvmerge is not available."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None

            with patch('sys.argv', ['submerge', 'video.mkv']):
                with patch('sys.exit') as mock_exit:
                    mock_exit.return_value = None  # Prevent actual exit

                    submerge.main()

                    # Should call sys.exit(1) when dependencies are missing
                    mock_exit.assert_called_once_with(1)

    def test_main_keyboard_interrupt(self, temp_dir, sample_video_file):
        """Test main function with keyboard interrupt."""
        with patch('submerge.process_videos') as mock_process:
            mock_process.side_effect = KeyboardInterrupt()

            with patch('sys.argv', ['submerge', str(sample_video_file)]):
                result = submerge.main()

                # Should return 1 when keyboard interrupt occurs
                assert result == 1

    def test_main_unexpected_error(self, temp_dir, sample_video_file):
        """Test main function with unexpected error."""
        with patch('submerge.process_videos') as mock_process:
            mock_process.side_effect = Exception("Unexpected error")

            with patch('sys.argv', ['submerge', str(sample_video_file)]):
                result = submerge.main()

                assert result == 1  # Failure exit code


class TestCliIntegration:
    """Test CLI integration scenarios."""

    @patch('submerge.process_single_video')
    def test_cli_single_file_workflow(self, mock_process_video, temp_dir, sample_video_file, sample_srt_file):
        """Test complete CLI workflow for single file processing."""
        mock_process_video.return_value = (True, "Successfully merged")

        with patch('submerge.find_subtitle_files') as mock_find:
            mock_find.return_value = [submerge.SubtitleFile.from_path(sample_srt_file, "test")]

            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                with patch('sys.argv', ['submerge', str(sample_video_file)]):
                    result = submerge.main()

                    assert result == 0

    @patch('submerge.process_single_video')
    def test_cli_directory_workflow(self, mock_process_video, temp_dir):
        """Test CLI workflow for directory processing."""
        # Create multiple video files
        video_files = []
        subtitle_files = []
        for i in range(3):
            video = temp_dir / f"video{i}.mkv"
            video.write_text(f"dummy video {i}")
            video_files.append(video)

            subtitle = temp_dir / f"video{i}.eng.srt"
            subtitle.write_text(f"subtitle {i}")
            subtitle_files.append(subtitle)

        mock_process_video.return_value = (True, "Successfully merged")

        with patch('submerge.find_video_files') as mock_find_videos:
            mock_find_videos.return_value = video_files

            with patch('submerge.find_subtitle_files') as mock_find_subs:
                mock_find_subs.return_value = [submerge.SubtitleFile.from_path(sub, "video") for sub in subtitle_files]

            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                with patch('sys.argv', ['submerge', str(temp_dir)]):
                    result = submerge.main()

                    assert result == 0
                    assert mock_process_video.call_count == 3

    def test_cli_no_matching_files(self, temp_dir):
        """Test CLI behavior when no matching files are found."""
        # Create directory with no video files
        text_file = temp_dir / "readme.txt"
        text_file.write_text("No videos here")

        with patch('submerge.find_video_files') as mock_find:
            mock_find.return_value = []

            with patch('sys.argv', ['submerge', str(temp_dir)]):
                result = submerge.main()

                assert result == 0  # No files is not an error

    def test_cli_mixed_file_types(self, temp_dir):
        """Test CLI behavior with mixed file types in directory."""
        # Create mixed file types
        video1 = temp_dir / "movie.mkv"
        video2 = temp_dir / "clip.webm"
        subtitle = temp_dir / "movie.eng.srt"
        text = temp_dir / "readme.txt"
        image = temp_dir / "cover.jpg"

        video1.write_text("dummy video")
        video2.write_text("dummy video")
        subtitle.write_text("subtitle")
        text.write_text("readme")
        image.write_bytes(b"image data")

        video_files = [video1, video2]

        with patch('submerge.find_video_files') as mock_find:
            mock_find.return_value = video_files

            with patch('submerge.find_subtitle_files') as mock_find_subs:
                mock_find_subs.return_value = []

            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                with patch('submerge.process_videos') as mock_process:
                    mock_process.return_value = submerge.ProcessingStats(total_videos=2, processed_videos=0, skipped_videos=2, failed_videos=0, total_subtitle_tracks=0, fonts_embedded=0)

                    with patch('sys.argv', ['submerge', str(temp_dir)]):
                        result = submerge.main()

                        assert result == 0
                        # Should only process video files, ignore others
                        mock_find.assert_called_once_with(temp_dir, False)


class TestModeSpecificCli:
    """Test mode-specific CLI behavior."""

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_cli_replace_mode_default(self, mock_find, mock_process, temp_dir, sample_video_file):
        """Test that replace mode is the default CLI behavior."""
        mock_find.return_value = [sample_video_file]
        mock_process.return_value = submerge.ProcessingStats(total_videos=1, processed_videos=1, skipped_videos=0, failed_videos=0, total_subtitle_tracks=1, fonts_embedded=0)

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0
                # Verify replace mode is used by default
                call_args = mock_process.call_args
                assert call_args.kwargs['mode'] == 'replace'

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_cli_append_mode_explicit(self, mock_find, mock_process, temp_dir, sample_video_file):
        """Test explicit append mode in CLI."""
        mock_find.return_value = [sample_video_file]
        mock_process.return_value = submerge.ProcessingStats(total_videos=1, processed_videos=1, skipped_videos=0, failed_videos=0, total_subtitle_tracks=1, fonts_embedded=0)

        with patch('sys.argv', ['submerge', '--mode', 'append', str(sample_video_file)]):
            with patch('submerge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                result = submerge.main()

                assert result == 0
                # Verify append mode is used
                call_args = mock_process.call_args
                assert call_args.kwargs['mode'] == 'append'

    @patch('submerge.process_videos')
    @patch('submerge.find_video_files')
    def test_cli_mode_case_insensitive(self, mock_find, mock_process, temp_dir, sample_video_file):
        """Test that mode argument is case sensitive (should fail with wrong case)."""
        mock_find.return_value = [sample_video_file]

        with patch('sys.argv', ['submerge', '--mode', 'APPEND', str(sample_video_file)]):
            with pytest.raises(SystemExit):
                submerge.main()