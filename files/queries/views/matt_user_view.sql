-- View: matt.user_view
-- Schema: matt
-- Extracted from database

CREATE OR REPLACE VIEW matt.user_view AS

WITH
  discord_members as (
SELECT
  x.member_id AS member_id,
  max((
    CASE
      WHEN (x.nm_rank = 1)
        THEN x.member_nm end)) AS member_nm,
  max((
    CASE
      WHEN (x.nm_rank = 2)
        THEN x.member_nm end)) AS alt_member_nm
FROM
  (
SELECT
  i.member_id AS member_id,
  i.member_nm AS member_nm,
  rank() OVER (PARTITION BY i.member_id
ORDER BY
  (
    CASE
      WHEN (i.member_nm like '%#%')
        THEN 1
      ELSE 0 end) )  AS nm_rank
FROM
  (
SELECT
  distinct member_id,
  member_nm
FROM
  matt.user_history) i) x
GROUP BY
  x.member_id), guild_users as (
SELECT
  a.member_id AS member_id,
  a.member_nm AS member_nm,
  a.alt_member_nm AS alt_member_nm,
  b.guild_id AS guild_id,
  b.guild_nm AS guild_nm
FROM
  (discord_members a
JOIN
  (
SELECT
  distinct member_id,
  guild_id,
  guild_nm
FROM
  matt.user_history) b on((a.member_id = b.member_id))))
SELECT
  distinct c.player_name AS player_name,
  c.nyt_id AS nyt_id,
  a.member_id AS member_id,
  a.member_nm AS member_nm,
  a.alt_member_nm AS alt_member_nm,
  coalesce(a.guild_id,'Global') AS guild_id,
  coalesce(a.guild_nm,'Global') AS guild_nm
FROM
  (matt.user_details c
LEFT
JOIN
  guild_users a on(((a.member_nm = c.discord_id) OR (a.alt_member_nm = c.discord_id)))) union
SELECT
  distinct c.player_name AS player_name,
  c.nyt_id AS nyt_id,
  a.member_id AS member_id,
  a.member_nm AS member_nm,
  a.alt_member_nm AS alt_member_nm,'Global' AS guild_id,'Global' AS guild_nm
FROM
  (matt.user_details c
JOIN
  guild_users a on(((a.member_nm = c.discord_id) OR (a.alt_member_nm = c.discord_id))))
ORDER BY
  player_name;
