alter view games.my_scores as
with
recent_games as (
	select distinct game_name
	from game_history
	where game_date > date_sub(current_date, interval 1 week)
	union all 
	select 'mini' as game_name
),
recent_players as (
	select distinct discord_id
	from game_history
	where game_date > date_sub(current_date, interval 1 week)
),
matrix as (
	select *
	from recent_games
	cross join recent_players
),
player_scores as (
    SELECT 
    	member_nm,
        game_name,
        game_score,
        game_rank
    FROM game_view
    where guild_nm = 'global'
    and game_date = curdate()
)
SELECT 
	a.discord_id as discord_nm,
    a.game_name as game,
    coalesce(b.game_score, '-') as score,
    coalesce(b.game_rank, '-') as rnk
FROM matrix a
LEFT JOIN player_scores b
    ON a.game_name = b.game_name
    and a.discord_id = b.member_nm
order by game
;