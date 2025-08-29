-- View: matt.leaderboards
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.leaderboards AS

SELECT
  game_name,
  game_rank,
  player_name AS player,
  game_score AS score,
  points
FROM
  matt.game_view
WHERE
  ((guild_id = 'global') AND (game_date = curdate()))
ORDER BY
  game_name,
  coalesce(game_rank,999);
