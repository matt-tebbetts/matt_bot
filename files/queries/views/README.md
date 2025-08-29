# Database Views Index

This directory contains all database views extracted from the `games` and `matt` schemas.

## 📊 Games Schema Views

- **daily_view** - [View Definition](games_daily_view.sql)
- **game_view** - [View Definition](games_game_view.sql)
- **leaderboard_curr_month** - [View Definition](games_leaderboard_curr_month.sql)
- **leaderboard_monthly** - [View Definition](games_leaderboard_monthly.sql)
- **leaderboard_today** - [View Definition](games_leaderboard_today.sql)
- **my_scores** - [View Definition](games_my_scores.sql)
- **nyt_history_view** - [View Definition](games_nyt_history_view.sql)
- **winners_today** - [View Definition](games_winners_today.sql)

## 🎯 Matt Schema Views

- **game_view** - [View Definition](matt_game_view.sql)
- **leaderboard_today** - [View Definition](matt_leaderboard_today.sql)
- **leaderboard_today_test** - [View Definition](matt_leaderboard_today_test.sql)
- **leaderboards** - [View Definition](matt_leaderboards.sql)
- **mini_current** - [View Definition](matt_mini_current.sql)
- **mini_latest** - [View Definition](matt_mini_latest.sql)
- **mini_leader_changed** - [View Definition](matt_mini_leader_changed.sql)
- **mini_not_completed** - [View Definition](matt_mini_not_completed.sql)
- **mini_run_checker** - [View Definition](matt_mini_run_checker.sql)
- **mini_view** - [View Definition](matt_mini_view.sql)
- **mini_view_linear** - [View Definition](matt_mini_view_linear.sql)
- **mini_view_new** - [View Definition](matt_mini_view_new.sql)
- **no_mini_yet** - [View Definition](matt_no_mini_yet.sql)
- **travle** - [View Definition](matt_travle.sql)
- **user_view** - [View Definition](matt_user_view.sql)

## 📝 Notes

- Views were extracted on: 2025-08-25
- Total views found: 23
- Games schema: 8 views
- Matt schema: 15 views

## 🔄 Updating Views

To refresh these views, run:
```bash
python3 extract_views.py
```
