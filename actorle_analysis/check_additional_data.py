#!/usr/bin/env python3
"""
Check for additional data fields available in Actorle scraping
"""

import sys
import os
import re

# Add parent directory to path for bot imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actorle_analysis.actorle_scraper import ActorleScraper

def analyze_additional_fields():
    """Analyze the HTML content to find additional data fields"""
    print("🔍 Analyzing Actorle page for additional data fields...")
    
    scraper = ActorleScraper(headless=True)
    
    try:
        # Scrape the page
        html_content = scraper.scrape_page()
        if not html_content:
            print("❌ Failed to scrape page")
            return
        
        print("✅ Page scraped successfully\n")
        
        # Check for additional patterns in the HTML
        patterns_to_check = {
            'Actor Name': [
                r'"actor"\s*:\s*"([^"]+)"',
                r'"mystery_actor"\s*:\s*"([^"]+)"',
                r'actor.*?name.*?"([^"]+)"',
                r'Answer.*?([A-Z][a-z]+\s+[A-Z][a-z]+)',
            ],
            'Game Information': [
                r'"game_id"\s*:\s*"?(\d+)"?',
                r'"date"\s*:\s*"([^"]+)"',
                r'"difficulty"\s*:\s*"([^"]+)"',
                r'difficulty.*?(\d+)',
            ],
            'Movie Additional Info': [
                r'"imdb_id"\s*:\s*"([^"]+)"',
                r'"director"\s*:\s*"([^"]+)"',
                r'"duration"\s*:\s*"?(\d+)"?',
                r'"box_office"\s*:\s*"([^"]+)"',
                r'tt\d{7,8}',  # IMDB ID pattern
            ],
            'Clues or Hints': [
                r'"hint"\s*:\s*"([^"]+)"',
                r'"clue"\s*:\s*"([^"]+)"',
                r'hint.*?"([^"]+)"',
                r'clue.*?"([^"]+)"',
            ]
        }
        
        found_data = {}
        
        for category, patterns in patterns_to_check.items():
            found_data[category] = []
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    # Limit to first 5 matches to avoid spam
                    unique_matches = list(set(matches))[:5]
                    found_data[category].extend(unique_matches)
        
        # Report findings
        print("📋 ADDITIONAL DATA ANALYSIS:")
        print("="*50)
        
        for category, data in found_data.items():
            if data:
                print(f"\n🎯 {category}:")
                for item in data[:5]:  # Limit display
                    print(f"   • {item}")
            else:
                print(f"\n❌ {category}: No additional data found")
        
        # Check for JSON objects that might contain structured data
        json_patterns = [
            r'\{[^{}]*"movie"[^{}]*\}',
            r'\{[^{}]*"actor"[^{}]*\}',
            r'\{[^{}]*"game"[^{}]*\}',
        ]
        
        print(f"\n🔍 JSON STRUCTURES:")
        print("="*30)
        
        json_found = False
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if matches:
                json_found = True
                print(f"\nFound JSON-like structures:")
                for i, match in enumerate(matches[:3]):  # Show first 3
                    print(f"   {i+1}. {match[:100]}{'...' if len(match) > 100 else ''}")
        
        if not json_found:
            print("   No JSON structures containing movie/actor/game data found")
        
        # Check for any structured data tables
        print(f"\n📊 STRUCTURED DATA:")
        print("="*25)
        
        # Look for table-like structures
        table_indicators = ['<table', '<tr', '<td', 'data-', 'id=']
        table_found = False
        
        for indicator in table_indicators:
            if indicator in html_content.lower():
                count = html_content.lower().count(indicator)
                if count > 5:  # Only report if significant
                    table_found = True
                    print(f"   • {indicator}: {count} occurrences")
        
        if not table_found:
            print("   No significant table structures found")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("="*20)
        print("   Currently captured: year, title, genres, rating, game_date, game_number")
        
        additional_fields = []
        for category, data in found_data.items():
            if data and category != 'Game Information':  # Game info already captured
                additional_fields.append(category.lower())
        
        if additional_fields:
            print(f"   Potentially available: {', '.join(additional_fields)}")
        else:
            print("   No significant additional fields detected in current scraping")
            print("   The current fields appear to be the primary data available")
        
    finally:
        scraper.close()

if __name__ == "__main__":
    analyze_additional_fields() 