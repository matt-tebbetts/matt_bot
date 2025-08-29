-- View: games.leaderboard_today
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.leaderboard_today AS

WITH
  combined_players as (
SELECT
  game_name AS game,
  player_name AS player,
  max((
    CASE
      WHEN (game_date = curdate())
        THEN game_date end)) AS game_date,
  max((
    CASE
      WHEN (game_date = curdate())
        THEN game_rank end)) AS game_rank,
  max((
    CASE
      WHEN (game_date = curdate())
        THEN game_score end)) AS score,
  max((
    CASE
      WHEN (game_date = curdate())
        THEN points end)) AS points
FROM
  games.game_view gv
WHERE
  (game_date = curdate())
GROUP BY
  game_name,
  player_name)
SELECT
  combined_players.game AS game,
  coalesce(cast(combined_players.game_rank as char charset utf8mb4),'') AS rnk,
  combined_players.player AS player,
  if((combined_players.game_date = curdate()),
  combined_players.score,'') AS score,
  if((combined_players.game_date = curdate()),
  combined_players.points,'') AS points,
  ROW_NUMBER() OVER (PARTITION BY combined_players.game
ORDER BY
  (combined_players.game_date = curdate()) desc,
  coalesce(combined_players.game_rank,999),
  combined_players.player )  AS sort_logic
FROM
  combined_players
ORDER BY
  combined_players.game,
  sort_logic;
