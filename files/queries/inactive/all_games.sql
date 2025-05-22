select 
	player_name,
	max(case when game_name = 'mini' then game_score end) as mini,
	max(case when game_name = 'connections' then game_score end) as connections,
	max(case when game_name = 'wordle' then game_score end) as wordle,
	max(case when game_name = 'octordle' then game_score end) as octordle,
	max(case when game_name = 'crosswordle' then game_score end) as crosswordle,
	max(case when game_name = 'boxoffice' then game_score end) as boxoffice,
	max(case when game_name = 'actorle' then game_score end) as actorle,
	max(case when game_name = 'timeguessr' then game_score end) as timeguessr,
	max(case when game_name = 'moviedle' then game_score end) as moviedle,
	max(case when game_name = 'worldle' then game_score end) as worldle,
	max(case when game_name = 'travle' then game_score end) as travle
from matt.game_view
where guild_id = 'global'
and game_date = curdate()
group by 1
order by 1;

select
	game_name,
	count(distinct player_Name) as unique_players
from matt.game_view
where game_date >= '2025-01-01'
group by 1 order by 2 desc;


select
	player_name,
	count(distinct game_name) as games,
	sum(1) as entries
from matt.game_view
where game_date >= '2025-01-01'
and guild_id = 'global'
group by 1 order by 2 desc;



SELECT  
	game_name,
	max(case when player_name = 'Whit' then game_score end) as Whit,
	max(case when player_name = 'Ryan' then game_score end) as Ryan,
	max(case when player_name = 'Matt' then game_score end) as Matt,
	max(case when player_name = 'Sally' then game_score end) as Sally,
	max(case when player_name = 'Brice' then game_score end) as Brice,
	max(case when player_name = 'Andy' then game_score end) as Andy,
	max(case when player_name = 'Jess' then game_score end) as Jess,
	max(case when player_name = 'Steve' then game_score end) as Steve,
	max(case when player_name = 'Jesse' then game_score end) as Jesse,
	max(case when player_name = 'Mickey' then game_score end) as Mickey,
	max(case when player_name = 'Ben' then game_score end) as Ben,
	max(case when player_name = 'Caroline' then game_score end) as Caroline,
	max(case when player_name = 'Jonathan' then game_score end) as Jonathan,
	max(case when player_name = 'Zach' then game_score end) as Zach,
	max(case when player_name = 'Andrew' then game_score end) as Andrew,
	max(case when player_name = 'Mary Beth' then game_score end) as "Mary Beth",
	max(case when player_name = 'Jim' then game_score end) as Jim,
	max(case when player_name = 'Evan' then game_score end) as Evan,
	max(case when player_name = 'Bob' then game_score end) as Bob
from matt.game_view
where guild_id = 'global'
and game_date = curdate()
group by 1
order by 1;
