# Test Suite

This directory contains all automated test scripts for the OCR Metadata Extraction project.

## Quick Start

```bash
# Run all tests
python -m pytest .

# Run specific test
python test_ami_upload.py

# Run with verbose output
python -m pytest -v .
```

## Test Categories

### AMI (Archival Metadata Items) Tests
- `test_ami_file_upload.py` - Tests file upload functionality for AMI
- `test_ami_pattern_push.py` - Tests push patterns and workflows
- `test_ami_upload.py` - General AMI upload tests
- `test_amiset_endpoints.py` - Tests AMISET API endpoints

### Archipelago Integration Tests
- `test_archipelago_upload.py` - Tests Archipelago upload functionality

### Backend Tests
- `test_backend_folders.py` - Tests backend folder operations
- `test_critical_fixes.py` - Verifies critical bug fixes

### OCR Provider Tests
- `test_google_lens.py` - Tests Google Lens OCR provider
- `test_lmstudio_direct.py` - Direct LMStudio integration tests
- `test_lmstudio_fixed.py` - Tests for fixed LMStudio issues
- `test_pdf_extraction_working.py` - Tests PDF extraction

### LMStudio Integration Tests
- `tests_lmstudio_integration.py` - Full LMStudio integration suite
- `tests_lmstudio_provider.py` - LMStudio provider-specific tests
- `tests_lmstudio_standalone.py` - Standalone LMStudio tests

### UI/Frontend Tests
- `test_folder_picker.py` - Tests folder picker component
- `test_docker_socket_streaming.py` - Docker socket streaming tests

### Worker Tests
- `test_worker_file_download.py` - Tests worker file download functionality

### General Tests
- `test_improvements.py` - Tests for improvements and enhancements
- `test_pip.py` - Package installation verification
- `test_fid_extraction.py` - File ID extraction tests

### Utility Scripts
- `check_latest_nodes.py` - Utility to check latest node versions

## Running Specific Test Groups

```bash
# AMI tests only
python -m pytest test_ami*.py

# LMStudio tests only
python -m pytest tests_lmstudio*.py test_lmstudio*.py

# Integration tests
python -m pytest test_*_integration.py

# Quick tests
python test_pip.py
python test_improvements.py
```

## Test Requirements

Most tests require:
- Python 3.8+
- pytest
- Backend service running
- MongoDB connection (for AMI tests)
- Appropriate API keys/credentials configured

## Environment Setup

Before running tests, ensure:

1. Copy `.env.example` to `.env`
2. Configure required API keys (Google Lens, Claude, etc.)
3. Start backend service: `python backend/run.py`
4. Ensure MongoDB is running

## Troubleshooting

### Tests fail with connection errors
- Verify backend service is running
- Check MongoDB connection
- Verify `MONGO_URI` in `.env`

### LMStudio tests fail
- Verify LMStudio is running locally
- Check `LMSTUDIO_HOST` setting
- Ensure LMStudio model is loaded

### Google Lens tests fail
- Verify API key is set
- Check network connectivity
- Verify rate limits not exceeded

## Writing New Tests

1. Create a new file: `test_feature_name.py`
2. Follow existing test patterns
3. Use descriptive names
4. Add docstrings explaining test purpose
5. Place in appropriate category

## Test Results

Test results and reports are typically saved in:
- `../TESTING_SUMMARY.txt` - Overall test summary
- `../TEST_SUMMARY_REPORT.md` - Detailed test report
- `../MAC_TEST_RESULTS.md` - macOS-specific results

---

**Last Updated:** January 13, 2026
