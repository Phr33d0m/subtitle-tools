"""
Core functionality tests for subextract.

Tests subtitle extraction from MKV files, language code handling,
track identification, and file processing logic.
"""

import pytest
import json
import subprocess
import sys
from unittest.mock import patch
import subextract
from dataclasses import asdict


class TestSubTrack:
    """Test SubTrack dataclass."""

    def test_subtrack_creation(self):
        """Test creating a SubTrack instance."""
        track = subextract.SubTrack(
            tid=1,
            codec_id="S_TEXT/ASS",
            lang3="eng",
            lang_ietf="en",
            track_name="English"
        )

        assert track.tid == 1
        assert track.codec_id == "S_TEXT/ASS"
        assert track.lang3 == "eng"
        assert track.lang_ietf == "en"
        assert track.track_name == "English"

    def test_subtrack_to_dict(self):
        """Test converting SubTrack to dictionary."""
        track = subextract.SubTrack(
            tid=2,
            codec_id="S_TEXT/UTF8",
            lang3="jpn",
            lang_ietf="ja",
            track_name="Japanese"
        )

        expected = {
            'tid': 2,
            'codec_id': 'S_TEXT/UTF8',
            'lang3': 'jpn',
            'lang_ietf': 'ja',
            'track_name': 'Japanese'
        }

        assert asdict(track) == expected

    def test_subtrack_optional_fields(self):
        """Test SubTrack with optional fields as None."""
        track = subextract.SubTrack(
            tid=3,
            codec_id="S_TEXT/ASS",
            lang3=None,
            lang_ietf=None,
            track_name=None
        )

        assert track.tid == 3
        assert track.codec_id == "S_TEXT/ASS"
        assert track.lang3 is None
        assert track.lang_ietf is None
        assert track.track_name is None


class TestToolDependency:
    """Test external tool dependency checking."""

    def test_need_tool_available(self):
        """Test need() function when tool is available."""
        with patch('shutil.which', return_value='/usr/bin/mkvmerge'):
            # Should not raise an exception
            subextract.need('mkvmerge')

    def test_need_tool_not_available(self):
        """Test need() function when tool is not available."""
        with patch('shutil.which', return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                subextract.need('nonexistent_tool')

            assert exc_info.value.code == 1

    def test_need_multiple_tools(self):
        """Test need() function with multiple tool checks."""
        with patch('shutil.which', return_value='/usr/bin/mkvtool'):
            subextract.need('mkvmerge')
            subextract.need('mkvextract')


class TestCodecExtension:
    """Test codec extension mapping."""

    def test_codec_ext_ass(self):
        """Test extension for ASS codec."""
        assert subextract.codec_ext("S_TEXT/ASS") == "ass"

    def test_codec_ext_utf8(self):
        """Test extension for UTF8 codec."""
        assert subextract.codec_ext("S_TEXT/UTF8") == "srt"

    def test_codec_ext_vobsub(self):
        """Test extension for VobSub codec."""
        assert subextract.codec_ext("S_VOBSUB") == "sub"

    def test_codec_ext_pgs(self):
        """Test extension for PGS codec."""
        assert subextract.codec_ext("S_HDMV/PGS") == "sup"

    def test_codec_ext_unknown(self):
        """Test extension for unknown codec."""
        assert subextract.codec_ext("UNKNOWN_CODEC") == "sub"

    def test_codec_ext_case_insensitive(self):
        """Test case insensitive codec handling."""
        assert subextract.codec_ext("s_text/ass") == "ass"
        assert subextract.codec_ext("S_ASS") == "ass"
        assert subextract.codec_ext("s_ssa") == "ssa"


class TestSlugFunction:
    """Test slug function for filename sanitization."""

    def test_slug_basic(self):
        """Test basic slug functionality."""
        assert subextract.slug("Simple Name") == "simple-name"

    def test_slug_with_spaces(self):
        """Test slug with multiple spaces."""
        assert subextract.slug("Name   with   spaces") == "name-with-spaces"

    def test_slug_with_special_characters(self):
        """Test slug with special characters."""
        assert subextract.slug("Name/with\\special:*chars") == "name-with-special-chars"

    def test_slug_empty_string(self):
        """Test slug with empty string."""
        assert subextract.slug("") == ""

    def test_slug_unicode_characters(self):
        """Test slug with unicode characters."""
        # Unicode accented characters get replaced with dashes
        assert subextract.slug("Café naïve") == "caf-na-ve"

    def test_slug_with_dashes(self):
        """Test slug with existing dashes."""
        assert subextract.slug("name-with-dashes") == "name-with-dashes"

    def test_slug_already_lowercase(self):
        """Test slug with already lowercase text."""
        assert subextract.slug("lowercase text") == "lowercase-text"

    def test_slug_uppercase(self):
        """Test slug with uppercase text."""
        assert subextract.slug("UPPERCASE TEXT") == "uppercase-text"


class TestLanguageCodeNormalization:
    """Test language code normalization."""

    def test_lang_code_3_valid_3_letter(self):
        """Test valid 3-letter language codes."""
        assert subextract.lang_code_3("eng") == "eng"
        assert subextract.lang_code_3("jpn") == "jpn"
        assert subextract.lang_code_3("chi") == "chi"

    def test_lang_code_3_case_insensitive(self):
        """Test case insensitive 3-letter language codes."""
        assert subextract.lang_code_3("ENG") == "eng"
        assert subextract.lang_code_3("JPN") == "jpn"
        assert subextract.lang_code_3("CHI") == "chi"

    def test_lang_code_3_2_letter_codes(self):
        """Test that 2-letter codes return 'und' (function only handles 3-letter codes)."""
        assert subextract.lang_code_3("en") == "und"
        assert subextract.lang_code_3("ja") == "und"
        assert subextract.lang_code_3("zh") == "und"

    def test_lang_code_3_unknown(self):
        """Test unknown language codes."""
        # If it's 3 letters, it returns as-is even if unknown
        assert subextract.lang_code_3("xyz") == "xyz"
        assert subextract.lang_code_3("xx") == "und"  # 2 letters -> und
        assert subextract.lang_code_3("") == "und"

    def test_lang_code_3_none_input(self):
        """Test None input."""
        assert subextract.lang_code_3(None) == "und"

    def test_lang_code_3_edge_cases(self):
        """Test edge cases."""
        assert subextract.lang_code_3("en ") == "und"  # with space
        assert subextract.lang_code_3("engg") == "und"  # too long
        assert subextract.lang_code_3("jp") == "und"   # too short


class TestJsonIdentify:
    """Test JSON track identification functionality."""

    def test_run_json_identify_success(self, temp_dir):
        """Test successful JSON identification."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "tracks": [
                {
                    "id": 0,
                    "type": "video",
                    "codec": "h264"
                },
                {
                    "id": 1,
                    "type": "subtitles",
                    "codec": "S_TEXT/ASS",
                    "properties": {
                        "language": "eng",
                        "language_ietf": "en",
                        "track_name": "English Subtitles"
                    }
                },
                {
                    "id": 2,
                    "type": "subtitles",
                    "codec": "S_TEXT/UTF8",
                    "properties": {
                        "language": "jpn",
                        "language_ietf": "ja"
                    }
                }
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            result = subextract.run_json_identify(mkv_file)

            assert isinstance(result, dict)
            assert "tracks" in result
            assert len(result["tracks"]) == 3

            # Check first subtitle track
            subtitle_track = result["tracks"][1]
            assert subtitle_track["id"] == 1
            assert subtitle_track["type"] == "subtitles"
            assert subtitle_track["codec"] == "S_TEXT/ASS"

    def test_run_json_identify_no_subtitles(self, temp_dir):
        """Test JSON identification with no subtitle tracks."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "tracks": [
                {
                    "id": 0,
                    "type": "video",
                    "codec": "h264"
                },
                {
                    "id": 1,
                    "type": "audio",
                    "codec": "aac"
                }
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            result = subextract.run_json_identify(mkv_file)

            assert isinstance(result, dict)
            assert len([t for t in result["tracks"] if t["type"] == "subtitles"]) == 0

    def test_run_json_identify_subprocess_failure(self, temp_dir):
        """Test JSON identification when subprocess fails."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subprocess.run') as mock_run:
            error = subprocess.CalledProcessError(1, 'mkvmerge')
            error.stderr = "mkvmerge failed"
            mock_run.side_effect = error

            with pytest.raises(RuntimeError, match="Command failed"):
                subextract.run_json_identify(mkv_file)

    def test_run_json_identify_malformed_json(self, temp_dir):
        """Test JSON identification with malformed JSON output."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "invalid json output"

            with pytest.raises(RuntimeError, match="Failed to parse JSON"):
                subextract.run_json_identify(mkv_file)

    def test_run_json_identify_missing_properties(self, temp_dir):
        """Test JSON identification with missing track properties."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"fake mkv content")

        mock_json_output = {
            "tracks": [
                {
                    "id": 1,
                    "type": "subtitles",
                    "codec": "S_TEXT/ASS"
                    # Missing properties section
                }
            ]
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(mock_json_output)

            result = subextract.run_json_identify(mkv_file)

            assert isinstance(result, dict)
            subtitle_track = result["tracks"][0]
            assert subtitle_track["id"] == 1
            assert subtitle_track["type"] == "subtitles"
            assert "properties" not in subtitle_track


class TestMKVFileIteration:
    """Test MKV file iteration in directories."""

    def test_iter_mkvs_in_dir_lowercase(self, temp_dir):
        """Test iteration with lowercase .mkv files."""
        # Create test files
        (temp_dir / "movie1.mkv").write_bytes(b"content1")
        (temp_dir / "movie2.mkv").write_bytes(b"content2")
        (temp_dir / "movie3.mkv").write_bytes(b"content3")

        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        assert len(files) == 3
        assert all(f.suffix == ".mkv" for f in files)
        assert [f.name for f in files] == ["movie1.mkv", "movie2.mkv", "movie3.mkv"]

    def test_iter_mkvs_in_dir_uppercase(self, temp_dir):
        """Test iteration with uppercase .MKV files."""
        # Create test files
        (temp_dir / "MOVIE1.MKV").write_bytes(b"content1")
        (temp_dir / "MOVIE2.MKV").write_bytes(b"content2")

        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        assert len(files) == 2
        assert all(f.suffix == ".MKV" for f in files)
        assert [f.name for f in files] == ["MOVIE1.MKV", "MOVIE2.MKV"]

    def test_iter_mkvs_in_dir_mixed_case(self, temp_dir):
        """Test iteration with mixed case MKV files."""
        # Create test files - only exact .mkv and .MKV matches work
        (temp_dir / "lower.mkv").write_bytes(b"content1")
        (temp_dir / "UPPER.MKV").write_bytes(b"content2")
        (temp_dir / "Mixed.Mkv").write_bytes(b"content3")

        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        # Function only searches for .mkv and .MKV, not mixed case
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "lower.mkv" in file_names
        assert "UPPER.MKV" in file_names
        assert "Mixed.Mkv" not in file_names  # Should not be found

    def test_iter_mkvs_in_dir_sorted(self, temp_dir):
        """Test that iteration returns files in sorted order."""
        # Create files out of alphabetical order
        (temp_dir / "z_movie.mkv").write_bytes(b"content1")
        (temp_dir / "a_movie.mkv").write_bytes(b"content2")
        (temp_dir / "m_movie.mkv").write_bytes(b"content3")

        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        assert [f.name for f in files] == ["a_movie.mkv", "m_movie.mkv", "z_movie.mkv"]

    def test_iter_mkvs_in_dir_no_mkv_files(self, temp_dir):
        """Test iteration with no MKV files."""
        # Create non-MKV files
        (temp_dir / "movie.mp4").write_bytes(b"content1")
        (temp_dir / "subtitle.srt").write_bytes(b"content2")
        (temp_dir / "document.txt").write_bytes(b"content3")

        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        assert len(files) == 0

    def test_iter_mkvs_in_dir_empty_directory(self, temp_dir):
        """Test iteration in empty directory."""
        files = list(subextract.iter_mkvs_in_dir(temp_dir))

        assert len(files) == 0


class TestExtractionProcess:
    """Test subtitle extraction process."""

    @patch('subextract.run_json_identify')
    @patch('subprocess.run')
    def test_extract_subs_for_file_success(self, mock_subprocess, mock_identify, temp_dir):
        """Test successful subtitle extraction."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock JSON identification with subtitle tracks
        mock_json = {
            "tracks": [
                {
                    "id": 1,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "language_ietf": "en",
                        "track_name": "English"
                    }
                }
            ]
        }
        mock_identify.return_value = mock_json

        # Mock successful extraction
        mock_subprocess.return_value.returncode = 0

        success, message = subextract.extract_subs_for_file(mkv_file, outdir)

        assert success
        assert "Successfully extracted" in message
        assert "test.mkv" in message
        mock_identify.assert_called_once_with(mkv_file)

    @patch('subextract.run_json_identify')
    def test_extract_subs_for_file_no_subtitles(self, mock_identify, temp_dir):
        """Test extraction when no subtitle tracks found."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock JSON with no subtitle tracks
        mock_json = {
            "tracks": [
                {
                    "id": 0,
                    "type": "video"
                }
            ]
        }
        mock_identify.return_value = mock_json

        success, message = subextract.extract_subs_for_file(mkv_file, outdir)

        assert success
        assert "No subtitle tracks" in message
        mock_identify.assert_called_once_with(mkv_file)

    @patch('subextract.run_json_identify')
    @patch('subprocess.run')
    def test_extract_subs_for_file_extraction_failure(self, mock_subprocess, mock_identify, temp_dir):
        """Test extraction when mkvextract fails."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock JSON identification with subtitle tracks
        mock_json = {
            "tracks": [
                {
                    "id": 1,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "language_ietf": "en"
                    }
                }
            ]
        }
        mock_identify.return_value = mock_json

        # Mock failed extraction using CalledProcessError
        error = subprocess.CalledProcessError(1, 'mkvextract')
        error.stderr = "Extraction failed"
        mock_subprocess.side_effect = error

        with patch('builtins.print'):
            success, message = subextract.extract_subs_for_file(mkv_file, outdir)

            assert not success
            assert "mkvextract failed" in message

    @patch('subextract.run_json_identify')
    @patch('subprocess.run')
    def test_extract_subs_for_file_filename_collision(self, mock_subprocess, mock_identify, temp_dir):
        """Test extraction with filename collision handling."""
        mkv_file = temp_dir / "test.mkv"
        mkv_file.write_bytes(b"mkv content")
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock JSON identification with subtitle tracks
        mock_json = {
            "tracks": [
                {
                    "id": 1,
                    "type": "subtitles",
                    "properties": {
                        "language": "eng",
                        "language_ietf": "en"
                    }
                }
            ]
        }
        mock_identify.return_value = mock_json

        # Mock successful extraction
        mock_subprocess.return_value.returncode = 0

        # Pre-existing file to cause collision
        existing_file = outdir / "test.eng.ass"
        existing_file.write_text("existing content")

        success, message = subextract.extract_subs_for_file(mkv_file, outdir)

        assert success
        assert "Successfully extracted" in message


class TestBatchProcessing:
    """Test batch processing of multiple MKV files."""

    @patch('subextract.extract_subs_for_file')
    def test_process_mkvs_sequential(self, mock_extract, temp_dir):
        """Test sequential processing of multiple files."""
        mkv_files = [
            temp_dir / "movie1.mkv",
            temp_dir / "movie2.mkv",
            temp_dir / "movie3.mkv"
        ]
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock successful extraction
        mock_extract.return_value = (True, "Success")

        successful, failed = subextract.process_mkvs(mkv_files, outdir, max_workers=1)

        assert successful == 3
        assert failed == 0
        assert mock_extract.call_count == 3

    @patch('subextract.extract_subs_for_file')
    def test_process_mkvs_with_failures(self, mock_extract, temp_dir):
        """Test processing with some failures."""
        mkv_files = [
            temp_dir / "movie1.mkv",
            temp_dir / "movie2.mkv",
            temp_dir / "movie3.mkv"
        ]
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock mixed success/failure
        mock_extract.side_effect = [
            (True, "Success"),
            (False, "Failed"),
            (True, "Success")
        ]

        successful, failed = subextract.process_mkvs(mkv_files, outdir, max_workers=1)

        assert successful == 2
        assert failed == 1
        assert mock_extract.call_count == 3

    @patch('subextract.extract_subs_for_file')
    def test_process_mkvs_parallel(self, mock_extract, temp_dir):
        """Test parallel processing of multiple files."""
        mkv_files = [
            temp_dir / "movie1.mkv",
            temp_dir / "movie2.mkv",
            temp_dir / "movie3.mkv",
            temp_dir / "movie4.mkv"
        ]
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock successful extraction
        mock_extract.return_value = (True, "Success")

        successful, failed = subextract.process_mkvs(mkv_files, outdir, max_workers=4)

        assert successful == 4
        assert failed == 0
        assert mock_extract.call_count == 4

    @patch('subextract.extract_subs_for_file')
    def test_process_mkvs_exception_handling(self, mock_extract, temp_dir):
        """Test handling of exceptions during processing."""
        mkv_files = [
            temp_dir / "movie1.mkv",
            temp_dir / "movie2.mkv"
        ]
        outdir = temp_dir / "output"
        outdir.mkdir()

        # Mock first call succeeds, second raises exception
        def mock_side_effect(mkv_file, outdir_path):
            if mkv_file.name == "movie1.mkv":
                return (True, "Success")
            else:
                raise Exception("Processing error")

        mock_extract.side_effect = mock_side_effect

        with patch('builtins.print') as mock_print:
            successful, failed = subextract.process_mkvs(mkv_files, outdir, max_workers=2)

            assert successful == 1
            assert failed == 1
            # Check that error was printed to stderr
            error_calls = [call for call in mock_print.call_args_list if call.kwargs.get('file') == sys.stderr]
            assert len(error_calls) >= 1
            assert any("Processing error" in str(call) for call in error_calls)

    @patch('subextract.extract_subs_for_file')
    def test_process_mkvs_empty_list(self, mock_extract, temp_dir):
        """Test processing empty file list."""
        mkv_files = []
        outdir = temp_dir / "output"
        outdir.mkdir()

        successful, failed = subextract.process_mkvs(mkv_files, outdir, max_workers=1)

        assert successful == 0
        assert failed == 0
        mock_extract.assert_not_called()