with overall as (
	SELECT 
	    'z_overall' as game,
	    player_name as winner,
	    sum(points) as score
	FROM games.game_view
	WHERE game_date = CURDATE() 
	GROUP BY 1,2
),
overall_rank as (
	SELECT *, DENSE_RANK() over(order by score desc) as rnk
	FROM overall
)
SELECT 
    game_name as game,
    player_name as winner,
    game_score as score
FROM games.game_view
WHERE game_date = CURDATE() 
and game_rank = 1
union ALL 
select 
	game,
	winner,
	score 
from overall_rank
where rnk = 1
order by 1
;