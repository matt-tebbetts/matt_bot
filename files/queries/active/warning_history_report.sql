-- Query to view mini warning history and statistics
SELECT 
    warning_date,
    player_name,
    discord_id_nbr,
    warning_sent,
    success,
    error_message,
    warning_type,
    warning_timestamp
FROM games.mini_warning_history
WHERE warning_date >= CURDATE() - INTERVAL 7 DAYS
ORDER BY warning_date DESC, warning_timestamp DESC;

-- Summary statistics for warnings
-- SELECT 
--     warning_date,
--     COUNT(*) as total_attempts,
--     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_warnings,
--     SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_warnings,
--     ROUND(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) as success_rate_percent
-- FROM games.mini_warning_history
-- WHERE warning_date >= CURDATE() - INTERVAL 30 DAYS
-- GROUP BY warning_date
-- ORDER BY warning_date DESC; 