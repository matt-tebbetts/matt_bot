-- View: matt.mini_view_new
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_view_new AS

WITH
  mini as (
SELECT
  x.game_date AS game_date,
  x.player_id AS player_id,
  x.game_time AS game_time,
  x.added_ts AS added_ts
FROM
  (
SELECT
  game_date,
  player_id,
  game_time,
  added_ts,
  ROW_NUMBER() OVER (PARTITION BY game_date,
  player_id
ORDER BY
  added_ts )  AS added_rank
FROM
  matt.mini_history) x
WHERE
  (x.added_rank = 1)), users as (
SELECT
  distinct a.nyt_id AS nyt_id,
  a.player_name AS player_name,
  b.guild_nm AS guild_nm
FROM
  (matt.user_details a
JOIN
  matt.user_history b on((a.discord_id = b.member_nm)))
WHERE
  (a.nyt_id is not null)
UNION ALL
SELECT
  distinct a.nyt_id AS nyt_id,
  a.player_name AS player_name,'Global' AS guild_nm
FROM
  matt.user_details a
WHERE
  (a.nyt_id is not null)), guild_leaderboards as (
SELECT
  distinct y.guild_nm AS guild_nm,
  x.game_date AS game_date,
  DENSE_RANK() OVER (PARTITION BY y.guild_nm,
  x.game_date
ORDER BY
  x.game_time )  AS game_rank,(
    CASE
      WHEN (DENSE_RANK() OVER (PARTITION BY y.guild_nm,
  x.game_date
ORDER BY
  x.game_time )  > 10)
        THEN 0
      ELSE pow((11 - DENSE_RANK() OVER (PARTITION BY y.guild_nm,
  x.game_date
ORDER BY
  x.game_time ) ),2) end) AS points,
  y.player_name AS player_name,
  x.game_time AS game_time,
  x.added_ts AS added_ts,((60 * substring_index(x.game_time,':',1)) + substring_index(x.game_time,':',-(1))) AS seconds,
  DENSE_RANK() OVER (PARTITION BY y.player_name
ORDER BY
  x.game_date )  AS player_game_nbr
FROM
  (mini x
JOIN
  users y on((lower(x.player_id) = lower(y.nyt_id)))))
SELECT
  guild_leaderboards.guild_nm AS guild_nm,
  guild_leaderboards.game_date AS game_date,
  guild_leaderboards.game_rank AS game_rank,
  guild_leaderboards.points AS points,
  guild_leaderboards.player_name AS player_name,
  guild_leaderboards.game_time AS game_time,
  guild_leaderboards.added_ts AS added_ts,
  guild_leaderboards.seconds AS seconds,
  guild_leaderboards.player_game_nbr AS player_game_nbr
FROM
  guild_leaderboards
WHERE
  (guild_leaderboards.game_date = curdate())
ORDER BY
  guild_leaderboards.guild_nm,
  guild_leaderboards.game_rank;
