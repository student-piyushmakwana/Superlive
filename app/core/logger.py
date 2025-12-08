import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Configures the root logger with:
    1. Console handler with colored logs (if available)
    2. File handler with rotation (superlive.log)
    3. Proper formatting including timestamps and levels
    """
    # Create logs directory if it doesn't exist (optional, or just save to root)
    # paths relative to run.py usually
    log_file = "superlive.log"
    
    # Define format
    # Example: 2023-10-27 10:00:00 [INFO] [Worker 1] Message
    log_fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_fmt = '%Y-%m-%d %H:%M:%S'
    
    # Configure Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # 1. File Handler (Rotating)
    # Rotate at 5MB, keep 5 updates
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_fmt, date_fmt))
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    # 2. Console Handler (Colored)
    try:
        import coloredlogs
        # coloredlogs installs its own handler, so we don't add a StreamHandler manually if using this
        coloredlogs.install(
            level='INFO', 
            logger=root_logger, 
            fmt=log_fmt, 
            datefmt=date_fmt,
            level_styles={
                'info': {'color': 'white'}, 
                'warning': {'color': 'yellow'}, 
                'error': {'color': 'red'}, 
                'critical': {'color': 'red', 'bold': True}
            }
        )
    except ImportError:
        # Fallback to standard stream handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_fmt, date_fmt))
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        
    # Silence httpx info logs a bit as they can be noisy per request
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("✅ Logging system initialized (File: superlive.log + Console)")

