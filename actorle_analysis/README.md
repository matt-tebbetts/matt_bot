# Actorle Movie Scraper

A simple Selenium-based scraper for extracting daily movie data from actorle.com.

## Overview

Extracts movie data from the JavaScript-heavy Actorle game website and provides clean CSV output with the hidden movie collection for each daily puzzle.

## Files

- **`parse_movie_table.py`** - Main scraper using Selenium
- **`parsed_movies_*.csv`** - Extracted movie data (timestamped files)
- **`README.md`** - This file

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install selenium pandas
   ```
   
2. **Run the scraper:**
   ```bash
   python parse_movie_table.py
   ```

## Output

Each run generates a timestamped CSV file: `parsed_movies_YYYYMMDD_HHMMSS.csv`

**Data Structure:**
- `year` - Movie release year
- `title` - Puzzle representation (e.g., "× ×××× ××× ×××××××")
- `genres` - Semicolon-separated genres (e.g., "SCIENCE FICTION; ACTION; ADVENTURE")  
- `rating` - IMDB rating (1-10 scale)

## Sample Results

53 movies extracted from recent game with:
- Year range: 1967-2025
- Rating range: 5.3-8.7
- Properly parsed genres and censored titles

## Technical Notes

- Uses Selenium WebDriver for JavaScript-rendered content
- Automatically waits for dynamic content loading
- Handles concatenated genre parsing
- Extracts censored titles showing puzzle structure
- Requires Chrome browser

## Output Files

Each run generates timestamped files:
- `parsed_movies_YYYYMMDD_HHMMSS.csv` - Raw extraction
- `clean_movie_summary_YYYYMMDD_HHMMSS.csv` - Processed analysis

## Analysis Features

- Decade-based movie distribution
- Genre frequency analysis  
- Rating distribution and statistics
- Notable movie identification (highest/lowest rated)
- Clean CSV export for further analysis

The scraper successfully handles Actorle's dynamic JavaScript content and provides comprehensive movie data extraction for puzzle analysis. 