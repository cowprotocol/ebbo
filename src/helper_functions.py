"""
This file contains some auxiliary functions
"""
from __future__ import annotations
import logging
from typing import Optional


def get_logger(filename: Optional[str] = None) -> logging.Logger:
    """
    get_logger() returns a logger object that can write to a file, terminal or only file if needed.
    """
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if filename:
        file_handler = logging.FileHandler(filename + ".log", mode="w")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
