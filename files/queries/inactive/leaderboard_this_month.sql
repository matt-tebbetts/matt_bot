SELECT
	month_rank as rnk,
	player_name as player,
	points,
	wins,
	top5,
	avg_rank as avg_rnk,
	games
FROM games.leaderboard_curr_month
where game_name = %s

SELECT 
    game_name,
    player_name,
    game_score,
    game_date,
    game_detail,
    game_rank,
    seconds
FROM games.game_view
WHERE game_date >= DATE_TRUNC('month', CURRENT_DATE)
    AND game_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
    AND game_name = %s
ORDER BY 
    game_rank ASC,
    game_score ASC
LIMIT 10;