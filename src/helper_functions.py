"""
This file contains some auxiliary functions.
"""

from __future__ import annotations
import sys
import logging
from typing import Optional


class LogFilter(logging.Filter):
    """
    Filter logs above given level
    """
    def __init__(self, max_log_level: int):
        super().__init__()
        self.max_log_level = max_log_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_log_level


class Logger:
    """
    Logging wrapper class to send info and below to stdout and above to stderr.
    """
    def __init__(
        self,
        name: str = __name__,
        level: int = logging.INFO,
        filename: Optional[str] = None,
    ):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.handlers = []
        self.formatter = logging.Formatter("%(levelname)s - %(message)s")

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.addFilter(LogFilter(logging.INFO))
        stdout_handler.setFormatter(self.formatter)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.setFormatter(self.formatter)

        self._logger.addHandler(stdout_handler)
        self._logger.addHandler(stderr_handler)

        if filename:
            file_handler = logging.FileHandler(f"{filename}.log", mode="w")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(self.formatter)
            self._logger.addHandler(file_handler)

    def debug(self, msg, *args, **kwargs):
        """
        Debug logs
        """
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Info logs
        """
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Warning logs
        """
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """
        Error logs
        """
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Critical logs
        """
        self._logger.critical(msg, *args, **kwargs)
