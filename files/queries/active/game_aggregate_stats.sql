WITH game_stats AS (
    SELECT 
        player_name as player,
        COUNT(*) as games,
        SUM(points) as points,
        AVG(seconds) as avg_score,
        COUNT(CASE WHEN game_rank = 1 THEN 1 END) as wins,
        COUNT(CASE WHEN game_rank = 2 THEN 1 END) as 2nd,
        COUNT(CASE WHEN game_rank = 3 THEN 1 END) as 3rd,
        COUNT(CASE WHEN game_rank < 6 THEN 1 END) / COUNT(*) as top_5
    FROM games.game_view
    WHERE game_date BETWEEN '2025-05-01' and '2025-05-24'
        AND game_name = 'mini'
    GROUP BY player_name
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY points DESC, avg_score ASC) as `rank`,
    player,
    points,
    ROUND(avg_score) as `avg`,
    wins,
    2nd,
    3rd,
    top_5,
    games
FROM game_stats
ORDER BY  points DESC
;