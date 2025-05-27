-- Create nyt_history table for NYT Crossword data
CREATE TABLE IF NOT EXISTS nyt_history (
    record_id VARCHAR(100) PRIMARY KEY,
    player_name VARCHAR(50) NOT NULL,
    print_date DATE NOT NULL,
    puzzle_type VARCHAR(20) NOT NULL,
    author VARCHAR(100),
    title VARCHAR(200),
    puzzle_id INT,
    solved BOOLEAN,
    solving_seconds INT,
    percent_filled INT,
    eligible BOOLEAN,
    star VARCHAR(20),
    checks_used INT,
    reveals_used INT,
    clean_solve BOOLEAN,
    opened_datetime VARCHAR(30),
    solved_datetime VARCHAR(30),
    min_guess_datetime VARCHAR(30),
    final_commit_datetime VARCHAR(30),
    bot_added_ts DATETIME NOT NULL,
    INDEX idx_player_date (player_name, print_date),
    INDEX idx_puzzle_type (puzzle_type)
);
DESCRIBE nyt_history; 