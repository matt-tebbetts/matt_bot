"""
Actorle scraper for Discord bot
Uses Selenium to scrape JavaScript-loaded content from actorle.com
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import re
from datetime import datetime
import logging
from typing import Dict, Optional
from bot.connections.logging_config import get_logger, log_exception

# Set up logger for this module
logger = get_logger('actorle_scraper')

# Suppress Selenium noise
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

def get_actorle_game_info() -> Optional[Dict]:
    """
    Scrape current Actorle game information using Selenium
    
    Returns:
        Dict containing game information, or None if scraping fails
        {
            'game_number': int,
            'movie_count': int,
            'genres_found': list,
            'avg_rating': float,
            'title': str,
            'scraped_at': str
        }
    """
    driver = None
    try:
        logger.info("Starting Selenium-based Actorle scraping...")
        
        # Setup Chrome driver with optimal settings
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        logger.debug("Loading actorle.com...")
        driver.get('https://actorle.com/')
        
        # Wait for game to load
        wait = WebDriverWait(driver, 15)
        
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
        logger.debug("Extracting game data...")
        
        # Extract game data
        game_data = {}
        html = driver.page_source
        
        # Extract game number
        game_number_patterns = [
            r'Actorle\s*#(\d+)',
            r'"gameNumber"\s*:\s*(\d+)',
            r'game.*?(\d{3,4})'  # Look for 3-4 digit numbers
        ]
        
        for pattern in game_number_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                try:
                    num = int(match)
                    if 1 <= num <= 9999:  # Reasonable range for daily games
                        game_data['game_number'] = num
                        logger.info(f"Found game number: {num}")
                        break
                except ValueError:
                    continue
            if 'game_number' in game_data:
                break
        
        # Extract movie data from elements with movie-related classes
        try:
            movie_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='movie']")
            movie_text = ""
            for element in movie_elements:
                text = element.text.strip()
                if text and len(text) > 50:  # Substantial content
                    movie_text += text + "\n"
            
            if movie_text:
                logger.debug(f"Found movie data: {len(movie_text)} characters")
                
                # Count number of movies by looking for year patterns
                years = re.findall(r'\b(19|20)\d{2}\b', movie_text)
                if years:
                    unique_years = set(years)
                    game_data['movie_count'] = len(unique_years)
                    logger.info(f"Found {len(unique_years)} movies")
                
                # Extract genre information
                genres = re.findall(r'\b(ACTION|DRAMA|COMEDY|THRILLER|ROMANCE|ADVENTURE|SCIENCE FICTION|WESTERN|HORROR|MYSTERY|CRIME|WAR|FANTASY|ANIMATION|FAMILY|HISTORY)\b', movie_text)
                if genres:
                    unique_genres = list(set(genres))
                    game_data['genres_found'] = unique_genres[:5]  # Top 5 genres
                    logger.info(f"Found genres: {unique_genres[:5]}")
                
                # Look for IMDB ratings
                ratings = re.findall(r'\b([0-9]\.[0-9])\b', movie_text)
                if ratings:
                    try:
                        rating_values = [float(r) for r in ratings[:10]]  # Max 10 ratings
                        avg_rating = sum(rating_values) / len(rating_values)
                        game_data['avg_rating'] = round(avg_rating, 1)
                        logger.info(f"Found average rating: {avg_rating}")
                    except Exception as e:
                        logger.debug(f"Error calculating rating: {e}")
        
        except Exception as e:
            logger.debug(f"Error extracting movie data: {e}")
        
        # Get basic page info
        game_data['title'] = driver.title
        game_data['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Successfully scraped Actorle data with {len(game_data)} fields")
        return game_data if game_data else None
        
    except WebDriverException as e:
        log_exception(logger, e, "Chrome WebDriver setup/operation")
        return None
    except Exception as e:
        log_exception(logger, e, "Actorle Selenium scraping")
        return None
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.debug("Browser closed successfully")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")

def format_actorle_info(game_data: Optional[Dict]) -> str:
    """
    Format game data for Discord display
    
    Args:
        game_data: Dictionary containing game information
        
    Returns:
        Formatted string for Discord message
    """
    if not game_data:
        return "❌ Unable to retrieve Actorle game information"
    
    lines = ["🎬 **Daily Actorle Game**"]
    
    if 'game_number' in game_data:
        lines.append(f"🎯 Game #{game_data['game_number']}")
    
    if 'movie_count' in game_data:
        lines.append(f"🎞️ Movies: {game_data['movie_count']}")
    
    if 'genres_found' in game_data:
        genres_str = ", ".join(game_data['genres_found'])
        lines.append(f"🏷️ Genres: {genres_str}")
    
    if 'avg_rating' in game_data:
        lines.append(f"⭐ Avg IMDB: {game_data['avg_rating']}")
    
    lines.append(f"🕒 Updated: {game_data.get('scraped_at', 'Unknown')}")
    lines.append("🌐 Play at: https://actorle.com/")
    
    return "\n".join(lines)

# Legacy function name for backward compatibility
def scrape_daily_actorle() -> Optional[Dict]:
    """Legacy function name - calls the new Selenium scraper"""
    return get_actorle_game_info()

# For testing/debugging
if __name__ == "__main__":
    result = get_actorle_game_info()
    if result:
        print("Actorle Game Data:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to scrape Actorle data") 