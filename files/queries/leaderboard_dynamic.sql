
-- this month's leaderboard
with daily_games as (
select
    CONCAT(YEAR(game_date), LPAD(MONTH(game_date), 2, '0')) as game_month,
   	game_name,
   	game_date,
    game_rank,
    player_name,
  	game_score,
    points
from
    matt.game_view
where guild_id = 'global'
and YEAR(game_date) = YEAR(CURDATE())
and MONTH(game_date) = MONTH(CURDATE())
and game_name = 'octordle'
order by
    game_name,
    coalesce(game_rank, 999)
)
select *
from daily_games