#!/usr/bin/env python3
"""
Parse the Actorle movie table structure more effectively
Focus on the table format we observed: year, genres, rating
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import re
import pandas as pd
from datetime import datetime

def setup_driver():
    """Setup Chrome driver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    return webdriver.Chrome(options=chrome_options)

def parse_movie_table_data(text_content):
    """Parse the movie table structure more intelligently"""
    print("🔍 Parsing movie table structure...")
    
    # Split into lines and look for the movie data pattern
    lines = text_content.split('\n')
    
    movies = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Check if this line has a year
        year_match = re.search(r'^(19|20)\d{2}$', line)
        if year_match:
            # This is a year line
            year = year_match.group()
            
            # Look at the previous line for censored movie title (×'s)
            title = ""
            if i > 0:
                prev_line = lines[i - 1].strip()
                # Look for × characters (censored title)
                if '×' in prev_line or '\u2002' in prev_line:  # × or en-space
                    title = prev_line
            
            # Look at the next few lines for genres and rating
            genres_line = ""
            rating_line = ""
            
            # Check next lines for patterns
            for j in range(1, 4):  # Check next 3 lines
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    
                    # Check if it's a genres line (ALL CAPS with common genres)
                    if re.match(r'^[A-Z][A-Z\s]*[A-Z]$', next_line) and any(genre in next_line for genre in ['ACTION', 'DRAMA', 'COMEDY', 'THRILLER', 'ROMANCE', 'WESTERN', 'HORROR', 'SCIENCE', 'ADVENTURE', 'CRIME']):
                        genres_line = next_line
                    
                    # Check if it's a rating line (decimal number)
                    elif re.match(r'^\d\.\d$', next_line):
                        rating_line = next_line
            
            # Parse and separate genres
            separated_genres = ""
            if genres_line:
                # Split the concatenated genres using common patterns
                # Add spaces before capital letters that follow lowercase or other capitals
                spaced_genres = re.sub(r'([a-z])([A-Z])', r'\1 \2', genres_line)
                spaced_genres = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', spaced_genres)
                
                # Common genre patterns to split on
                genre_list = []
                remaining = spaced_genres
                
                # Define common genres to look for
                common_genres = [
                    'SCIENCE FICTION', 'ACTION', 'ADVENTURE', 'ANIMATION', 'COMEDY', 
                    'CRIME', 'DRAMA', 'FAMILY', 'FANTASY', 'HORROR', 'HISTORY', 
                    'MYSTERY', 'ROMANCE', 'THRILLER', 'WAR', 'WESTERN'
                ]
                
                # Extract genres in order of appearance
                for genre in common_genres:
                    if genre in remaining:
                        genre_list.append(genre)
                        remaining = remaining.replace(genre, '', 1).strip()
                
                # Join with semicolons
                separated_genres = '; '.join(genre_list) if genre_list else genres_line
            
            # Create movie entry
            movie = {
                'year': int(year),
                'title': title if title else None,
                'genres': separated_genres if separated_genres else None,
                'rating': float(rating_line) if rating_line else None
            }
            movies.append(movie)
            
            # Show what we found
            title_display = title[:30] + '...' if len(title) > 30 else title
            print(f"  Found movie: {year} | {title_display or 'No title'} | {separated_genres or 'No genres'} | {rating_line or 'No rating'}")
    
    return movies

def extract_raw_movie_text(driver):
    """Extract the raw movie table text"""
    movie_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='movie']")
    
    for i, element in enumerate(movie_elements):
        text = element.text.strip()
        if 'MOVIE TITLE GENRES IMDB' in text and len(text) > 500:
            print(f"📽️  Found main movie table (element #{i+1}):")
            print(f"   Length: {len(text)} characters")
            print(f"   First 300 chars:\n{text[:300]}")
            print(f"\n   Lines 10-30:")
            lines = text.split('\n')
            for j, line in enumerate(lines[10:30], 10):
                print(f"   {j:2d}: '{line}'")
            return text
    
    return None

def main():
    """Main extraction function"""
    print("🎬 Starting focused movie table parsing...")
    
    driver = setup_driver()
    
    try:
        print("📱 Loading actorle.com...")
        driver.get('https://actorle.com/')
        
        # Wait for game to load
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='movie']")))
        time.sleep(4)  # Let it fully load
        
        print("✅ Game loaded!")
        
        # Extract the raw movie text
        movie_text = extract_raw_movie_text(driver)
        
        if movie_text:
            # Parse the movie data
            movies = parse_movie_table_data(movie_text)
            
            print(f"\n📊 PARSED {len(movies)} MOVIES:")
            print("=" * 60)
            
            if movies:
                # Create DataFrame
                df = pd.DataFrame(movies)
                print(df.to_string(index=False))
                
                # Save to CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_file = f"parsed_movies_{timestamp}.csv"
                df.to_csv(csv_file, index=False)
                print(f"\n💾 Saved to: {csv_file}")
                
                # Stats
                if 'rating' in df.columns:
                    valid_ratings = df['rating'].dropna()
                    if len(valid_ratings) > 0:
                        print(f"\n⭐ RATING STATS:")
                        print(f"   Movies with ratings: {len(valid_ratings)}/{len(movies)}")
                        print(f"   Average rating: {valid_ratings.mean():.1f}")
                        print(f"   Range: {valid_ratings.min():.1f} - {valid_ratings.max():.1f}")
                
                if 'genres' in df.columns:
                    movies_with_genres = df['genres'].dropna()
                    print(f"\n🏷️  GENRE STATS:")
                    print(f"   Movies with genres: {len(movies_with_genres)}/{len(movies)}")
                    
                    # Count unique genres
                    all_genres = []
                    for genre_str in movies_with_genres:
                        # Split on common genre separators
                        genres = re.findall(r'[A-Z]+', genre_str)
                        all_genres.extend(genres)
                    
                    if all_genres:
                        genre_counts = pd.Series(all_genres).value_counts()
                        print("   Top genres:")
                        for genre, count in genre_counts.head(5).items():
                            print(f"     {genre}: {count}")
                
                # Year range
                years = [int(movie['year']) for movie in movies]
                print(f"\n📅 YEAR RANGE: {min(years)} - {max(years)}")
                
            else:
                print("❌ No movies parsed successfully")
        else:
            print("❌ Could not find movie table data")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        driver.quit()
        print("\n🔒 Browser closed")

if __name__ == "__main__":
    main() 