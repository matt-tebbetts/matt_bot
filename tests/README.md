# Test Files

This directory contains test and investigation files used during development of the NYT crossword data collection system.

## Files

- **`test_api_limits.py`** - Tests NYT API rate limits and date range capabilities
- **`test_nyt_api.py`** - General NYT API testing and exploration
- **`investigate_api.py`** - Investigation of API response structure for finding checks/reveals data
- **`raw_nyt_response_*.json`** - Raw API responses captured for analysis

## Usage

These files were used to:
1. Understand NYT API behavior and limitations
2. Discover the checks/reveals data in board.cells
3. Test different date range strategies
4. Validate API responses

Most of these are historical artifacts from the development process. 