-- alter view matt.leaderboards as

-- today's leaderboards:
select
   	game_name,
    game_rank,
    player_name,
  	game_score,
    points
from
    matt.game_view
where guild_id = 'global'
and game_date = curdate()
order by
    game_name,
    coalesce(game_rank, 999);
