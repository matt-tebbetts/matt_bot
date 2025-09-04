WITH 
recently_played_games AS (
    SELECT DISTINCT
        game_name
    FROM games.game_view
    WHERE game_date >= date_sub(curdate(), interval 1 week)
),
specific_date_winners AS (
    SELECT
        game_name,
        game_score,
        GROUP_CONCAT(player_name ORDER BY player_name SEPARATOR ', ') as winners,
        game_detail
    FROM games.game_view
    WHERE game_date = %s
        AND game_rank = 1
    GROUP BY 
        game_name,
        game_score,
        game_detail
)
SELECT
    a.game_name,
    b.winners,
    b.game_score,
    b.game_detail
FROM recently_played_games a
LEFT JOIN specific_date_winners b
    ON a.game_name = b.game_name
ORDER BY a.game_name
;