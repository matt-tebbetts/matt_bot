select
	rnk,
	player,
	score,
	detail,
	bonus,
	added_at
from games.daily_view
where game_date = %s
and game_name = %s