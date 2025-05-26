# NYT Crossword Users Configuration

This directory contains configuration for collecting NYT crossword stats from multiple users.

## Setup

Edit `users.json` and add new users to the array:
   - `player_name`: Display name for the user
   - `nyt_s_cookie`: The NYT-S cookie string from their browser
   - `added_date`: Date when the user was added
   - `active`: Set to `false` to temporarily disable a user without deleting their data

## Getting NYT-S Cookie

To get your NYT-S cookie, follow steps 1 and 2 from this guide: https://xwstats.com/link

Quick summary:
1. Log into your NYT account at nytimes.com (make sure you have a paid NYT Games subscription)
2. Open browser developer tools (F12 or Chrome Menu → More Tools → Developer Tools)
3. Go to Application tab → Cookies → https://nytimes.com
4. Find the cookie named "NYT-S" and copy its entire value

**Note:** Only follow steps 1-2 from the linked guide - we're using the cookie for our own data collection, not submitting it to xwstats.

## Security

- `users.json` is gitignored to keep cookie data secure
- Never commit actual cookie values to version control
- Cookies may expire and need to be updated periodically

## Usage

Run the multi-user script:

```bash
# Process all active users
python bot/functions/save_nyt.py

# Process specific user only
python bot/functions/save_nyt.py -u "Matt"

# Custom date range
python bot/functions/save_nyt.py -s 2024-01-01 -e 2024-12-31

# Different puzzle type
python bot/functions/save_nyt.py -t mini

# Output format options
python bot/functions/save_nyt.py                # Master JSON only (default)
python bot/functions/save_nyt.py --format csv   # Individual CSV files by user/date
python bot/functions/save_nyt.py --format both  # Both master JSON + individual CSVs

# The default creates one master file: files/nyt_stats/nyt_crossword_data.json
# This contains ALL players and ALL puzzle types with smart merging

# Custom output directory
python bot/functions/save_nyt.py -o "custom/path"  # Default: files/nyt_stats/
``` 