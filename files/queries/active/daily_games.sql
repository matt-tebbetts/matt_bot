SELECT
    game_rank as rnk,
    player_name as player,
    game_score as score,
    points,
    game_detail
FROM games.game_view
WHERE game_date = %s
    AND game_name = %s
ORDER BY 
    points DESC
;