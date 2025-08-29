-- View: matt.no_mini_yet
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.no_mini_yet AS

SELECT
  distinct guild_id,
  member_id,
  member_nm,
  player_name,
  phone_nbr,(
    CASE
      WHEN (y.player_name is not null)
        THEN 1
      ELSE 0 end) AS mini_completed
FROM
  (matt.user_view x
LEFT
JOIN
  (
SELECT
  guild_id,
  player_name
FROM
  matt.mini_view
WHERE
  (game_date = curdate())) y on(((guild_id = y.guild_id) AND (player_name = y.player_name))))
WHERE
  ((mini_warning_text = 1) AND (y.player_name is null));
