SELECT
	game_name as game,
	month_rank as rnk,
	player_name as player,
	points,
	wins,
	top5,
	avg_rank as avg_rnk,
	games
FROM games.leaderboard_curr_month