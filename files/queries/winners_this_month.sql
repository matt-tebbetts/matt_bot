WITH winners AS (
	SELECT 
	    game_name as game,
	    player_name as player,
	    sum(points) as points,
	    count(*) as played
	FROM games.game_view
	WHERE extract(year from game_date) = extract(year from curdate())
	AND extract(month from game_date) = extract(month from curdate())
	AND game_rank = 1
	GROUP BY 1,2
	union all
	SELECT 
	    'z_overall' as game,
	    player_name as player,
	    sum(points) as points,
	    count(*) as played
	FROM games.game_view
	WHERE extract(year from game_date) = extract(year from curdate())
	AND extract(month from game_date) = extract(month from curdate())
	AND game_rank = 1
	GROUP BY 1,2
),
ranks as (
select
	game,
	player,
	points,
	played,
	dense_rank() over(partition by game order by points desc) as rnk
from winners
)
select
	game, player, points, played
from ranks
where rnk = 1
order by 1