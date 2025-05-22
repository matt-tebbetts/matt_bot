with all_games as (
    select distinct game_name
    from games.game_history
    where game_date > date_sub(current_date, interval 1 week)
    union all 
    select 'mini' as game_name
),
selected_games as (
    SELECT 
        game_name,
        game_score,
        game_rank
    FROM games.game_view
    WHERE game_date = curdate()
    AND member_nm = %s
)
SELECT 
    a.game_name,
    coalesce(b.game_score, '-') as game_score,
    coalesce(b.game_rank, '-') as game_rank
FROM all_games a
LEFT JOIN selected_games b
    ON a.game_name = b.game_name
ORDER BY game_name;