alter view games.game_view as
with
latest_records as (
	select	
		*,
		ROW_NUMBER() OVER(PARTITION BY game_name, game_date, user_name ORDER BY added_ts desc) AS added_rank
	from games.game_history
),
all_games as (
SELECT 
	x.game_date,
	x.game_name,
	x.game_score,
	x.added_ts,
	x.user_name,
	x.game_detail,
	g.scoring_type,
	
	# get the score into an integer so that we can sort and rank correctly
	case    when g.scoring_type = 'timed'
	        then cast(substring_index(x.game_score, ':', 1) * 60 + substring_index(x.game_score, ':', -1) as signed) # seconds
	        when g.scoring_type = 'guesses'
	        then 
	            case    when left(x.game_score, 1) in ('X', '?')
	                    then 0
	                    when SUBSTRING_INDEX(x.game_score, '/', 1) REGEXP '^-?[0-9]+$'
	                    then cast(SUBSTRING_INDEX(x.game_score, '/', 1) as signed)
	                    when LEFT(x.game_score, 1) = "+" -- in travle, it'll be "+0" or "+4"
	                    then cast(replace(x.game_score, '+', '') as signed)
	                    else NULL
	            end
	        when g.scoring_type = 'points'
	        then 
	            case    when x.game_score REGEXP '^-?[0-9]+$'
	                    then cast(x.game_score as signed)
	                    else NULL
	            end
	end as score_as_int,
	
	# determine if they even "won" the game itself (regardless of comparison to others)
	case 	when left(x.game_score, 1) in ('X','?') or (x.game_name = 'boxoffice' and game_score = '0')
			then 0
			else 1
	end as game_completed
	
FROM latest_records x
join games.game_details g
	on x.game_name = g.game_name
where x.added_rank = 1
),
games_by_guild as (
SELECT
	x.*,
	case 	when game_completed = 0
			then null
            else 
				case    
						#when score_as_int = 0
						#then null
						
						# games that go by lowest score
				        when scoring_type in ('timed','guesses')
						then dense_rank() over(partition by guild_nm, game_date, game_name order by game_completed desc, score_as_int asc)
				        
				        # games that go by highest score
				        when scoring_type = 'points'
						then dense_rank() over(partition by guild_nm, game_date, game_name order by score_as_int desc)
				
				end
	end as game_rank,
	y.player_name,
	y.member_nm
FROM all_games x
join matt.user_view y
	on (lower(x.user_name) = lower(y.member_nm) or lower(x.user_name) = lower(y.alt_member_nm))
WHERE y.guild_nm = 'global'
),
combined as (
select 
    game_name,
    game_date,
    player_name,
    member_nm,
    game_score,
    game_rank,
    game_completed,
    cast(
    case    	when game_completed = 0 -- win/loss
				then 0
				else power(11 - game_rank, 2) # all games for now use the same points based on rank
    end as signed) as points,
    case when score_as_int = 0 then null else score_as_int end as seconds,
    added_ts,
    game_detail
from games_by_guild
union all
select
	'mini' as game_name,
	game_date,
	player_name,
	member_nm,
	game_time as game_score,
	game_rank,
    1 as game_completed,
	cast(points as signed) as points,
	seconds,
	added_ts,
	null as game_detail
from matt.mini_view
where guild_id = 'global'
)
select *, row_number() over(partition by player_name, game_name order by game_date) as player_game_nbr
from combined

