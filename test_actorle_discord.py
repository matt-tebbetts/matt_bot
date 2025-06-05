#!/usr/bin/env python3
"""
Test script to see the Discord-formatted Actorle output
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), 'actorle_analysis'))

from actorle_analysis.actorle_scraper import ActorleScraper
import pandas as pd

def test_actorle_discord_output():
    """Test the new Discord-formatted output"""
    print("🎭 Testing Actorle Discord Output")
    print("="*50)
    
    scraper = ActorleScraper(headless=True)
    
    try:
        print("📡 Getting movie data (checking cache first)...")
        movies = scraper.get_movie_data()
        
        if not movies:
            print("❌ No movie data found")
            return
        
        print(f"✅ Found {len(movies)} movies!")
        
        print("\n📊 Raw movie data sample:")
        for i, movie in enumerate(movies[:3]):  # Show first 3 movies
            print(f"  Movie {i+1}: {movie}")
        
        print(f"\n🎯 Processing for Discord display...")
        discord_df = scraper.get_movies_for_discord(movies)
        
        if discord_df.empty:
            print("❌ No processed data")
            return
        
        print("✅ Discord DataFrame created!")
        print(f"📋 Shape: {discord_df.shape}")
        
        print(f"\n🎭 FINAL DISCORD OUTPUT:")
        print("="*60)
        print(discord_df.to_string(index=False))
        print("="*60)
        
        # Show it in CSV format too (what the df_to_image will receive)
        print(f"\n📋 CSV FORMAT (what df_to_image receives):")
        print("="*60)
        print(discord_df.to_csv(index=False))
        print("="*60)
        
        # Also show some stats about the genre prioritization
        print(f"\n📈 Genre Prioritization Results:")
        genre_counts = discord_df['Genres'].value_counts()
        print(f"  Total unique genre combinations: {len(genre_counts)}")
        print(f"  Top 5 genre combinations:")
        for genre, count in genre_counts.head().items():
            print(f"    {genre}: {count} movies")
        
        # Show cache info
        cache_file = scraper.cache_file
        if os.path.exists(cache_file):
            print(f"\n💾 Cache file exists at: {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                print(f"  Cache date: {cache_data.get('date')}")
                print(f"  Scraped at: {cache_data.get('scraped_at')}")
                print(f"  Movie count: {cache_data.get('movie_count')}")
            except Exception as e:
                print(f"  Error reading cache info: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close()

if __name__ == "__main__":
    test_actorle_discord_output() 