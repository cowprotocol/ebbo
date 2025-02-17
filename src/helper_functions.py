"""
This file contains some auxiliary functions.
"""

from __future__ import annotations
import os
import logging
from typing import Optional
from slack_sdc import WebClient


class Logger:
    """
    Logging wrapper class to send warning logs and above to slack.
    """

    def __init__(
        self,
        name: str = __name__,
        level: int = logging.INFO,
        filename: Optional[str] = None,
    ):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self.formatter = logging.Formatter("%(levelname)s - %(message)s")
        self._logger.setFormatter(self.formatter)

        if "SLACK_BOT_TOKEN" in os.environ:
            self.slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

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

    def _post_to_slack(self, msg):
        """
        Post log to slack
        """
        if self.slack_client:
            self.slack_client.chat_postMessage(
                channel=os.environ.get("SLACK_CHANNEL", "#alerts-ebbo"), text=msg
            )
        else:
            self._logger.info("Slack bot token not set")
