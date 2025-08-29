select
	game_rank as rnk,
	player_name as player,
	game_score as score,
	game_detail as detail,
	-- game_bonuses as bonus,
	added_at
from games.daily_view
where game_date = %s
and game_name = %s