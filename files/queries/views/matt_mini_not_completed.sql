-- View: matt.mini_not_completed
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.mini_not_completed AS

WITH
  users as (
SELECT
  x.player_name AS player_name,
  x.discord_id AS discord_id,
  x.discord_id_nbr AS discord_id_nbr,
  x.nyt_id AS nyt_id,
  x.phone_nbr AS phone_nbr,
  x.phone_carr_cd AS phone_carr_cd,
  x.mini_warning_text AS mini_warning_text,
  x.mini_warning_tag AS mini_warning_tag,
  x.warning_hours AS warning_hours,
  x.id_rank AS id_rank
FROM
  (
SELECT
  player_name,
  discord_id,
  discord_id_nbr,
  nyt_id,
  phone_nbr,
  phone_carr_cd,
  mini_warning_text,
  mini_warning_tag,
  warning_hours,
  ROW_NUMBER() OVER (PARTITION BY player_name
ORDER BY
  (
    CASE
      WHEN (discord_id like '%#%')
        THEN 1
      ELSE 0 end) )  AS id_rank
FROM
  matt.user_details) x
WHERE
  (x.id_rank = 1)), details as (
SELECT
  distinct x.player_name AS player_name,
  x.discord_id AS discord_id,
  x.discord_id_nbr AS discord_id_nbr,
  x.phone_nbr AS phone_nbr,
  x.phone_carr_cd AS phone_carr_cd,
  coalesce(x.mini_warning_text,0) AS wants_text,
  coalesce(x.mini_warning_tag,(
    CASE
      WHEN (z.player_id is not null)
        THEN 1
      ELSE 0 end)) AS wants_tag
FROM
  ((users x
LEFT
JOIN
  (
SELECT
  distinct player_id
FROM
  matt.mini_history
WHERE
  (game_date = curdate())) y on((x.nyt_id = y.player_id)))
LEFT
JOIN
  (
SELECT
  distinct player_id
FROM
  matt.mini_history
WHERE
  (game_date >= (curdate() - interval 7 day))) z on((x.nyt_id = z.player_id)))
WHERE
  ((y.player_id is null) AND (z.player_id is not null))), notification_history as (
SELECT
  user_name AS player_name,
  max(warning_dttm) AS last_msg_sent
FROM
  games.mini_warning_history
WHERE
  (message_status = 'Sent')
GROUP BY
  user_name)
SELECT
  a.player_name AS player_name,
  a.discord_id AS discord_id,
  a.discord_id_nbr AS discord_id_nbr,
  a.wants_text AS wants_text,
  a.wants_tag AS wants_tag,
  b.last_msg_sent AS last_msg_sent,
  timestampdiff(HOUR,
  b.last_msg_sent,
  now()) AS hours_since_last_text
FROM
  (details a
LEFT
JOIN
  notification_history b on((a.player_name = b.player_name)));
