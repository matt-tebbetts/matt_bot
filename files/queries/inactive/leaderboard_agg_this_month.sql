WITH monthly_stats AS (
    SELECT 
        player_name,
        COUNT(*) as games_played,
        SUM(points) as total_points,
        AVG(seconds) as avg_seconds,
        MIN(seconds) as best_time,
        COUNT(CASE WHEN game_rank = 1 THEN 1 END) as wins
    FROM games.game_view
    WHERE game_date >= DATE_TRUNC('month', CURRENT_DATE)
        AND game_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
        AND game_name = %s
    GROUP BY player_name
)
SELECT 
    player_name,
    games_played,
    total_points,
    ROUND(avg_seconds) as avg_seconds,
    best_time,
    wins,
    RANK() OVER (ORDER BY total_points DESC, avg_seconds ASC) as rank
FROM monthly_stats
ORDER BY 
    rank ASC,
    total_points DESC,
    avg_seconds ASC
LIMIT 10; 