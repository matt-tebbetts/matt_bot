# Universal Discord Server Support

This document outlines the changes made to make Matt Bot work seamlessly with any Discord server without manual configuration.

## ✅ **Fixed Issues - Now Server-Agnostic:**

### **1. User Name Handling**
- **Before**: Required manual mapping in `user_details` table to convert Discord usernames to "real names"
- **After**: Uses Discord usernames directly as display names via `games.universal_game_view`
- **Impact**: No manual user setup required for new servers

### **2. Database Dependencies**
- **Before**: Hard dependency on `matt.game_details` and server-specific views
- **After**: Uses `games.game_config` table populated from `games.json`
- **Impact**: Self-contained configuration, no external table dependencies

### **3. SQL Queries Updated**
All active queries now use `games.universal_game_view`:
- ✅ `daily_games.sql` 
- ✅ `game_aggregate_stats.sql`
- ✅ `daily_myscores.sql`
- ✅ `daily_winners.sql`

### **4. Code Analysis - No Hardcoded Values**
- ✅ **User Names**: Uses `message.author.name` dynamically
- ✅ **Server IDs**: Guild configs saved automatically per server
- ✅ **Game Config**: All games defined in `games.json` (server-agnostic)
- ✅ **Commands**: Dynamically generated from `games.json`

## ⚠️ **Remaining Dependencies (Minor)**

### **1. Mini Crossword Integration**
**Location**: `bot/functions/mini_warning.py`
```python
# Lines 40, 113 - Still references matt.* tables
result = await execute_query("SELECT * FROM matt.mini_not_completed")
query = "SELECT ... FROM matt.mini_view WHERE ..."
```

**Impact**: Mini crossword features won't work on new servers
**Solution**: Either disable mini features for new servers OR create universal mini tables

### **2. Environment Configuration**
**Location**: `bot/connections/config.py`
```python
# Lines 21-25 - Platform-based token selection
if IS_LINUX:
    BOT_TOKEN = os.getenv("MATT_BOT")    # Production
else:
    BOT_TOKEN = os.getenv("TEST_BOT")    # Development
```

**Impact**: Need separate bot tokens for prod vs test
**Solution**: This is actually good - allows testing without affecting production

## 🚀 **Migration Instructions**

### **For New Discord Servers:**

1. **Invite the bot** to your Discord server
2. **Run migration SQL** on your database:
   ```bash
   mysql -h your_host -u user -p < files/queries/active/migration_to_universal.sql
   ```
3. **Start using the bot** - it will automatically:
   - Create guild config for your server
   - Start saving game scores
   - Generate leaderboard commands

### **Database Requirements:**
- `games.game_history` table (for storing scores)
- `games.game_config` table (created by migration)
- `games.universal_game_view` view (created by migration)

### **No Manual Setup Needed:**
- ❌ No user mapping required
- ❌ No server-specific configuration
- ❌ No hardcoded Discord IDs
- ❌ No manual game configuration

## 🎯 **What Works Out of the Box:**

### **Game Score Detection & Saving**
- All games from `games.json` automatically detected
- Scores saved with Discord usernames
- Automatic ranking and points calculation

### **Leaderboard Commands**
- `/pips`, `/pips_easy`, `/pips_medium` 
- `/wordle`, `/connections`, `/crosswordle`
- All other games defined in `games.json`

### **User Experience**
- `my_scores` command works with Discord usernames
- Winners display uses Discord usernames
- Aggregate stats work across time periods

## 🔧 **Optional Enhancements for New Servers:**

### **Custom Display Names**
If you want prettier display names instead of Discord usernames:

1. Create a `games.user_display_names` table:
   ```sql
   CREATE TABLE games.user_display_names (
       discord_username VARCHAR(100) PRIMARY KEY,
       display_name VARCHAR(100) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. Update `universal_game_view` to use COALESCE:
   ```sql
   COALESCE(d.display_name, h.user_name) AS player_name
   ```

### **Mini Crossword Support**
If you want mini crossword features:

1. Set up mini crossword data source
2. Create universal mini tables/views
3. Update `mini_warning.py` to use universal queries

## 📊 **Testing Checklist for New Servers:**

- [ ] Bot joins server successfully
- [ ] Game scores are detected and saved
- [ ] Leaderboard commands work (`/wordle`, `/pips`, etc.)
- [ ] `my_scores` command shows user's games
- [ ] Winners display correctly
- [ ] Aggregate stats work for date ranges
- [ ] Emoji reactions appear on game scores

## 🎉 **Result:**

Matt Bot can now be added to any Discord server and will:
1. **Automatically detect** game scores from supported games
2. **Generate leaderboards** without manual configuration  
3. **Use Discord usernames** as display names
4. **Work immediately** without database setup beyond the migration

The only server-specific data stored is in `files/guilds/{guild_name}/` for message history and guild configuration - all managed automatically by the bot.
