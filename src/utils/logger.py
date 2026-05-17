# src/utils/logger.py

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime

from utils.paths import LOG_FILE as _DEFAULT_LOG, LOG_DIR as _DEFAULT_DIR

def setup_logging(log_file: str = _DEFAULT_LOG, level=logging.INFO):
    """Setup logging to file and console"""
    
    # Create logs directory
    log_dir = Path(_DEFAULT_DIR)
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / log_file
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # File handler (rotates when size > 2MB) — always UTF-8
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=2*1024*1024,  # 2MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler — force UTF-8 so emojis / non-Latin song titles
    # don't crash on Windows terminals that default to cp1252.
    try:
        utf8_stream = open(
            sys.stdout.fileno(),
            mode="w",
            encoding="utf-8",
            errors="replace",   # replace unencodable chars with '?' instead of crashing
            buffering=1,
            closefd=False,
        )
        console_handler = logging.StreamHandler(utf8_stream)
    except Exception:
        # Fallback: plain StreamHandler (might still crash on bad chars, but
        # at least the app won't fail to start)
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging initialized")
    return logger