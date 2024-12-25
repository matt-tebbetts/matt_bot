SELECT
    game_rank as rnk,
    player,
    score
FROM matt.leaderboard_today
WHERE game_name = %s
