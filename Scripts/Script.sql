#alter view matt.mini_not_completed as
with 
users as (
	select x.* 
	from
		(
		select *, row_number() over(partition by player_name 
					order by case when discord_id like '%#%' then 1 else 0 end) as id_rank
		from matt.user_details	
		) x
	where x.id_rank = 1
),
details as (
	select distinct
		x.player_name,
		x.discord_id,
	    x.discord_id_nbr,
	    x.phone_nbr,
	    x.phone_carr_cd,
	    coalesce(x.mini_warning_text, 0) as wants_text,
	    coalesce(x.mini_warning_tag, case when z.player_id is not null then 1 else 0 end) as wants_tag
	from users x
	left join 
			(
	        select distinct player_id
	        from matt.mini_history
	        where game_date = current_date
	        ) y
		on x.nyt_id = y.player_id
	left join
			(
			select distinct 
				player_id
			from matt.mini_history
			where game_date >= date_sub(current_date, interval 7 day)
			# group by 1
			) z
		on x.nyt_id = z.player_id
	where y.player_id is null # hasn't done today's mini
	and z.player_id is not null # has done it recently (should get notified)
),
notification_history as (
	select 
		user_name as player_name,
		max(warning_dttm) as last_msg_sent
	from games.mini_warning_history
	where message_status = 'Sent'
	group by 1
)
select 
	a.player_name,
	a.discord_id,
	a.discord_id_nbr,
	a.wants_text,
	a.wants_tag,
	b.last_msg_sent,
	TIMESTAMPDIFF(HOUR, b.last_msg_sent, CURRENT_TIMESTAMP) as hours_since_last_text
from details a
left join notification_history b
	on a.player_name = b.player_name
;