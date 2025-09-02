WITH game_stats AS (
    SELECT 
        player_name as player,
        COUNT(*) as games,
        SUM(points) as points,
        AVG(seconds) as avg_score,
        COUNT(CASE WHEN game_rank = 1 THEN 1 END) as 1st,
        COUNT(CASE WHEN game_rank = 2 THEN 1 END) as 2nd,
        COUNT(CASE WHEN game_rank = 3 THEN 1 END) as 3rd,
        COUNT(CASE WHEN game_rank = 4 THEN 1 END) as 4th,
        COUNT(CASE WHEN game_rank = 5 THEN 1 END) as 5th,
        COUNT(CASE WHEN game_rank < 11 THEN 1 END) / COUNT(*) as top_10_raw
    FROM games.game_view
    WHERE game_date BETWEEN %s and %s
        AND game_name = %s
    GROUP BY player_name
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY points DESC, avg_score ASC) as `rank`,
    player,
    points,
    ROUND(avg_score) as `avg`,
    1st,
    2nd,
    3rd,
    4th,
    5th,
    CASE 
        WHEN top_10_raw = 1.0 THEN '100%'
        ELSE CONCAT(ROUND(top_10_raw * 100, 1), '%')
    END as top_10,
    games
FROM game_stats
ORDER BY  points DESC
;