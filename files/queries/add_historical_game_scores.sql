-- if the old bot is adding scores that the new bot has missed, this will backfill

INSERT INTO games.game_history (
    added_ts,
    user_name,
    game_name,
    game_score,
    game_date,
    game_detail,
    game_bonuses,
    source_desc
)
SELECT 
    old.added_ts,
    old.discord_id AS user_name,
    old.game_name,
    old.game_score,
    old.game_date,
    old.game_dtl AS game_detail,
    null AS game_bonuses,
    'discord' AS source_desc
FROM matt.game_history old
LEFT JOIN games.game_history new
	ON new.user_name = old.discord_id
    AND new.game_name = old.game_name
    AND new.game_date = old.game_date
    AND new.added_ts = old.added_ts
WHERE new.added_ts IS NULL -- not in our new table yet
ORDER BY 1 DESC;