-- View: games.daily_view
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.daily_view AS

WITH
  raw_games as (
SELECT
  game_date,
  game_detail,
  source_desc,
  user_name,
  concat(upper(left(game_name,1)),
  lower(substr(game_name,2))) AS game_name,
  game_score,(
    CASE
      WHEN ((game_score like '%:%') AND regexp_like(game_score,'^[0-9]+:[0-5][0-9]$'))
        THEN ((cast(substring_index(game_score,':',1) as unsigned) * 60) + cast(substring_index(game_score,':',-(1)) as unsigned))
      WHEN ((game_score like '%/%') AND regexp_like(substring_index(game_score,'/',1),'^-?[0-9]+$'))
        THEN cast(substring_index(game_score,'/',1) as signed)
      WHEN ((game_score like '+%') AND regexp_like(replace(game_score,'+',''),'^[0-9]+$'))
        THEN cast(replace(game_score,'+','') as signed)
      WHEN (left(game_score,1) in ('X','?'))
        THEN 0
      WHEN regexp_like(game_score,'^-?[0-9]+$')
        THEN cast(game_score as signed)
      ELSE NULL end) AS score_as_int,
  game_bonuses,
  added_ts,(
    CASE
      WHEN ((game_score like '%X%') OR (game_score like '%?%'))
        THEN 0
      ELSE 1 end) AS game_completed
FROM
  games.game_history), raw_nyt as (
SELECT
  print_date AS game_date,
  dayname(print_date) AS game_detail,'NYT_Automated' AS source_desc,
  player_name AS user_name,
  puzzle_type AS game_name,(
    CASE
      WHEN (solving_seconds >= 3600)
        THEN time_format(sec_to_time(solving_seconds),'%k:%i:%s')
      ELSE concat(floor((solving_seconds / 60)),':',
  lpad((solving_seconds % 60),2,'0')) end) AS game_score,(
    CASE
      WHEN (solved = 0)
        THEN (100 - cast(percent_filled as signed))
      ELSE cast(solving_seconds as signed) end) AS score_as_int,
  concat((
    CASE
      WHEN (puzzle_type <> 'daily')
        THEN NULL
      WHEN (star is not null)
        THEN 'Gold!'
      WHEN ((solved = 1) AND (clean_solve = 1))
        THEN 'Solved clean'
      WHEN (solved = 1)
        THEN 'Solved
WITH
  help'
      ELSE concat('Solving... ',
  cast(percent_filled as char charset utf8mb4),'%') end)) AS game_bonuses,
  bot_added_ts,(
    CASE
      WHEN ((solved = 1) AND (clean_solve = 1))
        THEN 1
      WHEN ((solved = 1) AND (clean_solve = 0))
        THEN 0.5
      ELSE 0 end) AS game_completed
FROM
  games.nyt_history
WHERE
  (true AND ((puzzle_type <> 'mini') OR (percent_filled >= 100)))), raw_nyt_legacy as (
SELECT
  game_date,
  dayname(game_date) AS game_detail,'NYT_Legacy' AS source_desc,
  player_id AS user_name,'Mini' AS game_name,
  game_time AS game_score,(
    CASE
      WHEN ((game_time like '%:%') AND regexp_like(game_time,'^[0-9]+:[0-5][0-9]$'))
        THEN ((cast(substring_index(game_time,':',1) as unsigned) * 60) + cast(substring_index(game_time,':',-(1)) as unsigned))
      ELSE NULL end) AS score_as_int,
  NULL AS game_bonuses,
  added_ts,1 AS game_completed
FROM
  matt.mini_history), raw_data as (
SELECT
  raw_games.game_date AS game_date,
  raw_games.game_detail AS game_detail,
  raw_games.source_desc AS source_desc,
  raw_games.user_name AS user_name,
  raw_games.game_name AS game_name,
  raw_games.game_score AS game_score,
  raw_games.score_as_int AS score_as_int,
  raw_games.game_bonuses AS game_bonuses,
  raw_games.added_ts AS added_ts,
  raw_games.game_completed AS game_completed
FROM
  raw_games
UNION ALL
SELECT
  raw_nyt.game_date AS game_date,
  raw_nyt.game_detail AS game_detail,
  raw_nyt.source_desc AS source_desc,
  raw_nyt.user_name AS user_name,
  raw_nyt.game_name AS game_name,
  raw_nyt.game_score AS game_score,
  raw_nyt.score_as_int AS score_as_int,
  raw_nyt.game_bonuses AS game_bonuses,
  raw_nyt.bot_added_ts AS bot_added_ts,
  raw_nyt.game_completed AS game_completed
FROM
  raw_nyt
UNION ALL
SELECT
  raw_nyt_legacy.game_date AS game_date,
  raw_nyt_legacy.game_detail AS game_detail,
  raw_nyt_legacy.source_desc AS source_desc,
  raw_nyt_legacy.user_name AS user_name,
  raw_nyt_legacy.game_name AS game_name,
  raw_nyt_legacy.game_score AS game_score,
  raw_nyt_legacy.score_as_int AS score_as_int,
  raw_nyt_legacy.game_bonuses AS game_bonuses,
  raw_nyt_legacy.added_ts AS added_ts,
  raw_nyt_legacy.game_completed AS game_completed
FROM
  raw_nyt_legacy), added_user as (
SELECT
  x.game_date AS game_date,
  x.game_detail AS game_detail,
  x.source_desc AS source_desc,
  x.user_name AS user_name,
  x.game_name AS game_name,
  x.game_score AS game_score,
  x.score_as_int AS score_as_int,
  x.game_bonuses AS game_bonuses,
  x.added_ts AS added_ts,
  x.game_completed AS game_completed,
  coalesce(y.player_name,
  x.user_name) AS player_name,
  ROW_NUMBER() OVER (PARTITION BY x.game_date,
  x.game_name,
  coalesce(y.player_name,
  x.user_name)
ORDER BY
  x.added_ts desc )  AS row_nbr
FROM
  (raw_data x
LEFT
JOIN
  games.xref_users y on(((x.source_desc = y.sys_name) AND (x.user_name = y.sys_user))))), deduped_and_ranked as (
SELECT
  added_user.game_date AS game_date,
  added_user.game_detail AS game_detail,
  added_user.source_desc AS source_desc,
  added_user.user_name AS user_name,
  added_user.game_name AS game_name,
  added_user.game_score AS game_score,
  added_user.score_as_int AS score_as_int,
  added_user.game_bonuses AS game_bonuses,
  added_user.added_ts AS added_ts,
  added_user.game_completed AS game_completed,
  added_user.player_name AS player_name,
  added_user.row_nbr AS row_nbr,(
    CASE
      WHEN (added_user.game_completed = 0)
        THEN NULL
      WHEN (added_user.game_name in ('timeguessr','boxoffice'))
        THEN rank() OVER (PARTITION BY added_user.game_date,
  added_user.game_name
ORDER BY
  added_user.game_completed desc,
  added_user.score_as_int desc )
      ELSE rank() OVER (PARTITION BY added_user.game_date,
  added_user.game_name
ORDER BY
  added_user.game_completed desc,
  added_user.score_as_int )  end) AS game_rank
FROM
  added_user
WHERE
  (added_user.row_nbr = 1))
SELECT
  deduped_and_ranked.game_date AS game_date,
  deduped_and_ranked.game_name AS game_name,
  deduped_and_ranked.game_rank AS game_rank,
  deduped_and_ranked.player_name AS player_name,
  deduped_and_ranked.game_score AS game_score,
  deduped_and_ranked.score_as_int AS score_as_int,
  deduped_and_ranked.game_completed AS game_completed,(
    CASE
      WHEN (deduped_and_ranked.game_rank > 10)
        THEN 0
      ELSE pow((11 - deduped_and_ranked.game_rank),2) end) AS points,
  deduped_and_ranked.game_detail AS game_detail,
  deduped_and_ranked.game_bonuses AS game_bonuses,
  date_format(deduped_and_ranked.added_ts,'%l:%i%p') AS added_at
FROM
  deduped_and_ranked
ORDER BY
  deduped_and_ranked.game_date,
  deduped_and_ranked.game_name,
  coalesce(deduped_and_ranked.game_rank,9999);
