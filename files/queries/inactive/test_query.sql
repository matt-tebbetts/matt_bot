select 
	game_name,
	game_date,
	max(case when player_name = 'matt' then game_rank end) as matt,
	max(case when player_name = 'whit' then game_rank end) as whit,
	max(case when player_name = 'ryan' then game_rank end) as ryan,
	max(case when player_name = 'mickey' then game_rank end) as mickey,
	max(case when player_name = 'brice' then game_rank end) as brice
from matt.game_view
where game_name = 'octordle'
and game_date >= '2024-12-01'
and guild_id = 'global'
# and player_name in ('whit','matt','ryan')
group by 1,2
order by 1,2
;

select *
from matt.game_history 
order by added_ts  desc
;

update matt.game_history 
set game_date = '2024-10-11'
where added_ts  = '2024-10-15 12:18:47'