-- View: games.leaderboard_monthly
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.leaderboard_monthly AS

WITH
  daily_games as (
SELECT
  game_name,
  game_date,
  game_rank,
  player_name,
  game_score,
  points,
  concat(year(game_date),
  lpad(month(game_date),2,'0')) AS game_month,
  concat(year(game_date),'-',
  upper(date_format(game_date,'%b'))) AS game_month_name,(
    CASE
      WHEN ((year(game_date) = year(curdate())) AND (month(game_date) = month(curdate())))
        THEN true
      ELSE false end) AS is_curr_month,(
    CASE
      WHEN ((year(game_date) = year((curdate() - interval 1 month))) AND (month(game_date) = month((curdate() - interval 1 month))))
        THEN true
      ELSE false end) AS is_prev_month
FROM
  matt.game_view
WHERE
  (guild_id = 'global')), monthly_leaderboard as (
SELECT
  daily_games.is_curr_month AS is_curr_month,
  daily_games.is_prev_month AS is_prev_month,
  daily_games.game_month AS game_month,
  daily_games.game_name AS game_name,
  daily_games.player_name AS player_name,
  sum(daily_games.points) AS points,
  round(avg(daily_games.game_rank),1) AS avg_rank,
  sum((
    CASE
      WHEN (daily_games.game_rank = 1)
        THEN 1
      ELSE 0 end)) AS wins,
  round((sum((
    CASE
      WHEN (daily_games.game_rank <= 5)
        THEN 1
      ELSE 0 end)) / sum(1.00)),3) AS top5,
  count(0) AS games_played
FROM
  daily_games
GROUP BY
  daily_games.is_curr_month,
  daily_games.is_prev_month,
  daily_games.game_month,
  daily_games.game_name,
  daily_games.player_name), final_leaderboard as (
SELECT
  monthly_leaderboard.is_curr_month AS is_curr_month,
  monthly_leaderboard.is_prev_month AS is_prev_month,
  monthly_leaderboard.game_month AS game_month,
  monthly_leaderboard.game_name AS game_name,
  monthly_leaderboard.player_name AS player_name,
  monthly_leaderboard.points AS points,
  monthly_leaderboard.avg_rank AS avg_rank,
  monthly_leaderboard.wins AS wins,
  monthly_leaderboard.top5 AS top5,
  monthly_leaderboard.games_played AS games_played,
  DENSE_RANK() OVER (PARTITION BY monthly_leaderboard.game_name,
  monthly_leaderboard.game_month
ORDER BY
  monthly_leaderboard.points desc )  AS month_rank
FROM
  monthly_leaderboard)
SELECT
  final_leaderboard.is_curr_month AS is_curr_month,
  final_leaderboard.is_prev_month AS is_prev_month,
  final_leaderboard.game_month AS game_month,
  final_leaderboard.game_name AS game_name,
  final_leaderboard.player_name AS player_name,
  final_leaderboard.points AS points,
  final_leaderboard.avg_rank AS avg_rank,
  final_leaderboard.wins AS wins,
  final_leaderboard.top5 AS top5,
  final_leaderboard.games_played AS games_played,
  final_leaderboard.month_rank AS month_rank
FROM
  final_leaderboard;
