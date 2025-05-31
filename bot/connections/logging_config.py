import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from bot.functions.admin import direct_path_finder

class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for console and detailed info for file logs."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, use_colors=False, include_extra_info=False):
        self.use_colors = use_colors
        self.include_extra_info = include_extra_info
        
        if include_extra_info:
            # Detailed format for file logs
            fmt = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s'
        else:
            # Simpler format for console
            fmt = '%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s'
            
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    def format(self, record):
        # Add task/asyncio context if available
        if hasattr(record, 'task_name'):
            record.message = f"[{record.task_name}] {record.getMessage()}"
        elif hasattr(record, 'event_loop'):
            record.message = f"[LOOP] {record.getMessage()}"
        else:
            record.message = record.getMessage()
            
        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
            
        return super().format(record)

def setup_logging(debug_mode=False):
    """Set up comprehensive logging for the bot."""
    
    # Create logs directory
    logs_dir = Path(direct_path_finder('files', 'logs'))
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # === CONSOLE HANDLER ===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = CustomFormatter(use_colors=True, include_extra_info=False)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # === MAIN LOG FILE HANDLER ===
    main_log_file = logs_dir / 'bot_main.log'
    main_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setLevel(logging.DEBUG)
    main_formatter = CustomFormatter(use_colors=False, include_extra_info=True)
    main_handler.setFormatter(main_formatter)
    root_logger.addHandler(main_handler)
    
    # === TASKS LOG FILE HANDLER ===
    tasks_log_file = logs_dir / 'bot_tasks.log'
    tasks_handler = logging.handlers.RotatingFileHandler(
        tasks_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    tasks_handler.setLevel(logging.DEBUG)
    tasks_formatter = CustomFormatter(use_colors=False, include_extra_info=True)
    tasks_handler.setFormatter(tasks_formatter)
    
    # Add filter to only log task-related messages
    class TasksFilter:
        def filter(self, record):
            return (
                'task' in record.name.lower() or 
                'tasks' in record.name.lower() or
                hasattr(record, 'task_name') or
                'mini_leader' in str(record.getMessage()).lower() or
                'background' in str(record.getMessage()).lower()
            )
    
    tasks_handler.addFilter(TasksFilter())
    root_logger.addHandler(tasks_handler)
    
    # === ERROR LOG FILE HANDLER ===
    error_log_file = logs_dir / 'bot_errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = CustomFormatter(use_colors=False, include_extra_info=True)
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # === DISCORD LIBRARY LOGS ===
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)  # Only warnings and errors from discord.py
    
    # === ASYNCIO LOGS ===
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.setLevel(logging.DEBUG if debug_mode else logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger('bot.startup')
    logger.info("="*60)
    logger.info("Bot logging system initialized")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Main log: {main_log_file}")
    logger.info(f"Tasks log: {tasks_log_file}")
    logger.info(f"Error log: {error_log_file}")
    logger.info("="*60)
    
    return root_logger

def get_task_logger(task_name):
    """Get a logger for a specific task with task name context."""
    logger = logging.getLogger(f'bot.tasks.{task_name}')
    
    # Create a custom LoggerAdapter that adds task context
    class TaskLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f'[{self.extra["task_name"]}] {msg}', kwargs
    
    return TaskLoggerAdapter(logger, {'task_name': task_name})

def get_logger(name):
    """Get a logger for a specific module/component."""
    return logging.getLogger(f'bot.{name}')

def log_asyncio_context():
    """Log current asyncio context for debugging."""
    import asyncio
    logger = logging.getLogger('bot.asyncio')
    
    try:
        loop = asyncio.get_running_loop()
        task = asyncio.current_task()
        
        logger.debug(f"Current event loop: {loop}")
        logger.debug(f"Current task: {task}")
        logger.debug(f"Loop is running: {loop.is_running()}")
        logger.debug(f"Loop is closed: {loop.is_closed()}")
        
        if task:
            logger.debug(f"Task name: {task.get_name()}")
            logger.debug(f"Task done: {task.done()}")
            logger.debug(f"Task cancelled: {task.cancelled()}")
            
    except RuntimeError as e:
        logger.debug(f"No running event loop: {e}")
    except Exception as e:
        logger.error(f"Error getting asyncio context: {e}")

def log_exception(logger, exc, context=""):
    """Log an exception with full traceback and context."""
    import traceback
    
    logger.error(f"Exception occurred{' in ' + context if context else ''}: {exc}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception args: {exc.args}")
    logger.debug(f"Full traceback:\n{traceback.format_exc()}")
    
    # Log asyncio context if it's an asyncio-related error
    if 'asyncio' in str(exc).lower() or 'event loop' in str(exc).lower():
        log_asyncio_context() 