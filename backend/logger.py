import logging
import sys
from config import LOG_LEVEL, LOG_FILE, LOG_FORMAT

def setup_logger(name):
    """Create a logger with both file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
