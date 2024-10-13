alter view games.winners_today as 
with todays_games as (
	select 
		concat(upper(substring(replace(game_name, '_', ' '), 1, 1)), lower(substring(replace(game_name, '_', ' '), 2))) as game,
		game_rank,
		player_name as winner,
		game_score as score
	from matt.game_view
	where guild_id = 'global'
	and game_date = curdate()
),
players_per_game as (
	select 
		game, sum(1) as players
	from todays_games
	group by 1
),
winners as (
	select *
	from todays_games
	where game_rank = 1
)
select a.game, a.winner, a.score, b.players
from winners a
join players_per_game b
	using(game)
where a.game_rank = 1
order by players desc
;