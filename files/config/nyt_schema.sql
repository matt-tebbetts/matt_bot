-- NYT Crossword History Table
-- Stores solving stats for multiple users with UPSERT on record_id
-- APIs: /v3/puzzles.json (overview) + /v6/game/{id}.json (details)

CREATE TABLE IF NOT EXISTS nyt_history (
    record_id VARCHAR(255) PRIMARY KEY,        -- {date}_{type}_{player}
    player_name VARCHAR(100) NOT NULL,
    print_date DATE NOT NULL,
    puzzle_type VARCHAR(20) NOT NULL,          -- daily, mini, bonus
    puzzle_id INTEGER,
    author VARCHAR(200),
    title VARCHAR(500),
    solved BOOLEAN,                            -- completed puzzle
    solving_seconds INTEGER,                   -- calcs.secondsSpentSolving
    percent_filled INTEGER,                    -- 0-100, good for progress check
    eligible BOOLEAN,                          -- calcs.eligible (still eligible for gold star)
    star BOOLEAN,                              -- overview.star (got gold star)
    opened_datetime VARCHAR(50),               -- firsts.opened → Eastern time
    solved_datetime VARCHAR(50),               -- firsts.solved → Eastern time  
    final_commit_datetime VARCHAR(50),         -- timestamp → Eastern time (for smart updates)
    bot_added_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_player_date (player_name, print_date),
    INDEX idx_puzzle_type (puzzle_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Example Queries:
-- Recent stats: SELECT * FROM nyt_history WHERE print_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAYS);
-- Progress check: SELECT player_name, percent_filled FROM nyt_history WHERE solved = 0 AND percent_filled > 0;
-- Recently updated: SELECT * FROM nyt_history WHERE final_commit_datetime >= DATE_SUB(NOW(), INTERVAL 1 HOUR);
-- Leaderboard: SELECT player_name, AVG(solving_seconds), COUNT(*) FROM nyt_history WHERE solved = 1 GROUP BY player_name; 