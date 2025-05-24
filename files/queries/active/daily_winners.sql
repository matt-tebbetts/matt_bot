SELECT
    case    when game_name in ('boxoffice','actorle','moviedle')
            then 'movies'
            when game_name in ('travle','worldle','timeguessr')
            then 'geography'
            when game_name in ('connections','wordle','octordle','crosswordle','octordle_rescue','octordle_sequence')
            then 'language'
            when game_name in ('factle')
            then 'trivia'
            when game_name in ('mini')
            then 'crossword'
            else 'other'
    end as game_type,
    game_name,
    GROUP_CONCAT(player_name ORDER BY player_name SEPARATOR ', ') as winners,
    game_score,
    game_detail
FROM games.game_view
WHERE game_date = %s
    AND game_rank = 1
GROUP BY 
    game_name,
    game_score,
    game_detail
ORDER BY 1,2
;