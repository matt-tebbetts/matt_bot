# Database Views Summary

## 🔍 **Analysis of Your Database Views**

I extracted **23 views** from your `games` and `matt` schemas. Here's what I found:

### 📊 **Games Schema (8 views) - Your New Structure:**
1. **`daily_view`** - Daily game scores with rankings
2. **`game_view`** - ⭐ **MAIN VIEW** - Combines all games + mini crossword data
3. **`leaderboard_curr_month`** - Current month leaderboards
4. **`leaderboard_monthly`** - Monthly leaderboard aggregations
5. **`leaderboard_today`** - Today's game leaderboards
6. **`my_scores`** - Individual user score tracking
7. **`nyt_history_view`** - NYT puzzle history integration
8. **`winners_today`** - Daily winners by game

### 🎯 **Matt Schema (15 views) - Your Legacy Structure:**
1. **`game_view`** - Legacy game view (similar to games.game_view)
2. **`leaderboard_today`** - Legacy daily leaderboards
3. **`leaderboard_today_test`** - Test version of leaderboards
4. **`leaderboards`** - General leaderboard view
5. **`mini_current`** - Current mini crossword data
6. **`mini_latest`** - Latest mini crossword submissions
7. **`mini_leader_changed`** - Mini leadership change detection
8. **`mini_not_completed`** - Users who haven't done mini (used by warnings)
9. **`mini_run_checker`** - Mini completion checker
10. **`mini_view`** - ⭐ **MAIN MINI VIEW** - Complete mini crossword data
11. **`mini_view_linear`** - Linear mini progression view
12. **`mini_view_new`** - Updated mini view version
13. **`no_mini_yet`** - Users without mini attempts
14. **`travle`** - Specific travle game view
15. **`user_view`** - ⭐ **USER MAPPING** - Discord username → real name mapping

## 🔑 **Key Insights:**

### **Your Bot Currently Uses:**
- **`games.game_view`** - For most leaderboard queries (this is the main one!)
- **`games.daily_view`** - For daily game displays
- **`matt.mini_view`** - For mini crossword functionality
- **`matt.user_view`** - For converting Discord usernames to display names

### **The User Mapping Challenge:**
The `matt.user_view` is what maps Discord usernames to real names. Looking at the `games.game_view`, I can see it joins to:
```sql
join `matt`.`user_view` `y` on(((lower(`x`.`user_name`) = lower(`matt`.`y`.`member_nm`)) 
                               or (lower(`x`.`user_name`) = lower(`matt`.`y`.`alt_member_nm`))))
```

This means for new Discord servers, you'd need to either:
1. **Populate `matt.user_view`** with new server members, OR
2. **Create server-specific views** that don't require user mapping

### **Mini Crossword Dependencies:**
The mini functionality heavily relies on:
- `matt.mini_view` - Main mini data
- `matt.mini_not_completed` - For warning users
- `matt.user_view` - For user name mapping

## 💡 **Recommendations for Multi-Server Support:**

1. **Keep using `games.game_view`** - it's well-designed and handles all games
2. **For new servers**: Either populate `matt.user_view` OR create simplified views that use Discord usernames directly
3. **Mini features**: Will need setup for each server OR could be disabled for new servers

## 📂 **All View Definitions Available:**
Every view definition is now saved as readable SQL in this directory. You can easily see exactly how each view works and modify them as needed for multi-server support.
