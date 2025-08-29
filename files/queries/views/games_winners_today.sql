-- View: games.winners_today
-- Schema: games
-- Extracted from database

CREATE OR REPLACE VIEW games.winners_today AS

WITH
  todays_games as (
SELECT
  concat(upper(substr(replace(game_name,'_',' '),1,1)),
  lower(substr(replace(game_name,'_',' '),2))) AS game,
  game_rank,
  player_name AS winner,
  game_score AS score
FROM
  matt.game_view
WHERE
  ((guild_id = 'global') AND (game_date = curdate()))), players_per_game as (
SELECT
  todays_games.game AS game,
  sum(1) AS players
FROM
  todays_games
GROUP BY
  todays_games.game), winners as (
SELECT
  todays_games.game AS game,
  todays_games.game_rank AS game_rank,
  todays_games.winner AS winner,
  todays_games.score AS score
FROM
  todays_games
WHERE
  (todays_games.game_rank = 1))
SELECT
  a.game AS game,
  a.winner AS winner,
  a.score AS score,
  b.players AS players
FROM
  (winners a
JOIN
  players_per_game b on((a.game = b.game)))
WHERE
  (a.game_rank = 1)
ORDER BY
  b.players desc;
