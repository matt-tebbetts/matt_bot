-- View: matt.mini_current
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_current AS

SELECT
  game_date,
  player_id,
  game_time,
  added_ts
FROM
  matt.mini_history
WHERE
  (game_date = (
    CASE
      WHEN (((dayofweek(curdate()) in (1,7)) AND (hour(curtime()) >= 18)) OR ((dayofweek(curdate()) not in (1,7)) AND (hour(curtime()) >= 22)))
        THEN (curdate() + interval 1 day)
      ELSE curdate() end));
