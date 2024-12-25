CREATE VIEW games.leaderboard_curr_month AS 
SELECT
	game_name,
	month_rank,
	player_name,
	points,
	wins,
	top5,
	avg_rank,
	games_played as games
FROM games.leaderboard_monthly
WHERE is_curr_month
;

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
WHERE game_name = 'boxoffice'