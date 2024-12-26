SELECT
    rnk,
    player,
    score
FROM games.leaderboard_today
WHERE game = %s