-- Create table for storing Actorle movie details
CREATE TABLE IF NOT EXISTS actorle_detail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_date DATE NOT NULL,
    year INT NOT NULL,
    title TEXT,
    genres TEXT,
    rating DECIMAL(3,1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Add index for efficient queries
    INDEX idx_game_date (game_date),
    INDEX idx_year (year),
    INDEX idx_rating (rating)
);

-- Optional: Create a unique constraint to prevent duplicate entries for the same game_date and movie
-- ALTER TABLE actorle_detail ADD UNIQUE KEY unique_game_movie (game_date, year, title(100)); 