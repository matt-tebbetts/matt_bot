
 select *
 from games.game_history 
 order by 2 desc;
 

 select *
 from matt.game_history 
 order by added_ts desc;
 
create view games.game_view as (
with latest as (
	select *, row_number() over(partition by user_name, game_name, game_date order by id desc) as row_nbr
	from games.game_history
)
select * from latest where row_nbr = 1
);

select * from games.game_view where game_date = '2024-09-09' order by 2 desc