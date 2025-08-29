-- View: matt.travle
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.travle AS

SELECT
  distinct x.game_name AS game_name,
  x.game_date AS game_date,
  y.player_name AS player_name,
  x.game_score AS game_score,
  x.game_completed AS game_completed,
  x.guesses AS guesses,
  x.max_guesses AS max_guesses,(x.max_guesses - x.guesses) AS addtl_guesses_required
FROM
  ((
SELECT
  distinct game_date,
  game_name,
  discord_id,
  game_score,(
    CASE
      WHEN (left(game_score,1) = '?')
        THEN 0
      ELSE 1 end) AS game_completed,(
    CASE
      WHEN (left(game_score,1) = '?')
        THEN 0
      ELSE cast(substring_index(game_score,'/',1) as signed) end) AS guesses,(
    CASE
      WHEN (left(game_score,1) = '?')
        THEN 0
      ELSE cast(substring_index(game_score,'/',-(1)) as signed) end) AS max_guesses
FROM
  matt.game_history
WHERE
  (game_name = 'travle')) x
JOIN
  matt.user_details y on((x.discord_id = y.discord_id)));
