SELECT
    game_rank,
    points,
    player_name,
    game_score,
    game_date,
    game_name,
    game_detail
FROM game_view
WHERE game_date = %s
    AND game_name = %s
ORDER BY 
    points DESC
;