-- View: games.game_view
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.game_view AS

WITH
  latest_records as (
SELECT
  id,
  added_ts,
  user_name,
  game_name,
  game_score,
  game_date,
  game_detail,
  game_bonuses,
  source_desc,
  ROW_NUMBER() OVER (PARTITION BY game_name,
  game_date,
  user_name
ORDER BY
  added_ts desc )  AS added_rank
FROM
  games.game_history
UNION ALL
SELECT
  NULL AS id,
  NULL AS added_ts,(
    CASE
      WHEN (player_name = 'Whit')
        THEN 'croasus'
      WHEN (player_name = 'Brice')
        THEN 'acowinthewcrowd'
      WHEN (player_name = 'Zach')
        THEN 'cryingprincess'
      WHEN (player_name = 'Matt')
        THEN 'svendiamond'
      WHEN (player_name = 'Andy')
        THEN 'scratchysaurus'
      WHEN (player_name = 'Ryan')
        THEN 'tuckletheknuckle'
      WHEN (player_name = 'Sally')
        THEN 'sat1056'
      WHEN (player_name = 'Bob')
        THEN 'SSIBob'
      WHEN (player_name = 'Steve')
        THEN 'RabbiFerret'
      ELSE player_name end) AS user_name,'daily' AS game_name,
  concat(floor((solving_seconds / 60)),':',
  lpad((solving_seconds % 60),2,'0')) AS game_score,
  print_date AS game_date,
  NULL AS game_detail,
  NULL AS game_bonuses,
  NULL AS source_desc,1 AS added_rank
FROM
  games.nyt_history
WHERE
  ((puzzle_type = 'daily') AND (solved = 1))), all_games as (
SELECT
  x.game_date AS game_date,
  x.game_name AS game_name,
  x.game_score AS game_score,
  x.added_ts AS added_ts,
  x.user_name AS user_name,
  x.game_detail AS game_detail,
  g.scoring_type AS scoring_type,(
    CASE
      WHEN (g.scoring_type = 'timed')
        THEN cast(((substring_index(x.game_score,':',1) * 60) + substring_index(x.game_score,':',-(1))) as signed)
      WHEN (g.scoring_type = 'guesses')
        THEN (
    CASE
      WHEN (left(x.game_score,1) in ('X','?'))
        THEN 0
      WHEN regexp_like(substring_index(x.game_score,'/',1),'^-?[0-9]+$')
        THEN cast(substring_index(x.game_score,'/',1) as signed)
      WHEN (left(x.game_score,1) = '+')
        THEN cast(replace(x.game_score,'+','') as signed)
      ELSE NULL end)
      WHEN (g.scoring_type = 'points')
        THEN (
    CASE
      WHEN regexp_like(x.game_score,'^-?[0-9]+$')
        THEN cast(x.game_score as signed)
      ELSE NULL end) end) AS score_as_int,(
    CASE
      WHEN ((left(x.game_score,1) in ('X','?')) OR ((x.game_name = 'boxoffice') AND (x.game_score = '0')))
        THEN 0
      ELSE 1 end) AS game_completed
FROM
  (latest_records x
LEFT
JOIN
  games.game_details g on((x.game_name = g.game_name)))
WHERE
  (x.added_rank = 1)), games_by_guild as (
SELECT
  x.game_date AS game_date,
  x.game_name AS game_name,
  x.game_score AS game_score,
  x.added_ts AS added_ts,
  x.user_name AS user_name,
  x.game_detail AS game_detail,
  x.scoring_type AS scoring_type,
  x.score_as_int AS score_as_int,
  x.game_completed AS game_completed,(
    CASE
      WHEN (x.game_completed = 0)
        THEN NULL
      ELSE (
    CASE
      WHEN (x.scoring_type in ('timed','guesses'))
        THEN DENSE_RANK() OVER (PARTITION BY guild_nm,
  x.game_date,
  x.game_name
ORDER BY
  x.game_completed desc,
  x.score_as_int )
      WHEN (x.scoring_type = 'points')
        THEN DENSE_RANK() OVER (PARTITION BY guild_nm,
  x.game_date,
  x.game_name
ORDER BY
  x.score_as_int desc )  end) end) AS game_rank,
  player_name,
  member_nm
FROM
  (all_games x
JOIN
  matt.user_view y on(((lower(x.user_name) = lower(member_nm)) OR (lower(x.user_name) = lower(alt_member_nm)))))
WHERE
  (guild_nm = 'global')), combined as (
SELECT
  games_by_guild.game_name AS game_name,
  games_by_guild.game_date AS game_date,
  games_by_guild.player_name AS player_name,
  games_by_guild.member_nm AS member_nm,
  games_by_guild.game_score AS game_score,
  games_by_guild.game_rank AS game_rank,
  games_by_guild.game_completed AS game_completed,
  cast((
    CASE
      WHEN (games_by_guild.game_completed = 0)
        THEN 0
      ELSE pow((11 - games_by_guild.game_rank),2) end) as signed) AS points,(
    CASE
      WHEN (games_by_guild.score_as_int = 0)
        THEN NULL
      ELSE games_by_guild.score_as_int end) AS seconds,
  games_by_guild.added_ts AS added_ts,
  games_by_guild.game_detail AS game_detail
FROM
  games_by_guild
UNION ALL
SELECT
  'mini' AS game_name,
  game_date,
  player_name,
  member_nm,
  game_time AS game_score,
  game_rank,1 AS game_completed,
  cast(points as signed) AS points,
  seconds,
  added_ts,
  NULL AS game_detail
FROM
  matt.mini_view
WHERE
  (guild_id = 'global'))
SELECT
  combined.game_name AS game_name,
  combined.game_date AS game_date,
  combined.player_name AS player_name,
  combined.member_nm AS member_nm,
  combined.game_score AS game_score,
  combined.game_rank AS game_rank,
  combined.game_completed AS game_completed,
  combined.points AS points,
  combined.seconds AS seconds,
  combined.added_ts AS added_ts,
  combined.game_detail AS game_detail,
  ROW_NUMBER() OVER (PARTITION BY combined.player_name,
  combined.game_name
ORDER BY
  combined.game_date )  AS player_game_nbr
FROM
  combined;
