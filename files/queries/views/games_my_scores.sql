-- View: games.my_scores
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.my_scores AS

WITH
  recent_games as (
SELECT
  distinct game_name
FROM
  matt.game_history
WHERE
  (game_date > (curdate() - interval 1 week))
UNION ALL
SELECT
  'mini' AS game_name), recent_players as (
SELECT
  distinct discord_id
FROM
  matt.game_history
WHERE
  (game_date > (curdate() - interval 1 week))), matrix as (
SELECT
  recent_games.game_name AS game_name,
  recent_players.discord_id AS discord_id
FROM
  (recent_games
JOIN
  recent_players)), player_scores as (
SELECT
  member_nm,
  game_name,
  game_score,
  game_rank
FROM
  matt.game_view
WHERE
  ((guild_nm = 'global') AND (game_date = curdate())))
SELECT
  a.discord_id AS discord_nm,
  a.game_name AS game,
  coalesce(b.game_score,'-') AS score,
  coalesce(b.game_rank,'-') AS rnk
FROM
  (matrix a
LEFT
JOIN
  player_scores b on(((a.game_name = b.game_name) AND (a.discord_id = b.member_nm))))
ORDER BY
  a.game_name;
