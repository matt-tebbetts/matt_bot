#!/usr/bin/env python3
"""
NYT Crossword Service Wrapper
Handles automated data collection with proper timing and new player detection.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging
import pytz

# Add the bot functions to path
sys.path.append(str(Path(__file__).parent.parent))
from functions.save_nyt import main as save_nyt_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/nyt_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NYTService:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_file = self.base_dir / "files/config/users.json"
        self.state_file = self.base_dir / "files/config/service_state.json"
        self.known_players = set()
        
    def load_service_state(self):
        """Load the service state to track known players"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.known_players = set(state.get('known_players', []))
            else:
                self.known_players = set()
        except Exception as e:
            logger.error(f"Error loading service state: {e}")
            self.known_players = set()
    
    def save_service_state(self):
        """Save the service state"""
        try:
            os.makedirs(self.state_file.parent, exist_ok=True)
            state = {
                'known_players': list(self.known_players),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving service state: {e}")
    
    def get_current_players(self):
        """Get current players from config"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return {user['player_name'] for user in config['users']}
        except Exception as e:
            logger.error(f"Error loading users config: {e}")
            return set()
    
    def detect_new_players(self):
        """Detect if there are any new players and return them"""
        current_players = self.get_current_players()
        new_players = current_players - self.known_players
        
        if new_players:
            logger.info(f"New players detected: {new_players}")
            self.known_players.update(new_players)
            self.save_service_state()
            
        return new_players
    
    def get_nyt_puzzle_date(self):
        """
        Get the current NYT puzzle date, accounting for their release schedule:
        - Daily puzzles: Released at 10pm ET on weekdays, 6pm ET on weekends
        - We should fetch data for the date that's currently "active"
        """
        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)
        
        # Determine if it's weekend (Saturday=5, Sunday=6)
        is_weekend = now_et.weekday() >= 5
        
        # Release times
        release_hour = 18 if is_weekend else 22  # 6pm weekend, 10pm weekday
        
        # If it's before release time, use yesterday's puzzle
        # If it's after release time, use today's puzzle
        if now_et.hour < release_hour:
            puzzle_date = (now_et - timedelta(days=1)).date()
        else:
            puzzle_date = now_et.date()
            
        return puzzle_date.strftime('%Y-%m-%d')
    
    async def run_historical_backfill(self, player_names):
        """Run year-to-date backfill for new players"""
        logger.info(f"Running year-to-date backfill for players: {player_names}")
        
        # Get current year start date
        current_year = datetime.now().year
        year_start = f"{current_year}-01-01"
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching data from {year_start} to {current_date}")
        
        # Modify sys.argv to simulate command line args for year-to-date backfill
        original_argv = sys.argv.copy()
        try:
            sys.argv = [
                'save_nyt.py',
                '--start-date', year_start,
                '--end-date', current_date,
                '--sql',
                '--type', 'all'
            ]
            
            # Add specific users if needed
            for player_name in player_names:
                sys.argv.extend(['--user', player_name])
                
            await save_nyt_main()
            logger.info(f"Year-to-date backfill completed for {player_names}")
            
        except Exception as e:
            logger.error(f"Error during year-to-date backfill: {e}")
        finally:
            sys.argv = original_argv
    
    async def run_daily_update(self):
        """Run daily data update for current puzzle date"""
        puzzle_date = self.get_nyt_puzzle_date()
        logger.info(f"Running daily update for puzzle date: {puzzle_date}")
        
        # Modify sys.argv to simulate command line args for daily update
        original_argv = sys.argv.copy()
        try:
            sys.argv = [
                'save_nyt.py',
                '--start-date', puzzle_date,
                '--end-date', puzzle_date,
                '--sql',
                '--type', 'all'
            ]
            
            await save_nyt_main()
            logger.info(f"Daily update completed for {puzzle_date}")
            
        except Exception as e:
            logger.error(f"Error during daily update: {e}")
        finally:
            sys.argv = original_argv
    
    async def run_service_cycle(self):
        """Run one complete service cycle"""
        logger.info("Starting NYT service cycle")
        
        # Load current state
        self.load_service_state()
        
        # Check for new players
        new_players = self.detect_new_players()
        
        # Run historical backfill for new players
        if new_players:
            await self.run_historical_backfill(new_players)
        
        # Run daily update
        await self.run_daily_update()
        
        logger.info("NYT service cycle completed")

async def main():
    """Main service entry point"""
    service = NYTService()
    
    try:
        await service.run_service_cycle()
    except Exception as e:
        logger.error(f"Service cycle failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 