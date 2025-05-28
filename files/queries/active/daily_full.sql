with daily as (
	select 
		print_date,
		row_number() over(
			partition by puzzle_type, print_date 
			order by
				case when star = '1' then 1 else 0 end desc,
				solved desc,
				solving_seconds asc
		) as game_rank,
		player_name,
		CONCAT(FLOOR(solving_seconds / 60), ':', LPAD(MOD(solving_seconds, 60), 2, '0')) AS solve_time,
		percent_filled as pct_done,
		case when star = '1' then 1 else 0 end as gold,
		solved_datetime
	from games.nyt_history
	where puzzle_type = 'daily'
	and print_date = %s
)
select *
from daily
;
