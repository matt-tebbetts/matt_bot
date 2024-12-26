 SELECT 
    game_name as game,
    player_name as winner,
    game_score as score
FROM games.game_view
WHERE game_date = CURDATE() 
and game_rank = 1
ORDER BY game_name, game_date desc;