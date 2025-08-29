-- View: matt.mini_run_checker
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_run_checker AS

SELECT
  x.game_date AS game_date,
  x.wkday_nbr AS wkday_nbr,
  x.wkday_nm AS wkday_nm,
  x.mini_runs AS mini_runs,
  x.last_run AS last_run,
  x.expiry_time AS expiry_time,
  round((timestampdiff(SECOND,
  x.last_run,
  x.expiry_time) / 60.0),1) AS minutes_remaining
FROM
  (
SELECT
  game_date,
  weekday(game_date) AS wkday_nbr,
  left(dayname(game_date),3) AS wkday_nm,
  count(distinct hour(added_ts)) AS mini_runs,
  max(added_ts) AS last_run,(
    CASE
      WHEN (weekday(game_date) in (5,6))
        THEN concat(game_date,' ','18:00:00')
      ELSE concat(game_date,' ','22:00:00') end) AS expiry_time
FROM
  matt.mini_history
WHERE
  (cast(game_date as date) >= '2023-01-25')
GROUP BY
  game_date) x
ORDER BY
  x.game_date desc;
