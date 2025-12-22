"""
CLI tests for submerge argument parsing and main function.

Tests command-line interface behavior including argument validation,
help messages, and integration with core functionality.
"""

import pytest
from unittest.mock import patch
from tests.test_submerge.conftest import sub_merge


class TestArgumentParsing:
    """Test command-line argument parsing."""

    def test_parse_args_basic(self):
        """Test basic argument parsing."""
        with patch('sys.argv', ['submerge', 'video.mkv']):
            args = sub_merge.parse_arguments()

            assert args.path == 'video.mkv'
            assert args.mode == 'replace'  # default value
            assert args.recursive is False
            assert args.dry_run is False
            assert args.parallel == 1  # default value

    def test_parse_args_with_mode(self):
        """Test argument parsing with mode specified."""
        with patch('sys.argv', ['submerge', '--mode', 'append', 'video.mkv']):
            args = sub_merge.parse_arguments()

            assert args.path == 'video.mkv'
            assert args.mode == 'append'

    def test_parse_args_directory_path(self):
        """Test argument parsing with directory path."""
        with patch('sys.argv', ['submerge', '/path/to/videos']):
            args = sub_merge.parse_arguments()

            assert args.path == '/path/to/videos'
            assert args.mode == 'replace'  # default value

    def test_parse_args_recursive(self):
        """Test recursive directory argument."""
        with patch('sys.argv', ['submerge', '--recursive', '/path/to/videos']):
            args = sub_merge.parse_arguments()

            assert args.recursive is True

    def test_parse_args_dry_run(self):
        """Test dry-run argument."""
        with patch('sys.argv', ['submerge', '--dry-run', 'video.mkv']):
            args = sub_merge.parse_arguments()

            assert args.dry_run is True

    def test_parse_args_parallel_workers(self):
        """Test parallel workers argument."""
        with patch('sys.argv', ['submerge', '-p', '4', 'video.mkv']):
            args = sub_merge.parse_arguments()

            assert args.parallel == 4

    def test_parse_args_verbose(self):
        """Test verbose argument."""
        with patch('sys.argv', ['submerge', '-v', 'video.mkv']):
            args = sub_merge.parse_arguments()

            assert args.verbose is True

    def test_parse_args_invalid_mode(self):
        """Test argument parsing with invalid mode."""
        with patch('sys.argv', ['submerge', '--mode', 'invalid', 'video.mkv']):
            with pytest.raises(SystemExit):
                sub_merge.parse_arguments()

    def test_parse_args_no_path(self):
        """Test argument parsing with no path (defaults to current directory)."""
        with patch('sys.argv', ['submerge']):  # Only script name, defaults to current directory
            args = sub_merge.parse_arguments()

            assert args.path == '.'  # Should default to current directory

    def test_parse_args_help(self):
        """Test help message generation."""
        with patch('sys.argv', ['submerge', '--help']):
            with pytest.raises(SystemExit):
                sub_merge.parse_arguments()

    def test_parse_args_version(self):
        """Test version argument."""
        with patch('sys.argv', ['submerge', '--version']):
            with pytest.raises(SystemExit):
                sub_merge.parse_arguments()


class TestMainFunction:
    """Test main function behavior."""

    @patch('sub_merge.SubtitleMergeProcessor.process_videos')
    def test_main_single_video_success(self, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with single video processing success."""
        mock_process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0  # Success exit code
            mock_process_videos.assert_called_once()

    @patch('sub_merge.SubtitleMergeProcessor.process_videos')
    @patch('sub_merge.find_video_files')
    def test_main_directory_processing(self, mock_find_videos, mock_process_videos, temp_dir):
        """Test main function with directory processing."""
        video_files = []
        for i in range(3):
            video = temp_dir / f"video{i}.mkv"
            video.write_text(f"dummy video {i}")
            video_files.append(video)

        mock_find_videos.return_value = video_files
        mock_process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=3,
            processed_videos=2,
            skipped_videos=1,
            failed_videos=0,
            total_subtitle_tracks=4,
            fonts_embedded=2
        )

        with patch('sys.argv', ['submerge', str(temp_dir)]):
            result = sub_merge.main()

            assert result == 0  # Success exit code

    @patch('sub_merge.SubtitleMergeProcessor.process_videos')
    def test_main_with_failures(self, mock_process_videos, temp_dir, sample_video_file):
        """Test main function with processing failures."""
        mock_process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1,
            processed_videos=0,
            skipped_videos=0,
            failed_videos=1,
            total_subtitle_tracks=0,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 1  # Failure exit code

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_main_append_mode(self, mock_processor_class, temp_dir, sample_video_file):
        """Test main function with append mode."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '--mode', 'append', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0
            # Verify processor was created with mode="append"
            mock_processor_class.assert_called_once_with(
                mode='append',
                verbose=False,
                dry_run=False
            )

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_main_dry_run(self, mock_processor_class, temp_dir, sample_video_file):
        """Test main function with dry run."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '--dry-run', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0
            # Verify processor was created with dry_run=True
            mock_processor_class.assert_called_once_with(
                mode='replace',
                verbose=False,
                dry_run=True
            )

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_main_custom_max_workers(self, mock_processor_class, temp_dir, sample_video_file):
        """Test main function with custom max_workers."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1,
            processed_videos=1,
            skipped_videos=0,
            failed_videos=0,
            total_subtitle_tracks=1,
            fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '-p', '2', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0
            # Verify process_videos was called with max_workers=2
            call_args = mock_processor.process_videos.call_args
            assert call_args.kwargs['max_workers'] == 2

    def test_main_no_mkvmerge(self):
        """Test main function when mkvmerge is not available."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None

            with patch('sys.argv', ['submerge', 'video.mkv']):
                with patch('sys.exit') as mock_exit:
                    mock_exit.return_value = None  # Prevent actual exit

                    sub_merge.main()

                    # Should call sys.exit(1) when dependencies are missing
                    mock_exit.assert_called_once_with(1)

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_main_keyboard_interrupt(self, mock_processor_class, temp_dir, sample_video_file):
        """Test main function with keyboard interrupt."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.side_effect = KeyboardInterrupt()

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            result = sub_merge.main()

            # Should return 1 when keyboard interrupt occurs
            assert result == 1

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_main_unexpected_error(self, mock_processor_class, temp_dir, sample_video_file):
        """Test main function with unexpected error."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.side_effect = Exception("Unexpected error")

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 1  # Failure exit code


class TestCliIntegration:
    """Test CLI integration scenarios."""

    @patch('sub_merge.process_single_video')
    def test_cli_single_file_workflow(self, mock_process_video, temp_dir, sample_video_file, sample_srt_file):
        """Test complete CLI workflow for single file processing."""
        mock_process_video.return_value = (True, "Successfully merged")

        with patch('sub_merge.find_subtitle_files') as mock_find:
            mock_find.return_value = [sub_merge.SubtitleFile.from_path(sample_srt_file, "test")]

            with patch('sub_merge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                with patch('sys.argv', ['submerge', str(sample_video_file)]):
                    result = sub_merge.main()

                    assert result == 0

    @patch('sub_merge.process_single_video')
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

        with patch('sub_merge.find_video_files') as mock_find_videos:
            mock_find_videos.return_value = video_files

            with patch('sub_merge.find_subtitle_files') as mock_find_subs:
                mock_find_subs.return_value = [sub_merge.SubtitleFile.from_path(sub, "video") for sub in subtitle_files]

            with patch('sub_merge.collect_font_attachments') as mock_fonts:
                mock_fonts.return_value = []

                with patch('sys.argv', ['submerge', str(temp_dir)]):
                    result = sub_merge.main()

                    assert result == 0
                    assert mock_process_video.call_count == 3

    def test_cli_no_matching_files(self, temp_dir):
        """Test CLI behavior when no matching files are found."""
        # Create directory with no video files
        text_file = temp_dir / "readme.txt"
        text_file.write_text("No videos here")

        with patch('sub_merge.find_video_files') as mock_find:
            mock_find.return_value = []

            with patch('sys.argv', ['submerge', str(temp_dir)]):
                result = sub_merge.main()

                assert result == 0  # No files is not an error

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_cli_mixed_file_types(self, mock_processor_class, temp_dir):
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

        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=2, processed_videos=0, skipped_videos=2,
            failed_videos=0, total_subtitle_tracks=0, fonts_embedded=0
        )

        with patch('sub_merge.find_video_files') as mock_find:
            mock_find.return_value = video_files

            with patch('sys.argv', ['submerge', str(temp_dir)]):
                result = sub_merge.main()

                assert result == 0
                # Should only process video files, ignore others
                mock_find.assert_called_once_with(temp_dir, False)


class TestModeSpecificCli:
    """Test mode-specific CLI behavior."""

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_cli_replace_mode_default(self, mock_processor_class, temp_dir, sample_video_file):
        """Test that replace mode is the default CLI behavior."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1, processed_videos=1, skipped_videos=0,
            failed_videos=0, total_subtitle_tracks=1, fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0
            # Verify replace mode is used by default
            mock_processor_class.assert_called_once_with(
                mode='replace',
                verbose=False,
                dry_run=False
            )

    @patch('sub_merge.SubtitleMergeProcessor')
    def test_cli_append_mode_explicit(self, mock_processor_class, temp_dir, sample_video_file):
        """Test explicit append mode in CLI."""
        mock_processor = mock_processor_class.return_value
        mock_processor.process_videos.return_value = sub_merge.ProcessingStats(
            total_videos=1, processed_videos=1, skipped_videos=0,
            failed_videos=0, total_subtitle_tracks=1, fonts_embedded=0
        )

        with patch('sys.argv', ['submerge', '--mode', 'append', str(sample_video_file)]):
            result = sub_merge.main()

            assert result == 0
            # Verify append mode is used
            mock_processor_class.assert_called_once_with(
                mode='append',
                verbose=False,
                dry_run=False
            )

    def test_cli_mode_case_insensitive(self, temp_dir, sample_video_file):
        """Test that mode argument is case sensitive (should fail with wrong case)."""
        with patch('sys.argv', ['submerge', '--mode', 'APPEND', str(sample_video_file)]):
            with pytest.raises(SystemExit):
                sub_merge.main()