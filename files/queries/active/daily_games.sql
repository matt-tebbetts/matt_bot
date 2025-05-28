SELECT
    game_rank,
    player_name,
    game_score,
    points,
    case    when game_name in ('daily','mini')
            then 
                case    when player_name in ('Matt','Brice','Whit','Zach')
                        then 'Automatic'
                        else 'Manual'
                end
            else game_detail
    end as game_detail
FROM games.game_view
WHERE game_date = %s
    AND game_name = %s
ORDER BY 
    points DESC
;