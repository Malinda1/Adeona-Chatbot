# Logger utility

import logging
import sys
from datetime import datetime
import os
from typing import Optional

class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class AdeonaLogger:
    """Centralized logging system for Adeona Chatbot"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AdeonaLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger configuration"""
        self._logger = logging.getLogger("AdeonaBot")
        self._logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        
        # File handler
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        file_handler = logging.FileHandler(
            f"logs/adeona_bot_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
        )
        file_handler.setFormatter(file_formatter)
        
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)
    
    def get_logger(self):
        return self._logger

# Global logger instance
logger_instance = AdeonaLogger()
logger = logger_instance.get_logger()

def log_function_call(func_name: str, params: Optional[dict] = None):
    """Log function calls with parameters"""
    param_str = f" with params: {params}" if params else ""
    logger.info(f"Calling function: {func_name}{param_str}")

def log_error(error: Exception, context: str = ""):
    """Log errors with context"""
    context_str = f" in {context}" if context else ""
    logger.error(f"Error{context_str}: {str(error)}", exc_info=True)

def log_success(message: str):
    """Log success messages"""
    logger.info(f"SUCCESS: {message}")

def log_warning(message: str):
    """Log warning messages"""
    logger.warning(f"WARNING: {message}")

def log_debug(message: str):
    """Log debug messages"""
    logger.debug(f"DEBUG: {message}")