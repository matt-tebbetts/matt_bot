WITH 
recently_played_games AS (
    SELECT DISTINCT
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
        game_name
    FROM games.game_view
    WHERE game_date >= date_sub(curdate(), interval 2 week)
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
    a.game_type,
    a.game_name,
    b.winners,
    b.game_score,
    b.game_detail
FROM recently_played_games a
LEFT JOIN specific_date_winners b
    ON a.game_name = b.game_name
ORDER BY a.game_type, a.game_name
;