SELECT 
    game_name,
    player_name,
    game_score,
    game_date,
    game_detail,
    game_rank,
    seconds
FROM games.game_view
WHERE game_date = CURRENT_DATE
    AND game_name = %s
ORDER BY 
    game_rank ASC,
    game_score ASC
LIMIT 10;