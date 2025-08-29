-- View: matt.leaderboard_today_test
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.leaderboard_today_test AS

WITH
  combined_players as (
SELECT
  distinct guild_id,
  guild_nm,
  game_name,
  player_name,(
    CASE
      WHEN (game_date = curdate())
        THEN game_date
      ELSE NULL end) AS game_date,(
    CASE
      WHEN (game_date = curdate())
        THEN game_rank
      ELSE NULL end) AS game_rank,(
    CASE
      WHEN (game_date = curdate())
        THEN game_score
      ELSE NULL end) AS game_score,(
    CASE
      WHEN (game_date = curdate())
        THEN points
      ELSE NULL end) AS points
FROM
  matt.game_view gv
WHERE
  (game_date between (curdate() - interval 1 week) AND curdate()))
SELECT
  cp.guild_id AS guild_id,
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
  cp.game_rank,
  cp.player_name )  AS sort_logic
FROM
  combined_players cp
ORDER BY
  cp.guild_id,
  cp.game_name,
  sort_logic;
