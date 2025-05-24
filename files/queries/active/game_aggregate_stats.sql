WITH game_stats AS (
    SELECT 
        player_name as player,
        COUNT(*) as games,
        SUM(points) as points,
        AVG(seconds) as avg_score,
        COUNT(CASE WHEN game_rank = 1 THEN 1 END) as wins,
        COUNT(CASE WHEN game_rank < 6 THEN 1 END) as top_5
    FROM games.game_view
    WHERE game_date BETWEEN %s AND %s
        AND game_name = %s
    GROUP BY player_name
)
SELECT 
    player,
    games,
    points,
    ROUND(avg_score) as avg_score,
    wins,
    ROW_NUMBER() OVER (ORDER BY points DESC, avg_score ASC) as game_rank
FROM game_stats
ORDER BY  points DESC
;