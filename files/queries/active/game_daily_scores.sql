SELECT
    game_rank,
    player_name,
    game_score,
    points,
    game_detail
FROM games.game_view
WHERE game_date = %s
    AND game_name = %s
ORDER BY 
    points DESC
;