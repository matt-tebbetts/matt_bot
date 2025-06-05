#!/usr/bin/env python3
"""
Unified Actorle scraper for both Discord bot integration and detailed analysis
Combines web scraping, movie data parsing, and summary generation
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import re
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple
import os
import sys
import json

# Add parent directory to path for bot imports when running standalone
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import bot logger, fallback to basic logging if not available
try:
    # Try simple SQL import first to avoid circular imports
    from bot.functions.sql_helper import send_df_to_sql, execute_query, DatabaseManager
    SQL_AVAILABLE = True
    
    # Try logger import, but don't fail if it has circular import issues
    try:
        from bot.connections.logging_config import get_logger, log_exception
        logger = get_logger('actorle_scraper')
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('actorle_scraper')
        def log_exception(logger, e, context):
            logger.error(f"{context}: {str(e)}")
    
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('actorle_scraper')
    SQL_AVAILABLE = False
    def log_exception(logger, e, context):
        logger.error(f"{context}: {str(e)}")
    def send_df_to_sql(*args, **kwargs):
        logger.warning("SQL functionality not available - install bot dependencies")
        return None
    def execute_query(*args, **kwargs):
        logger.warning("SQL functionality not available - install bot dependencies")
        return None
    # Create a dummy DatabaseManager for consistency
    class DatabaseManager:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def run_async(self, coro): 
            logger.warning("SQL functionality not available")
            return None

# Suppress Selenium noise
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


class ActorleScraper:
    """Unified Actorle scraper with multiple output formats"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.cache_dir = os.path.dirname(__file__)  # Save in actorle_analysis directory
        self.cache_file = os.path.join(self.cache_dir, "daily_actorle_cache.json")
        
        # Create cache directory if it doesn't exist (should already exist since it's actorle_analysis)
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver with optimal settings"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        return webdriver.Chrome(options=chrome_options)
    
    def scrape_page(self) -> Optional[str]:
        """Scrape the Actorle page and return raw content"""
        try:
            logger.info("Starting Actorle page scraping...")
            self.driver = self.setup_driver()
            self.driver.set_page_load_timeout(30)
            
            logger.debug("Loading actorle.com...")
            self.driver.get('https://actorle.com/')
            
            # Wait for game to load
            wait = WebDriverWait(self.driver, 15)
            
            # Try to find game elements that indicate the page loaded
            game_loaded = False
            selectors_to_try = [
                "div[class*='movie']",
                "div[class*='actor']", 
                "input[placeholder*='actor']"
            ]
            
            for selector in selectors_to_try:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    game_loaded = True
                    logger.debug(f"Game loaded! Found element: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not game_loaded:
                logger.warning("Game did not load properly - no game elements found")
                return None
            
            # Give extra time for full JavaScript execution
            time.sleep(3)
            html_content = self.driver.page_source
            
            # Store HTML content for later use (e.g., extracting game number)
            self._current_html = html_content
            
            return html_content
            
        except WebDriverException as e:
            log_exception(logger, e, "Chrome WebDriver setup/operation")
            return None
        except Exception as e:
            log_exception(logger, e, "Actorle page scraping")
            return None
    
    def extract_movie_table_data(self, html_content: str) -> List[Dict]:
        """Extract detailed movie data from the page content"""
        if not html_content:
            return []
        
        # Debug: check what elements we can find
        logger.info("Debugging page elements...")
        
        # Try multiple selectors that might contain movie data
        selectors_to_try = [
            "[class*='movie']",
            "[class*='table']", 
            "[class*='film']",
            "[class*='data']",
            "div",  # Fallback to all divs
            "*"     # Last resort - all elements
        ]
        
        main_table_text = None
        
        for selector in selectors_to_try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            logger.debug(f"Found {len(elements)} elements with selector '{selector}'")
            
            for i, element in enumerate(elements[:20]):  # Check first 20 elements
                try:
                    text = element.text.strip()
                    if len(text) > 100:  # Only check substantial content
                        # Look for movie-related keywords
                        if any(keyword in text.upper() for keyword in ['MOVIE', 'TITLE', 'GENRE', 'IMDB', 'RATING']):
                            logger.info(f"Found potential movie element #{i} with selector '{selector}': {len(text)} chars")
                            logger.debug(f"Content preview: {text[:200]}")
                            
                            if len(text) > 500:  # Substantial content likely to be the main table
                                main_table_text = text
                                logger.info(f"Using this as main movie table")
                                break
                except Exception as e:
                    logger.debug(f"Error reading element #{i}: {e}")
                    continue
            
            if main_table_text:
                break
        
        # If we didn't find it in elements, try parsing from HTML directly
        if not main_table_text:
            logger.info("Movie table not found in elements, trying HTML parsing...")
            # Look for patterns in the raw HTML that might contain movie data
            # Sometimes the data is in script tags or other structures
            
            # Try to find movie data patterns in HTML
            year_patterns = re.findall(r'(19|20)\d{2}', html_content)
            rating_patterns = re.findall(r'\b[0-9]\.[0-9]\b', html_content)
            
            if len(year_patterns) > 10 and len(rating_patterns) > 5:
                logger.info(f"Found potential movie data in HTML: {len(year_patterns)} years, {len(rating_patterns)} ratings")
                # Try to extract from HTML structure
                return self._parse_from_html_structure(html_content)
        
        if not main_table_text:
            logger.warning("Could not find main movie table in any elements")
            return []
        
        return self._parse_movie_table_structure(main_table_text)
    
    def _parse_from_html_structure(self, html_content: str) -> List[Dict]:
        """Parse movie data directly from HTML structure when table text is not available"""
        logger.info("Attempting to parse movie data from HTML structure...")
        
        movies = []
        
        # Look for structured data in the HTML
        # This is a fallback method for when the text extraction doesn't work
        
        # Try to find JSON data embedded in the page
        json_patterns = [
            r'"movies"\s*:\s*\[(.*?)\]',
            r'"filmography"\s*:\s*\[(.*?)\]',
            r'movies\s*=\s*\[(.*?)\]'
        ]
        
        for pattern in json_patterns:
            matches = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if matches:
                logger.info(f"Found potential JSON movie data")
                try:
                    # This would need more sophisticated JSON parsing
                    # For now, just log that we found it
                    logger.debug(f"JSON data preview: {matches.group(1)[:200]}")
                except Exception as e:
                    logger.debug(f"Error parsing JSON data: {e}")
        
        # If no structured data found, return empty list
        if not movies:
            logger.warning("No movie data could be extracted from HTML structure")
        
        return movies
    
    def _parse_movie_table_structure(self, text_content: str) -> List[Dict]:
        """Parse the movie table structure intelligently"""
        logger.info("Parsing movie table structure...")
        
        lines = text_content.split('\n')
        movies = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line has a year
            year_match = re.search(r'^(19|20)\d{2}$', line)
            if year_match:
                year = year_match.group()
                
                # Look at the previous line for censored movie title
                title = ""
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    if '×' in prev_line or '\u2002' in prev_line:
                        title = prev_line
                
                # Look at the next few lines for genres and rating
                genres_line = ""
                rating_line = ""
                
                for j in range(1, 4):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        
                        # Check if it's a genres line
                        if re.match(r'^[A-Z][A-Z\s]*[A-Z]$', next_line) and any(
                            genre in next_line for genre in ['ACTION', 'DRAMA', 'COMEDY', 
                            'THRILLER', 'ROMANCE', 'WESTERN', 'HORROR', 'SCIENCE', 
                            'ADVENTURE', 'CRIME']):
                            genres_line = next_line
                        
                        # Check if it's a rating line
                        elif re.match(r'^\d\.\d$', next_line):
                            rating_line = next_line
                
                # Parse genres
                separated_genres = self._parse_genres(genres_line) if genres_line else None
                
                movie = {
                    'year': int(year),
                    'title': title if title else None,
                    'genres': separated_genres,
                    'rating': float(rating_line) if rating_line else None
                }
                movies.append(movie)
                
                logger.debug(f"Found movie: {year} | {title[:30] if title else 'No title'} | "
                           f"{separated_genres or 'No genres'} | {rating_line or 'No rating'}")
        
        logger.info(f"Successfully parsed {len(movies)} movies")
        return movies
    
    def _parse_genres(self, genres_line: str) -> str:
        """Parse and separate concatenated genres"""
        # Add spaces before capital letters
        spaced_genres = re.sub(r'([a-z])([A-Z])', r'\1 \2', genres_line)
        spaced_genres = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', spaced_genres)
        
        # Define common genres
        common_genres = [
            'SCIENCE FICTION', 'ACTION', 'ADVENTURE', 'ANIMATION', 'COMEDY', 
            'CRIME', 'DRAMA', 'FAMILY', 'FANTASY', 'HORROR', 'HISTORY', 
            'MYSTERY', 'ROMANCE', 'THRILLER', 'WAR', 'WESTERN'
        ]
        
        # Extract genres in order of appearance
        genre_list = []
        remaining = spaced_genres
        
        for genre in common_genres:
            if genre in remaining:
                genre_list.append(genre)
                remaining = remaining.replace(genre, '', 1).strip()
        
        return '; '.join(genre_list) if genre_list else genres_line
    
    def _prioritize_genres(self, genres_str: str) -> str:
        """Intelligently prioritize and consolidate genres to top 2 most important"""
        if not genres_str or pd.isna(genres_str):
            return "X"
        
        # Parse genres from the string
        genres = [g.strip() for g in str(genres_str).split(';') if g.strip()]
        if not genres:
            return "X"
        
        # Define genre priority and combinations
        high_priority = ['WAR', 'COMEDY', 'HORROR', 'WESTERN', 'MYSTERY', 'ANIMATION']
        medium_priority = ['ACTION', 'THRILLER', 'CRIME', 'SCIENCE FICTION', 'FANTASY', 'ROMANCE']
        low_priority = ['DRAMA', 'ADVENTURE']  # These are too common/generic
        
        # Check for special combinations first
        genre_set = set(genres)
        
        # ROM-COM combination
        if 'ROMANCE' in genre_set and 'COMEDY' in genre_set:
            other_genres = [g for g in genres if g not in ['ROMANCE', 'COMEDY']]
            if other_genres and other_genres[0] not in low_priority:
                return f"ROM-COM/{other_genres[0]}"
            else:
                return "ROM-COM"
        
        # ACTION-ADVENTURE combination (only if no better genres)
        if 'ACTION' in genre_set and 'ADVENTURE' in genre_set:
            other_high = [g for g in genres if g in high_priority]
            other_medium = [g for g in genres if g in medium_priority and g not in ['ACTION']]
            
            if other_high:
                return f"ACTION/{other_high[0]}"
            elif other_medium:
                return f"ACTION/{other_medium[0]}"
            else:
                return "ACTION/ADVENTURE"
        
        # SCI-FI combination
        if 'SCIENCE FICTION' in genre_set:
            other_genres = [g for g in genres if g != 'SCIENCE FICTION' and g not in low_priority]
            if other_genres:
                return f"SCI-FI/{other_genres[0]}"
            else:
                return "SCI-FI"
        
        # General prioritization logic
        prioritized = []
        
        # Add high priority genres first
        for genre in genres:
            if genre in high_priority and len(prioritized) < 2:
                prioritized.append(genre)
        
        # Add medium priority if we need more
        for genre in genres:
            if genre in medium_priority and len(prioritized) < 2 and genre not in prioritized:
                prioritized.append(genre)
        
        # Add low priority only if we still need more and have no other options
        for genre in genres:
            if genre in low_priority and len(prioritized) < 2 and genre not in prioritized:
                # Only add if it's the only option or paired with something good
                if len(prioritized) == 0 or (len(prioritized) == 1 and prioritized[0] not in low_priority):
                    prioritized.append(genre)
        
        # If we still don't have enough, add whatever we have
        for genre in genres:
            if len(prioritized) < 2 and genre not in prioritized:
                prioritized.append(genre)
        
        # Clean up genre names for display
        cleaned = []
        for genre in prioritized[:2]:  # Only take top 2
            if genre == 'SCIENCE FICTION':
                cleaned.append('SCI-FI')
            else:
                cleaned.append(genre)
        
        return '/'.join(cleaned) if cleaned else "X"
    
    def get_summary_stats(self, movies: List[Dict]) -> Dict:
        """Extract summary statistics for Discord bot"""
        if not movies:
            return {}
        
        df = pd.DataFrame(movies)
        
        # Basic stats
        stats = {
            'movie_count': len(df),
            'year_range': f"{df['year'].min()}-{df['year'].max()}",
            'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Ratings
        valid_ratings = df['rating'].dropna()
        if len(valid_ratings) > 0:
            stats['avg_rating'] = round(valid_ratings.mean(), 1)
            stats['rating_count'] = len(valid_ratings)
        
        # Genres
        all_genres = []
        for _, movie in df.iterrows():
            if pd.notna(movie['genres']):
                genres = re.findall(r'[A-Z]+', str(movie['genres']))
                all_genres.extend(genres)
        
        if all_genres:
            genre_counts = pd.Series(all_genres).value_counts()
            stats['top_genres'] = genre_counts.head(5).index.tolist()
        
        return stats
    
    def save_to_sql(self, movies: List[Dict]) -> bool:
        """Save movie data to SQL database"""
        if not movies:
            return False
        
        if not SQL_AVAILABLE:
            logger.warning("SQL functionality not available - falling back to CSV")
            return self._save_to_csv_fallback(movies)
        
        df = pd.DataFrame(movies)
        
        # Sort by year ascending to assign sequential IDs
        df_sorted = df.sort_values('year', ascending=True, na_position='last')
        
        # Add game_date column with today's date
        today = datetime.now().strftime("%Y-%m-%d")
        today_compact = datetime.now().strftime("%Y%m%d")
        df_sorted['game_date'] = today
        
        # Generate custom IDs: YYYYMMDD_NN format
        df_sorted['id'] = [f"{today_compact}_{i+1:02d}" for i in range(len(df_sorted))]
        
        # Set game_status (currently always 'puzzle' since we're scraping the unsolved state)
        df_sorted['game_status'] = 'puzzle'
        
        # Try to extract game_number from the page
        game_number = None
        try:
            if hasattr(self, '_current_html') and self._current_html:
                game_number_patterns = [
                    r'Actorle\s*#(\d+)',
                    r'"gameNumber"\s*:\s*(\d+)',
                    r'game.*?(\d{3,4})'
                ]
                
                for pattern in game_number_patterns:
                    matches = re.findall(pattern, self._current_html, re.IGNORECASE)
                    for match in matches:
                        try:
                            num = int(match)
                            if 1 <= num <= 9999:
                                game_number = num
                                break
                        except ValueError:
                            continue
                    if game_number:
                        break
        except Exception as e:
            logger.debug(f"Could not extract game number: {e}")
        
        df_sorted['game_number'] = game_number
        
        # Reorder columns to put id, game_date, and game_status first
        columns = ['id', 'game_date', 'game_number', 'game_status'] + [col for col in df_sorted.columns if col not in ['id', 'game_date', 'game_number', 'game_status']]
        df_sorted = df_sorted[columns]
        
        try:
            # Use DatabaseManager context manager for proper connection handling
            with DatabaseManager() as db:
                # Check if we're already in an async context
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    logger.warning("Already in async context - falling back to CSV. SQL save requires sync context.")
                    return self._save_to_csv_fallback(movies)
                except RuntimeError:
                    # No running loop, safe to use DatabaseManager
                    try:
                        # Delete any existing data for today's date and status
                        delete_query = "DELETE FROM actorle_history WHERE game_date = %s AND game_status = %s"
                        db.run_async(execute_query(delete_query, (today, 'puzzle')))
                        logger.info(f"Deleted existing puzzle data for {today}")
                        
                        # Then insert new data
                        db.run_async(send_df_to_sql(df_sorted, 'actorle_history', if_exists='append'))
                        logger.info(f"Saved {len(df_sorted)} movies to actorle_history table for {today} (status: puzzle)")
                        return True
                        
                    except Exception as e:
                        logger.error(f"Error in database operations: {e}")
                        raise
                        
        except Exception as e:
            logger.error(f"Error saving to SQL: {e}")
            logger.info("Falling back to CSV")
            return self._save_to_csv_fallback(movies)
    
    def _save_to_csv_fallback(self, movies: List[Dict]) -> bool:
        """Fallback method to save as CSV if SQL fails"""
        df = pd.DataFrame(movies)
        df_sorted = df.sort_values('rating', ascending=False, na_position='last')
        
        # Add game_date column
        today = datetime.now().strftime("%Y-%m-%d")
        df_sorted['game_date'] = today
        
        filename = "actorle_movies_backup.csv"
        df_sorted.to_csv(filename, index=False)
        logger.info(f"Saved {len(df_sorted)} movies to backup CSV: {filename}")
        return True
    
    def generate_summary(self, movies: List[Dict]) -> str:
        """Generate comprehensive actor identification summary"""
        if not movies:
            return ""
        
        df = pd.DataFrame(movies)
        summary_lines = []
        
        # Header
        summary_lines.extend([
            "="*80,
            "🎭 ACTOR IDENTIFICATION SUMMARY",
            "="*80
        ])
        
        # Basic career stats
        total_movies = len(df)
        year_range = f"{df['year'].min()}-{df['year'].max()}"
        career_span = df['year'].max() - df['year'].min() + 1
        
        valid_ratings = df['rating'].dropna()
        avg_rating = valid_ratings.mean() if len(valid_ratings) > 0 else 0
        
        summary_lines.extend([
            f"📊 CAREER OVERVIEW:",
            f"   • Total Movies: {total_movies}",
            f"   • Active Years: {year_range} ({career_span} years)",
            f"   • Average Rating: {avg_rating:.1f}/10",
            f"   • Movies with Ratings: {len(valid_ratings)}/{total_movies}"
        ])
        
        # Top-rated movies
        if len(valid_ratings) > 0:
            summary_lines.append(f"\n⭐ TOP-RATED MOVIES (Most Recognizable):")
            top_movies = df[df['rating'].notna()].nlargest(10, 'rating')
            for _, movie in top_movies.iterrows():
                genres_short = (movie['genres'][:40] + '...' 
                              if pd.notna(movie['genres']) and len(str(movie['genres'])) > 40 
                              else movie['genres'])
                summary_lines.append(f"   • {movie['year']} - {movie['rating']}/10 - {genres_short or 'Unknown genres'}")
        
        # Career by decade
        summary_lines.append(f"\n📅 CAREER BY DECADE:")
        decades = {}
        for _, movie in df.iterrows():
            decade = (movie['year'] // 10) * 10
            if decade not in decades:
                decades[decade] = {'count': 0, 'ratings': [], 'genres': set()}
            decades[decade]['count'] += 1
            if pd.notna(movie['rating']):
                decades[decade]['ratings'].append(movie['rating'])
            if pd.notna(movie['genres']):
                genres = re.findall(r'[A-Z]+', str(movie['genres']))
                decades[decade]['genres'].update(genres)
        
        for decade in sorted(decades.keys()):
            data = decades[decade]
            avg_rating = sum(data['ratings'])/len(data['ratings']) if data['ratings'] else 0
            top_genres = ', '.join(list(data['genres'])[:3])
            summary_lines.append(f"   • {decade}s: {data['count']} movies, avg {avg_rating:.1f}/10, genres: {top_genres}")
        
        # Genre analysis
        summary_lines.append(f"\n🏷️  GENRE BREAKDOWN:")
        all_genres = []
        for _, movie in df.iterrows():
            if pd.notna(movie['genres']):
                genres = re.findall(r'[A-Z]+', str(movie['genres']))
                all_genres.extend(genres)
        
        if all_genres:
            genre_counts = pd.Series(all_genres).value_counts()
            total_genre_instances = len(all_genres)
            summary_lines.append("   Top genres (actor's specialty):")
            for genre, count in genre_counts.head(8).items():
                percentage = (count/total_genre_instances)*100
                summary_lines.append(f"   • {genre}: {count} movies ({percentage:.1f}%)")
        
        # Career patterns
        summary_lines.extend([
            f"\n🎯 IDENTIFICATION CLUES:",
            f"   • Peak decade: {max(decades.keys(), key=lambda x: decades[x]['count'])}s",
            f"   • Most common genre: {genre_counts.index[0] if all_genres else 'Unknown'}",
            f"   • Highest rated film: {df.loc[df['rating'].idxmax(), 'year'] if len(valid_ratings) > 0 else 'Unknown'}"
        ])
        
        summary_text = '\n'.join(summary_lines)
        
        # Save to fixed filename (always overwrites)
        filename = "summary.txt"
        with open(filename, 'w') as f:
            f.write(summary_text)
        
        logger.info(f"Generated summary saved to {filename}")
        return filename
    
    def close(self):
        """Clean up driver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("Browser closed successfully")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
    
    def get_movies_for_discord(self, movies: List[Dict]) -> pd.DataFrame:
        """Process movies for Discord display with smart genre prioritization"""
        if not movies:
            return pd.DataFrame()
        
        df = pd.DataFrame(movies)
        
        # Ensure we have the required columns
        if 'title' not in df.columns:
            df['title'] = 'X'  # All titles are hidden anyway
        
        # Apply smart genre prioritization
        if 'genres' in df.columns:
            df['smart_genres'] = df['genres'].apply(self._prioritize_genres)
        else:
            df['smart_genres'] = 'X'
        
        # Sort by rating (best first), with NaN values at the end
        df = df.sort_values('rating', ascending=False, na_position='last')
        
        # Select columns for display
        display_df = pd.DataFrame({
            'Rating': df['rating'].fillna('X').apply(lambda x: f"{x}/10" if x != 'X' else 'X'),
            'Year': df['year'].fillna('X'),
            'Title': df['title'].fillna('X'),
            'Genres': df['smart_genres']
        })
        
        # Save the processed CSV for review
        csv_file = os.path.join(self.cache_dir, "daily_actorle_processed.csv")
        display_df.to_csv(csv_file, index=False)
        logger.info(f"💾 Saved processed CSV to {csv_file}")
        
        return display_df

    def _get_today_date(self) -> str:
        """Get today's date as string"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _load_cached_data(self) -> Optional[List[Dict]]:
        """Load cached movie data if it exists and is from today"""
        if not os.path.exists(self.cache_file):
            logger.info("No cache file found")
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cached_date = cache_data.get('date')
            today = self._get_today_date()
            
            if cached_date == today:
                logger.info(f"✅ Using cached data from {cached_date}")
                return cache_data.get('movies', [])
            else:
                logger.info(f"Cache is from {cached_date}, but today is {today}. Need fresh data.")
                return None
        
        except Exception as e:
            logger.warning(f"Error reading cache file: {e}")
            return None
    
    def _save_cached_data(self, movies: List[Dict]) -> bool:
        """Save movie data to cache with today's date"""
        try:
            cache_data = {
                'date': self._get_today_date(),
                'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'movie_count': len(movies),
                'movies': movies
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Cached {len(movies)} movies to {self.cache_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
            return False

    def get_movie_data(self) -> List[Dict]:
        """Get movie data - from cache if available, otherwise scrape"""
        # First try to load from cache
        cached_movies = self._load_cached_data()
        if cached_movies:
            return cached_movies
        
        # No cache or stale cache - need to scrape
        logger.info("🌐 No valid cache found, scraping fresh data...")
        
        html_content = self.scrape_page()
        if not html_content:
            logger.error("Failed to scrape page")
            return []
        
        movies = self.extract_movie_table_data(html_content)
        if not movies:
            logger.error("No movie data extracted")
            return []
        
        # Save to cache for future use
        self._save_cached_data(movies)
        
        return movies


# Discord bot integration functions
def get_actorle_game_info() -> Optional[Dict]:
    """
    Get Actorle game information for Discord bot integration
    Returns summary statistics suitable for Discord display
    """
    scraper = ActorleScraper()
    try:
        # Use the new caching system
        movies = scraper.get_movie_data()
        if not movies:
            return None
        
        stats = scraper.get_summary_stats(movies)
        
        # For cached data, try to extract game number if we have HTML, otherwise skip
        # (Game number extraction requires the HTML content which we don't cache)
        if hasattr(scraper, '_current_html') and scraper._current_html:
            # Extract game number from HTML if possible
            game_number_patterns = [
                r'Actorle\s*#(\d+)',
                r'"gameNumber"\s*:\s*(\d+)',
                r'game.*?(\d{3,4})'
            ]
            
            for pattern in game_number_patterns:
                matches = re.findall(pattern, scraper._current_html, re.IGNORECASE)
                for match in matches:
                    try:
                        num = int(match)
                        if 1 <= num <= 9999:
                            stats['game_number'] = num
                            break
                    except ValueError:
                        continue
                if 'game_number' in stats:
                    break
        
        # Add title if we have driver access
        if scraper.driver:
            stats['title'] = scraper.driver.title
        
        return stats
    
    finally:
        scraper.close()


def format_actorle_info(game_data: Optional[Dict]) -> str:
    """Format game data for Discord display"""
    if not game_data:
        return "❌ Unable to retrieve Actorle game information"
    
    lines = ["🎬 **Daily Actorle Game**"]
    
    if 'game_number' in game_data:
        lines.append(f"🎯 Game #{game_data['game_number']}")
    
    if 'movie_count' in game_data:
        lines.append(f"🎞️ Movies: {game_data['movie_count']}")
    
    if 'top_genres' in game_data:
        genres_str = ", ".join(game_data['top_genres'][:3])
        lines.append(f"🏷️ Top Genres: {genres_str}")
    
    if 'avg_rating' in game_data:
        lines.append(f"⭐ Average Rating: {game_data['avg_rating']}/10")
    
    if 'year_range' in game_data:
        lines.append(f"📅 Career Span: {game_data['year_range']}")
    
    lines.append(f"🕐 Updated: {game_data.get('scraped_at', 'Unknown')}")
    
    return "\n".join(lines)


def scrape_daily_actorle() -> Optional[Dict]:
    """Legacy function name for backward compatibility"""
    return get_actorle_game_info()


# Standalone analysis functions
def main():
    """Main function for standalone analysis"""
    print("🎭 Starting comprehensive Actorle analysis...")
    
    scraper = ActorleScraper(headless=True)
    
    try:
        # Scrape the page
        html_content = scraper.scrape_page()
        if not html_content:
            print("❌ Failed to scrape Actorle page")
            return
        
        # Extract movie data
        movies = scraper.extract_movie_table_data(html_content)
        if not movies:
            print("❌ No movie data found")
            return
        
        print(f"✅ Successfully extracted {len(movies)} movies")
        
        # Save to SQL
        if scraper.save_to_sql(movies):
            print("📊 Movie data saved to SQL database (actorle_history table)")
        else:
            print("❌ Failed to save movie data")
        
        # Generate summary
        summary_file = scraper.generate_summary(movies)
        print(f"📝 Actor analysis saved to: {summary_file}")
        
        # Display summary stats
        stats = scraper.get_summary_stats(movies)
        print(f"\n🎯 Quick Stats:")
        print(f"   Movies: {stats.get('movie_count', 0)}")
        print(f"   Years: {stats.get('year_range', 'Unknown')}")
        print(f"   Avg Rating: {stats.get('avg_rating', 'N/A')}/10")
        print(f"   Top Genres: {', '.join(stats.get('top_genres', [])[:3])}")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    main() 