# Shared Test Infrastructure

This directory contains shared test fixtures, utilities, and configuration that can be used across all subtitle processing tools.

## Structure

- `fixtures.py`: Common pytest fixtures for temporary directories, mock files, and test scenarios
- `utils.py`: Shared test utilities and helper classes
- `conftest.py`: Global pytest configuration and custom markers

## Available Fixtures

### Core Fixtures
- `temp_dir`: Creates a temporary directory for testing
- `sample_video_file`: Creates a sample video file
- `sample_srt_file`: Creates a sample SRT subtitle file
- `sample_ass_file`: Creates a sample ASS subtitle file
- `fonts_dir`: Creates a Fonts directory with sample fonts
- `complex_subtitle_setup`: Creates a complex setup with multiple subtitles and fonts

### Mock Fixtures
- `mock_subprocess_success`: Mock successful subprocess calls
- `mock_subprocess_failure`: Mock failed subprocess calls
- `mock_encoding_utf8`: Mock UTF-8 encoding detection
- `mock_encoding_iso8859`: Mock ISO-8859-1 encoding detection
- `mock_encoding_unknown`: Mock unknown encoding detection

## Usage

To use these fixtures in your test files:

```python
# Import from shared fixtures
from tests.shared.fixtures import (
    temp_dir,
    sample_video_file,
    mock_subprocess_success,
)

class TestMyTool:
    def test_basic_functionality(self, temp_dir, sample_video_file):
        # Your test code here
        pass
```

## Adding New Fixtures

When adding new fixtures that could be useful across multiple tools, add them to `fixtures.py` in this directory. For tool-specific fixtures, add them to the tool's `conftest.py` file.