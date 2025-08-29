-- View: games.leaderboard_curr_month
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.leaderboard_curr_month AS

SELECT
  game_name,
  month_rank,
  player_name,
  points,
  wins,
  top5,
  avg_rank,
  games_played AS games
FROM
  games.leaderboard_monthly
WHERE
  (0 <> is_curr_month);
