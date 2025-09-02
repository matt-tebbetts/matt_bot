WITH
game_stats AS (
    SELECT 
        player_name,
        a.game_name,
        d.scoring_type as game_type,
        COUNT(*) as games,
        SUM(points) as points,
        MAX(case when game_completed = 1 then score_as_int end) as max_score,
        MIN(case when game_completed = 1 then score_as_int end) as min_score,
        AVG(case when a.game_name = 'daily' then (score_as_int / 60.0) else score_as_int end) as avg_score,
        COUNT(CASE WHEN game_rank = 1 THEN 1 END) as 1st,
        COUNT(CASE WHEN game_rank = 2 THEN 1 END) as 2nd,
        COUNT(CASE WHEN game_rank = 3 THEN 1 END) as 3rd,
        COUNT(CASE WHEN game_rank = 4 THEN 1 END) as 4th,
        COUNT(CASE WHEN game_rank = 5 THEN 1 END) as 5th
    FROM games.daily_view a
    left join games.game_details d
    		on a.game_name = d.game_name
    WHERE game_date BETWEEN %s and %s
    GROUP BY 1,2,3
),
combined as (
    SELECT 
    		game_name,
        ROW_NUMBER() OVER (partition by game_name ORDER BY points DESC, avg_score ASC) as agg_rank,
        player_name,
        points,
        ROUND(avg_score, 1) as `avg`,
        case when game_type = 'points' then max_score else min_score end as best,
        1st,
        2nd,
        3rd,
        4th,
        5th,
        games
    FROM game_stats
)
select
	game_name,
    player_name as winner,
    `avg`,
    best,
    1st,
    2nd,
    3rd,
    4th,
    5th,
    games,
    points
from combined
where agg_rank = 1
order by games desc