import logging
import sys
import os
from typing import Literal, Dict, Any
from datetime import datetime

from app.core.config import settings

class ColoredFormatter(logging.Formatter):
    """
    Custom log formatter for colored console output and structured logging.
    Includes request_id and execution_time if available in log record extra.
    """

    # ANSI escape codes for colors
    GRAY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: f"{BLUE}%(levelname)-8s{RESET} {GRAY}%(asctime)s {settings.APP_NAME} (PID:{os.getpid()}) %(message)s{RESET}",
        logging.INFO: f"{BLUE}%(levelname)-8s{RESET} {GRAY}%(asctime)s {settings.APP_NAME} (PID:{os.getpid()}) %(message)s{RESET}",
        logging.WARNING: f"{YELLOW}%(levelname)-8s{RESET} {GRAY}%(asctime)s {settings.APP_NAME} (PID:{os.getpid()}) %(message)s{RESET}",
        logging.ERROR: f"{RED}%(levelname)-8s{RESET} {GRAY}%(asctime)s {settings.APP_NAME} (PID:{os.getpid()}) %(message)s{RESET}",
        logging.CRITICAL: f"{BOLD_RED}%(levelname)-8s{RESET} {GRAY}%(asctime)s {settings.APP_NAME} (PID:{os.getpid()}) %(message)s{RESET}"
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")

        # Add extra context to the message if available
        extra_parts = []
        if hasattr(record, 'request_id') and record.request_id:
            extra_parts.append(f"RequestID:{record.request_id}")
        if hasattr(record, 'route') and record.route:
            extra_parts.append(f"Route:{record.route}")
        if hasattr(record, 'method') and record.method:
            extra_parts.append(f"Method:{record.method}")
        if hasattr(record, 'status_code') and record.status_code:
            extra_parts.append(f"Status:{record.status_code}")
        if hasattr(record, 'duration') and record.duration is not None:
            extra_parts.append(f"Duration:{record.duration:.2f}ms")

        if extra_parts:
            # Prepend extra parts to the original message
            record.msg = f"{' '.join(extra_parts)} {record.msg}"

        return formatter.format(record)

def configure_logging() -> None:
    """
    Configures the application's logging system.
    Sets up a console handler with a custom colored formatter.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL) # Set global log level from settings

    # Clear existing handlers to prevent duplicate logs in case of re-configuration
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_handler.setFormatter(ColoredFormatter())

    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)

    # Optionally, mute noisy loggers from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(f"Logging initialized with level: {settings.LOG_LEVEL}")


# Expose a logger for application-wide use, pre-configured if called after configure_logging()
# It's good practice to get a named logger for modules rather than using the root_logger directly.
# However, for simple use or where a global logger is desired, root_logger can be used or
# an application-wide logger can be exposed after initial setup.
app_logger = logging.getLogger(settings.APP_NAME)
