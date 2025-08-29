-- View: matt.mini_leader_changed
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_leader_changed AS

WITH
  latest_runs as (
SELECT
  distinct added_ts
FROM
  matt.mini_history
ORDER BY
  added_ts desc limit 2), winners as (
SELECT
  x.guild_id AS guild_id,
  x.guild_nm AS guild_nm,
  x.player_name AS player_name,
  x.game_time AS game_time,
  x.game_rank AS game_rank,
  x.added_ts AS added_ts,
  DENSE_RANK() OVER (PARTITION BY x.guild_id
ORDER BY
  x.added_ts desc )  AS added_rank
FROM
  (
SELECT
  a.game_date AS game_date,
  a.guild_id AS guild_id,
  a.guild_nm AS guild_nm,
  a.player_name AS player_name,
  a.game_time AS game_time,
  a.added_ts AS added_ts,
  DENSE_RANK() OVER (PARTITION BY a.guild_id,
  a.game_date,
  a.added_ts
ORDER BY
  a.game_time )  AS game_rank
FROM
  (
SELECT
  x.game_date AS game_date,
  guild_id,
  guild_nm,
  player_name,
  x.game_time AS game_time,
  x.added_ts AS added_ts
FROM
  ((matt.mini_history x
JOIN
  matt.user_view y on((lower(x.player_id) = lower(nyt_id))))
JOIN
  latest_runs r on((x.added_ts = r.added_ts)))) a) x
WHERE
  (x.game_rank = 1)), current_winners as (
SELECT
  winners.guild_id AS guild_id,
  winners.guild_nm AS guild_nm,
  winners.player_name AS player_name,
  winners.game_time AS game_time,
  winners.game_rank AS game_rank,
  winners.added_ts AS added_ts,
  winners.added_rank AS added_rank
FROM
  winners
WHERE
  (winners.added_rank = 1)), previous_winners as (
SELECT
  winners.guild_id AS guild_id,
  winners.guild_nm AS guild_nm,
  winners.player_name AS player_name,
  winners.game_time AS game_time,
  winners.game_rank AS game_rank,
  winners.added_ts AS added_ts,
  winners.added_rank AS added_rank
FROM
  winners
WHERE
  (winners.added_rank = 2))
SELECT
  current_winners.guild_id AS guild_id,
  current_winners.guild_nm AS guild_nm,
  current_winners.player_name AS player_name,
  current_winners.game_time AS game_time,
  current_winners.game_rank AS game_rank,
  current_winners.added_ts AS added_ts,
  current_winners.added_rank AS added_rank
FROM
  current_winners
WHERE
  (current_winners.guild_id,
  current_winners.player_name) in (
SELECT
  previous_winners.guild_id,
  previous_winners.player_name
FROM
  previous_winners) is false;
