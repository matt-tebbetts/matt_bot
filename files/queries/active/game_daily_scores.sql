SELECT
    game_rank,
    player_name,
    game_score,
    points
FROM game_view
WHERE game_date = %s
    AND game_name = %s
ORDER BY 
    points DESC
;