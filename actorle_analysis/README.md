# 🎭 Actorle Analysis

A comprehensive scraper and analyzer for the daily Actorle game at [actorle.com](https://actorle.com/).

## 📁 Centralized Organization

This directory contains the unified Actorle functionality:

- **`actorle_scraper.py`** - Main unified scraper with both Discord bot integration and standalone analysis
- **`summary.txt`** - Latest actor identification analysis (always overwrites)
- **`create_table.sql`** - Database schema for the actorle_detail table
- **Backup files** - CSV fallbacks when SQL is unavailable

## 🚀 Usage

### For Discord Bot Integration

The scraper is automatically imported by the bot and provides these functions:

```python
from actorle_scraper import get_actorle_game_info, format_actorle_info

# Get game stats for Discord
game_data = get_actorle_game_info()
formatted_message = format_actorle_info(game_data)
```

### For Standalone Analysis

Run the scraper directly for comprehensive analysis:

```bash
# From the actorle_analysis directory
python actorle_scraper.py
```

This will:
- Scrape the current Actorle game
- Extract all movie data (title, year, genres, ratings)
- **Save to SQL database** (`actorle_detail` table) with `game_date` column
- Create/overwrite `summary.txt` with actor identification analysis

## 📊 Features

### 🎯 Discord Bot Integration
- Quick game stats (movie count, year range, top genres, average rating)
- Game number detection
- Formatted messages for Discord

### 🔍 Detailed Analysis
- **Movie Data Storage**: Saves to SQL database with game date tracking
- **Actor Identification Summary**: Comprehensive analysis in `summary.txt` including:
  - Career overview and statistics
  - Top-rated movies (most recognizable)
  - Career breakdown by decade
  - Genre analysis and specialties
  - Key identification clues

### 🛠️ Technical Features
- **SQL Database Integration** - Stores data in `actorle_detail` table
- **CSV Fallback** - Automatic backup when SQL unavailable
- **Fixed Summary File** - Always overwrites `summary.txt` (no date clutter)
- **Selenium-based scraping** - Handles JavaScript-heavy content
- **Intelligent parsing** - Extracts structured data from unstructured text
- **Error handling** - Graceful fallbacks and logging
- **Bot compatibility** - Works with or without bot infrastructure

## 🗄️ Database Schema

The scraper saves data to the `actorle_detail` table:

```sql
CREATE TABLE actorle_detail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_date DATE NOT NULL,        -- When the game was played
    year INT NOT NULL,              -- Movie release year
    title TEXT,                     -- Censored movie title (××× format)
    genres TEXT,                    -- Semicolon-separated genres
    rating DECIMAL(3,1),            -- IMDB rating (1.0-10.0)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📈 Output Files

- **SQL Database**: All movie data stored in `actorle_detail` table
- **`summary.txt`** - Current actor analysis (always overwrites)
- **`actorle_movies_backup.csv`** - Backup when SQL unavailable

## 🔧 Dependencies

- `selenium` - Web scraping
- `pandas` - Data processing
- `aiomysql` - Database connectivity
- `python-dateutil` - Date handling

## 🏗️ Architecture

The `ActorleScraper` class provides a unified interface:

1. **`scrape_page()`** - Gets raw HTML content
2. **`extract_movie_table_data()`** - Parses movie information
3. **`get_summary_stats()`** - Generates Discord-friendly stats
4. **`save_to_sql()`** - Saves to database with game_date
5. **`generate_summary()`** - Creates fixed `summary.txt` file

### Data Flow

```
Actorle.com → Selenium → Movie Parser → SQL Database
                                    ↘ summary.txt (fixed filename)
```

This design:
- **Eliminates file clutter** - No more dated CSV files
- **Centralizes data** - All historical games in one SQL table
- **Provides fallbacks** - CSV backup when SQL unavailable
- **Maintains bot compatibility** - Works in all contexts 