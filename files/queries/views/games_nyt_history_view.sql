-- View: games.nyt_history_view
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.nyt_history_view AS

SELECT
  record_id,
  player_name,
  print_date,
  puzzle_type,
  author,
  title,
  puzzle_id,
  solved,
  solving_seconds,
  percent_filled,
  eligible,
  star,
  checks_used,
  reveals_used,
  clean_solve,
  opened_datetime,
  solved_datetime,
  min_guess_datetime,
  final_commit_datetime,
  bot_added_ts,
  ROW_NUMBER() OVER (PARTITION BY puzzle_type,
  player_name,
  dayofweek(print_date)
ORDER BY
  print_date )  AS player_game_nbr
FROM
  games.nyt_history;
