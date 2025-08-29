-- View: matt.game_view
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.game_view AS

WITH
  all_games as (
SELECT
  x.game_date AS game_date,
  x.game_name AS game_name,
  x.game_score AS game_score,
  x.added_ts AS added_ts,
  x.discord_id AS discord_id,
  x.game_dtl AS game_dtl,
  g.scoring_type AS scoring_type,
  ROW_NUMBER() OVER (PARTITION BY x.game_name,
  x.game_date,
  x.discord_id
ORDER BY
  x.added_ts )  AS added_rank,(
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
  (matt.game_history x
JOIN
  matt.game_details g on((x.game_name = g.game_name)))), games_by_guild as (
SELECT
  x.game_date AS game_date,
  x.game_name AS game_name,
  x.game_score AS game_score,
  x.added_ts AS added_ts,
  x.discord_id AS discord_id,
  x.game_dtl AS game_dtl,
  x.scoring_type AS scoring_type,
  x.added_rank AS added_rank,
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
  guild_id,
  guild_nm,
  player_name,
  member_nm
FROM
  (all_games x
JOIN
  matt.user_view y on(((lower(x.discord_id) = lower(member_nm)) OR (lower(x.discord_id) = lower(alt_member_nm)))))
WHERE
  (x.added_rank = 1)), combined as (
SELECT
  games_by_guild.guild_id AS guild_id,
  games_by_guild.guild_nm AS guild_nm,
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
  games_by_guild.game_dtl AS game_dtl
FROM
  games_by_guild
UNION ALL
SELECT
  guild_id,
  guild_nm,'mini' AS game_name,
  game_date,
  player_name,
  member_nm,
  game_time AS game_score,
  game_rank,1 AS game_completed,
  cast(points as signed) AS points,
  seconds,
  added_ts,
  NULL AS game_dtl
FROM
  matt.mini_view)
SELECT
  combined.guild_id AS guild_id,
  combined.guild_nm AS guild_nm,
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
  combined.game_dtl AS game_dtl,
  ROW_NUMBER() OVER (PARTITION BY combined.guild_id,
  combined.player_name,
  combined.game_name
ORDER BY
  combined.game_date )  AS player_game_nbr
FROM
  combined;
