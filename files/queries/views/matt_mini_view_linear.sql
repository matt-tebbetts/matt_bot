-- View: matt.mini_view_linear
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_view_linear AS

SELECT
  'mini' AS game_name,
  z.guild_id AS guild_id,
  z.guild_nm AS guild_nm,
  z.game_date AS game_date,
  z.player_name AS player_name,
  z.game_time AS game_score,
  z.seconds AS seconds,
  z.game_nbr AS game_nbr,
  z.player_game_nbr AS player_game_nbr,
  z.added_ts AS added_ts,
  z.game_rank AS game_rank,(
    CASE
      WHEN (z.game_rank > 10)
        THEN 0
      ELSE (10 * (11 - z.game_rank)) end) AS points
FROM
  (
SELECT
  a.player_id AS player_id,
  a.player_name AS player_name,
  a.game_date AS game_date,
  a.game_time AS game_time,
  a.seconds AS seconds,
  a.game_nbr AS game_nbr,
  a.player_game_nbr AS player_game_nbr,
  a.added_ts AS added_ts,
  a.guild_id AS guild_id,
  a.guild_nm AS guild_nm,
  DENSE_RANK() OVER (PARTITION BY a.guild_nm,
  a.game_date
ORDER BY
  a.seconds )  AS game_rank
FROM
  (
SELECT
  distinct a.player_id AS player_id,
  player_name,
  a.game_date AS game_date,
  a.game_time AS game_time,((60 * substring_index(a.game_time,':',1)) + substring_index(a.game_time,':',-(1))) AS seconds,
  DENSE_RANK() OVER (
ORDER BY
  a.game_date )  AS game_nbr,
  DENSE_RANK() OVER (PARTITION BY player_name
ORDER BY
  a.game_date )  AS player_game_nbr,
  a.added_ts AS added_ts,
  guild_id,
  guild_nm
FROM
  ((matt.mini_history a
JOIN
  (
SELECT
  game_date,
  player_id,
  min(added_ts) AS added_ts
FROM
  matt.mini_history
GROUP BY
  game_date,
  player_id) b on(((a.game_date = b.game_date) AND (a.player_id = b.player_id) AND (a.added_ts = b.added_ts))))
JOIN
  matt.user_view c on((lower(a.player_id) = lower(nyt_id))))) a) z;
