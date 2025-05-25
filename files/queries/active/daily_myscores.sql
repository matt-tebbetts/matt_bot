WITH 
recently_played AS (
	SELECT DISTINCT
		player_name,
		member_nm, -- discord name
		game_name
	FROM games.game_view
	WHERE game_date >= date_sub(curdate(), interval 2 week)
	AND member_nm = %s
),
specific_date as (
	SELECT
	    player_name,
		member_nm,
	    game_name,
	    game_score,
	    game_rank,
	    game_detail
	FROM games.game_view
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
	AND a.member_nm = b.member_nm
	AND a.game_name = b.game_name
;