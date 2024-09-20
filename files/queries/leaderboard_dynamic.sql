alter view games.leaderboard_monthly as
with
daily_games as (
    select
        game_name,
        game_date,
        game_rank,
        player_name,
        game_score,
        points,
        CONCAT(YEAR(game_date), LPAD(MONTH(game_date), 2, '0')) as game_month,
        CONCAT(YEAR(game_date), '-', UPPER(DATE_FORMAT(game_date, '%b'))) as game_month_name,
        CASE 	WHEN YEAR(game_date) = YEAR(CURDATE()) 
        			 AND MONTH(game_date) = MONTH(CURDATE()) 
        			THEN TRUE 
        			ELSE FALSE
		END as is_curr_month,
        CASE 	WHEN (YEAR(game_date) = YEAR(CURDATE() - INTERVAL 1 MONTH) 
        			 AND MONTH(game_date) = MONTH(CURDATE() - INTERVAL 1 MONTH))
        			THEN TRUE 
        			ELSE FALSE 
	 	END as is_prev_month
    from matt.game_view
    where guild_id = 'global'
    -- and game_name in ('octordle', 'mini')
),
monthly_leaderboard as (
	select
	    is_curr_month,
	    is_prev_month,
	    game_month,
	    game_name,
	    player_name,
	    sum(points) as points,
	    round(avg(game_rank), 1) as avg_rank, # 10th place if they ranked NULL
	    sum(case when game_rank = 1 then 1 else 0 end) as wins,
	    round(sum(case when game_rank <= 5 then 1 else 0 end) / sum(1.00), 3) as top5,
	    count(*) as games_played
	from daily_games
	group by 1,2,3,4,5
),
final_leaderboard as (
    select *, dense_rank() over (partition by game_name, game_month order by points desc) as month_rank
    from monthly_leaderboard
)
SELECT *
	-- game_month,
	-- game_name,
	-- player_name,
	-- total_points
from final_leaderboard
-- where game_name = 'octordle' and is_curr_month