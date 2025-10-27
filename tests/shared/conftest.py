"""
Shared pytest configuration for all subtitle processing tools.

This module provides common configuration and markers that apply
to all test suites in the project.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Global configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "submerge: Tests for submerge.py subtitle merging tool"
    )
    config.addinivalue_line(
        "markers",
        "ocrp: Tests for ocrp.py OCR processing tool"
    )
    config.addinivalue_line(
        "markers",
        "subextract: Tests for subextract.py subtitle extraction tool"
    )
    config.addinivalue_line(
        "markers",
        "subattachextract: Tests for subattachextract.py attachment extraction tool"
    )
    config.addinivalue_line(
        "markers",
        "subtimefix: Tests for subtimefix.py timestamp shifting tool"
    )
    config.addinivalue_line(
        "markers",
        "ass_qafix: Tests for ass_qafix.py quality fix tool"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "test_submerge/" in str(item.fspath):
            item.add_marker(pytest.mark.submerge)
        elif "test_ocrp/" in str(item.fspath):
            item.add_marker(pytest.mark.ocrp)
        elif "test_subextract/" in str(item.fspath):
            item.add_marker(pytest.mark.subextract)
        elif "test_subattachextract/" in str(item.fspath):
            item.add_marker(pytest.mark.subattachextract)
        elif "test_subtimefix/" in str(item.fspath):
            item.add_marker(pytest.mark.subtimefix)
        elif "test_ass_qafix/" in str(item.fspath):
            item.add_marker(pytest.mark.ass_qafix)