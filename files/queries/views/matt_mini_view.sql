-- View: matt.mini_view
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_view AS

WITH
  mini_history_latest as (
SELECT
  x.game_date AS game_date,
  x.player_id AS player_id,
  x.game_time AS game_time,
  x.added_ts AS added_ts,
  x.added_rank AS added_rank,0 AS from_cookie
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
  (x.added_rank = 1)
UNION ALL
SELECT
  print_date,(
    CASE
      WHEN (player_name = 'Brice')
        THEN 'acowinthecrowd'
      WHEN (player_name = 'Whit')
        THEN 'croasus'
      WHEN (player_name = 'Zach')
        THEN 'Throoper'
      WHEN (player_name = 'Matt')
        THEN 'Matt'
      WHEN (player_name = 'Sally')
        THEN 'mama56'
      WHEN (player_name = 'Andy')
        THEN 'Andy'
      WHEN (player_name = 'Ryan')
        THEN 'Tuckle'
      WHEN (player_name = 'Andrew')
        THEN 'aromatt'
      WHEN (player_name = 'Ben')
        THEN 'Benji'
      WHEN (player_name = 'Steve')
        THEN 'RabbiFerret'
      ELSE player_name end) AS player_id,
  concat(floor((solving_seconds / 60)),':',
  lpad((solving_seconds % 60),2,'0')) AS game_time,
  left(solved_datetime,19) AS added_ts,1 AS added_rank,1 AS from_cookie
FROM
  games.nyt_history
WHERE
  ((puzzle_type = 'mini') AND (solved = 1))), mini_history_no_dupes as (
SELECT
  mini_history_latest.game_date AS game_date,
  mini_history_latest.player_id AS player_id,
  mini_history_latest.game_time AS game_time,
  mini_history_latest.added_ts AS added_ts,
  mini_history_latest.added_rank AS added_rank,
  mini_history_latest.from_cookie AS from_cookie,
  ROW_NUMBER() OVER (PARTITION BY mini_history_latest.game_date,
  mini_history_latest.player_id
ORDER BY
  mini_history_latest.added_ts desc )  AS rnk
FROM
  mini_history_latest), mini as (
SELECT
  distinct guild_id,
  guild_nm,
  x.game_date AS game_date,
  player_name,
  member_nm,
  x.game_time AS game_time,((60 * substring_index(x.game_time,':',1)) + substring_index(x.game_time,':',-(1))) AS seconds,
  DENSE_RANK() OVER (PARTITION BY player_name
ORDER BY
  x.game_date )  AS player_game_nbr,
  x.added_ts AS added_ts,
  DENSE_RANK() OVER (PARTITION BY guild_nm,
  x.game_date
ORDER BY
  ((60 * substring_index(x.game_time,':',1)) + substring_index(x.game_time,':',-(1))) )  AS game_rank,
  x.from_cookie AS from_cookie
FROM
  (mini_history_no_dupes x
JOIN
  matt.user_view y on((lower(x.player_id) = lower(nyt_id))))
WHERE
  ((x.rnk = 1) AND (guild_id = 'global'))), mini_final as (
SELECT
  mini.guild_id AS guild_id,
  mini.guild_nm AS guild_nm,
  mini.game_date AS game_date,
  mini.player_name AS player_name,
  mini.member_nm AS member_nm,
  mini.game_time AS game_time,
  mini.seconds AS seconds,
  mini.player_game_nbr AS player_game_nbr,
  mini.added_ts AS added_ts,
  mini.game_rank AS game_rank,(
    CASE
      WHEN (mini.game_rank > 10)
        THEN 0
      ELSE pow((11 - mini.game_rank),2) end) AS points
FROM
  mini)
SELECT
  mini_final.guild_id AS guild_id,
  mini_final.guild_nm AS guild_nm,
  mini_final.game_date AS game_date,
  mini_final.player_name AS player_name,
  mini_final.member_nm AS member_nm,
  mini_final.game_time AS game_time,
  mini_final.seconds AS seconds,
  mini_final.player_game_nbr AS player_game_nbr,
  mini_final.added_ts AS added_ts,
  mini_final.game_rank AS game_rank,
  mini_final.points AS points
FROM
  mini_final;
