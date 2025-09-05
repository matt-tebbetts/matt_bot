WITH 
recently_played AS (
	SELECT DISTINCT
		player_name, -- discord name
		game_name
	FROM games.daily_view
	WHERE game_date >= date_sub(curdate(), interval 2 week)
	AND player_name = %s
),
specific_date as (
	SELECT
	    player_name,
	    game_name,
	    game_score,
	    game_rank,
	    game_detail
	FROM games.daily_view
	WHERE game_date = %s
)
SELECT
	a.player_name,
	a.game_name,
	b.game_score,
	b.game_rank,
	b.game_detail
FROM recently_played a
LEFT JOIN specific_date b
	ON a.player_name = b.player_name
	AND a.game_name = b.game_name
;