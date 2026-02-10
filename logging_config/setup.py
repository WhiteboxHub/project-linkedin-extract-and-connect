# logging_config/setup.py
"""
Logging setup and configuration.
"""

import logging
import sys
import os
from typing import Optional
from pathlib import Path

from .formatters import StructuredFormatter, ColoredConsoleFormatter, CompactFormatter
from .enrichment import ContextEnrichmentFilter


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    console_format: str = "colored",  # colored, compact, or standard
    file_format: str = "json",  # json or standard
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
) -> logging.Logger:
    """
    Setup standardized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        console_format: Console formatter type
        file_format: File formatter type
        enable_file_logging: Whether to log to files
        enable_console_logging: Whether to log to console
        
    Returns:
        Configured root logger
    """
    # Create log directory
    if enable_file_logging:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add enrichment filter to root logger
    enrichment_filter = ContextEnrichmentFilter()
    root_logger.addFilter(enrichment_filter)
    
    # ========== CONSOLE HANDLER ==========
    if enable_console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Select console formatter
        if console_format == "colored":
            console_formatter = ColoredConsoleFormatter(use_colors=True, show_context=True)
        elif console_format == "compact":
            console_formatter = CompactFormatter()
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # ========== FILE HANDLERS ==========
    if enable_file_logging:
        # Main log file (all levels)
        main_log_path = os.path.join(log_dir, 'bot.log')
        main_handler = logging.FileHandler(main_log_path, encoding='utf-8')
        main_handler.setLevel(logging.DEBUG)
        
        # Error log file (errors only)
        error_log_path = os.path.join(log_dir, 'errors.log')
        error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        
        # Select file formatter
        if file_format == "json":
            file_formatter = StructuredFormatter()
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        main_handler.setFormatter(file_formatter)
        error_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(main_handler)
        root_logger.addHandler(error_handler)
    
    # Log setup complete
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, console={console_format}, file={file_format}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def configure_from_env():
    """
    Configure logging from environment variables.
    
    Environment variables:
        LOG_LEVEL: Logging level (default: INFO)
        LOG_DIR: Log directory (default: logs)
        CONSOLE_FORMAT: Console format (default: colored)
        FILE_FORMAT: File format (default: json)
        ENABLE_FILE_LOGGING: Enable file logging (default: true)
        ENABLE_CONSOLE_LOGGING: Enable console logging (default: true)
    """
    from config.secrets import get_config
    
    config = get_config()
    
    log_level = os.getenv('LOG_LEVEL', config.get('LOG_LEVEL', 'INFO'))
    log_dir = os.getenv('LOG_DIR', 'logs')
    console_format = os.getenv('CONSOLE_FORMAT', 'colored')
    file_format = os.getenv('FILE_FORMAT', 'json')
    enable_file = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'
    enable_console = os.getenv('ENABLE_CONSOLE_LOGGING', 'true').lower() == 'true'
    
    return setup_logging(
        log_level=log_level,
        log_dir=log_dir,
        console_format=console_format,
        file_format=file_format,
        enable_file_logging=enable_file,
        enable_console_logging=enable_console,
    )
