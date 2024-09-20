SELECT
	month_rank,
	player_name,
	points,
	wins,
	top5,
	avg_rank,
	games_played as games
FROM games.leaderboard_monthly
WHERE game_name = 'boxoffice'
AND is_curr_month