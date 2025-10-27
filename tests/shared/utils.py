"""
Common test utilities and helper functions.

Provides reusable utility functions for testing across different tools.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock


def create_mock_video_file(path: Path, content: str = "dummy video") -> Path:
    """Create a mock video file with the specified content."""
    path.write_text(content)
    return path


def create_mock_subtitle_file(path: Path, language_code: str, content: str) -> Path:
    """Create a mock subtitle file with the specified language and content."""
    if path.suffix.lower() == '.srt':
        subtitle_content = (
            f"1\n"
            f"00:00:01,000 --> 00:00:02,000\n"
            f"{content}\n"
        )
    elif path.suffix.lower() == '.ass':
        subtitle_content = (
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,0,0,1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            f"Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,{content}\n"
        )
    else:
        raise ValueError(f"Unsupported subtitle format: {path.suffix}")

    path.write_text(subtitle_content)
    return path


def create_font_file(path: Path, content: bytes = b"dummy font") -> Path:
    """Create a mock font file with the specified content."""
    path.write_bytes(content)
    return path


def mock_subprocess_run(returncode: int = 0, stdout: str = "", stderr: str = "") -> Mock:
    """Create a mock subprocess.run object."""
    mock = Mock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


def assert_command_contains(mock_run: Mock, *expected_parts: str) -> None:
    """Assert that a subprocess command contains all expected parts."""
    if mock_run.called:
        call_args = mock_run.call_args[0][0] if mock_run.call_args else []
        command_str = ' '.join(call_args)
        for part in expected_parts:
            assert part in command_str, f"Expected '{part}' in command: {command_str}"
    else:
        raise AssertionError("subprocess.run was not called")


def create_temp_file_with_content(content: str, suffix: str = ".txt") -> Path:
    """Create a temporary file with specified content and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with open(fd, 'w') as f:
            f.write(content)
        return Path(path)
    except:
        # Clean up on error
        Path(path).unlink(missing_ok=True)
        raise


def get_supported_video_extensions() -> List[str]:
    """Get list of supported video file extensions."""
    return ['.mkv', '.mp4', '.webm']


def get_supported_subtitle_extensions() -> List[str]:
    """Get list of supported subtitle file extensions."""
    return ['.srt', '.ass', '.ssa', '.sub']


def get_supported_font_extensions() -> List[str]:
    """Get list of supported font file extensions."""
    return ['.ttf', '.otf', '.ttc', '.woff', '.woff2']


def create_mock_file_with_mime_type(path: Path, mime_type: str, content: str = "") -> Path:
    """Create a mock file and return the file command would return the specified MIME type."""
    path.write_text(content)
    return path


def mock_file_command(output: str, returncode: int = 0) -> Mock:
    """Mock the file command to return specific output."""
    mock = Mock()
    mock.stdout = output
    mock.returncode = returncode
    return mock


class TestHelper:
    """Helper class for common test operations."""

    @staticmethod
    def assert_logs_contain(mock_log, *expected_messages: str):
        """Assert that log messages contain expected text."""
        if mock_log.called:
            for call in mock_log.call_args_list:
                args = call[0]
                if args:
                    log_message = ' '.join(str(arg) for arg in args)
                    for message in expected_messages:
                        assert message in log_message, f"Expected '{message}' in logs: {log_message}"
        else:
            raise AssertionError("No log calls were made")

    @staticmethod
    def extract_command_from_log(mock_log) -> Optional[str]:
        """Extract command string from log calls."""
        if not mock_log.called:
            return None

        for call in mock_log.call_args_list:
            args = call[0]
            if len(args) >= 2 and 'DRY RUN: Would execute:' in str(args[0]):
                return str(args[1])
        return None

    @staticmethod
    def assert_command_in_log(mock_log, *expected_parts: str):
        """Assert that a command in logs contains expected parts."""
        cmd = TestHelper.extract_command_from_log(mock_log)
        if cmd is None:
            raise AssertionError("No command found in logs")

        for part in expected_parts:
            assert part in cmd, f"Expected '{part}' in command: {cmd}"