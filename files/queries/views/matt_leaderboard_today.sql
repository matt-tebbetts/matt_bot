-- View: matt.leaderboard_today
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.leaderboard_today AS

WITH
  combined_players as (
SELECT
  guild_id,
  guild_nm,
  game_name,
  player_name,
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
        THEN game_score end)) AS game_score,
  max((
    CASE
      WHEN (game_date = curdate())
        THEN points end)) AS points
FROM
  matt.game_view gv
WHERE
  (game_date between if((curtime() > '16:00:00'),(curdate() - interval 1 week),
  curdate()) AND curdate())
GROUP BY
  guild_id,
  guild_nm,
  game_name,
  player_name)
SELECT
  cp.guild_id AS guild_id,
  cp.guild_nm AS guild_nm,
  curdate() AS game_date,
  cp.game_name AS game_name,
  coalesce(cast(cp.game_rank as char charset utf8mb4),'') AS game_rank,
  cp.player_name AS player_name,
  if((cp.game_date = curdate()),
  cp.game_score,'') AS game_score,
  if((cp.game_date = curdate()),
  cp.points,'') AS points,
  ROW_NUMBER() OVER (PARTITION BY cp.guild_id,
  cp.game_name
ORDER BY
  (cp.game_date = curdate()) desc,
  coalesce(cp.game_rank,999),
  cp.player_name )  AS sort_logic
FROM
  combined_players cp
ORDER BY
  cp.guild_id,
  cp.game_name,
  sort_logic;
