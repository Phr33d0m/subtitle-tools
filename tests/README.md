# Test Suite for Subtitle Processing Tools

This directory contains comprehensive test suites for all subtitle processing tools in the project.

## Structure

```
tests/
├── shared/                     # Shared test infrastructure
│   ├── fixtures.py            # Common pytest fixtures
│   ├── utils.py               # Shared test utilities
│   ├── conftest.py            # Global pytest configuration
│   └── README.md              # This file
├── test_submerge/             # Tests for submerge.py (subtitle merging)
│   ├── test_cli.py            # CLI interface tests
│   ├── test_core.py           # Core functionality tests
│   ├── test_integration.py    # Integration tests
│   ├── test_modes.py          # Mode-specific behavior tests
│   ├── test_scenarios.py      # Real-world scenario tests
│   ├── test_units.py          # Unit tests
│   ├── conftest.py            # Submerge-specific fixtures
│   └── __init__.py
├── test_ocrp/                 # Tests for ocrp.py (OCR processing) [TEMPLATE]
│   ├── test_cli.py            # CLI interface tests (template)
│   ├── test_core.py           # Core functionality tests (template)
│   ├── conftest.py            # OCRP-specific fixtures (template)
│   └── __init__.py
├── test_subextract/           # Tests for subextract.py (subtitle extraction) [TEMPLATE]
│   ├── test_cli.py            # CLI interface tests (template)
│   ├── test_core.py           # Core functionality tests (template)
│   ├── conftest.py            # Subextract-specific fixtures (template)
│   └── __init__.py
├── test_subattachextract/     # Tests for subattachextract.py (attachment extraction) [TEMPLATE]
│   ├── test_cli.py            # CLI interface tests (template)
│   ├── conftest.py            # Subattachextract-specific fixtures (template)
│   └── __init__.py
├── test_subtimefix/           # Tests for subtimefix.py (timestamp shifting) [TEMPLATE]
│   ├── test_cli.py            # CLI interface tests (template)
│   ├── conftest.py            # Subtimefix-specific fixtures (template)
│   └── __init__.py
├── test_ass_qafix/            # Tests for ass_qafix.py (quality fixing) [TEMPLATE]
│   ├── test_cli.py            # CLI interface tests (template)
│   ├── conftest.py            # ASS QA Fix-specific fixtures (template)
│   └── __init__.py
└── conftest.py                # Top-level conftest with additional shared fixtures
```

## Running Tests

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run Specific Tool Tests

```bash
python -m pytest tests/test_submerge/ -v
python -m pytest tests/test_ocrp/ -v
```

### Run Specific Test Categories

```bash
# Only unit tests
python -m pytest tests/ -m unit -v

# Only integration tests
python -m pytest tests/ -m integration -v

# Only CLI tests
python -m pytest tests/ -m cli -v

# Only submerge tests
python -m pytest tests/ -m submerge -v
```

### Generate Coverage Report

```bash
python -m pytest tests/ --cov=tests/ --cov-report=html
```

## Test Status

- ✅ **submerge.py**: Complete test suite (146 tests passing)
- 📋 **ocrp.py**: Test infrastructure ready (conftest.py and **init**.py available)
- 📋 **subextract.py**: Test infrastructure ready (conftest.py and **init**.py available)
- 📋 **subattachextract.py**: Test infrastructure ready (conftest.py and **init**.py available)
- 📋 **subtimefix.py**: Test infrastructure ready (conftest.py and **init**.py available)
- 📋 **ass_qafix.py**: Test infrastructure ready (conftest.py and **init**.py available)

## Test Infrastructure

The project has established test infrastructure for all tools:

1. **Shared Infrastructure**: Common fixtures and utilities in `tests.shared/`
2. **Tool-Specific Setup**: Each tool has its own directory with conftest.py and **init**.py
3. **Proven Patterns**: The submerge test suite (146 tests) provides a complete example

### Next Steps for Tool Implementation

When implementing tests for the remaining tools:

1. Follow the patterns established in `tests/test_submerge/`
2. Use the shared fixtures from `tests.shared.fixtures`
3. Adapt the test structure to match each tool's actual function names
4. Focus on CLI parsing, core functionality, error handling, and integration scenarios

## Adding New Tests

When adding tests for a new tool:

1. Create a new directory: `tests/test_toolname/`
2. Add `__init__.py` with tool description
3. Add `conftest.py` with tool-specific fixtures
4. Create test files following the established patterns:
   - `test_cli.py` for command-line interface
   - `test_core.py` for core functionality
   - `test_integration.py` for end-to-end scenarios
5. Import shared fixtures from `tests.shared.fixtures`
6. Follow the naming conventions and structure used in existing tests

## Configuration

The test suite is configured in `pytest.ini` with:

- Test discovery patterns
- Coverage requirements (80% minimum)
- Custom markers for different test types
- Warning filters
- Output formatting

## Best Practices

1. **Use Shared Fixtures**: Leverage fixtures in `tests.shared.fixtures` to avoid duplication
2. **Mock External Dependencies**: Mock subprocess calls, file operations, and external tools
3. **Test Error Scenarios**: Include tests for failures, timeouts, and edge cases
4. **Use Descriptive Names**: Test function names should clearly describe what they test
5. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
6. **Temporary Files**: Always use temporary directories for file-based tests
7. **Cleanup**: Ensure tests clean up any resources they create
