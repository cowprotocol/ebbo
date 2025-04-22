"""
In this file, we introduce the BaseTest class, whose purpose is to be used as the basis
for all tests developed.
"""

# pylint: disable=logging-fstring-interpolation

import os
from abc import ABC, abstractmethod
from slack_sdk import WebClient
from src.helper_functions import get_logger


class BaseTest(ABC):
    """
    This is a BaseTest class that contains a few auxiliary functions that
    multiple tests might find useful. The intended usage is that every new test
    is a subclass of this class.
    """

    def __init__(self) -> None:
        self.tx_hashes: list[str] = []
        self.logger = get_logger()

        if "SLACK_BOT_TOKEN" in os.environ:
            self.slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
        else:
            self.slack_client = None

    @abstractmethod
    def run(self, tx_hash: str) -> bool:
        """
        This function runs the test. It must be implemented by all subclasses.
        The function returns `False` if the test should be run again for this hash and `True`
        otherwise.
        """

    def run_queue(self) -> None:
        """
        Run the test for all hashes in the list tx_hashes.
        """
        tx_hashes_fails: list[str] = []
        for tx_hash in self.tx_hashes:
            success = self.run(tx_hash)
            if not success:
                tx_hashes_fails.append(tx_hash)
        tx_hashes_success = [
            tx_hash for tx_hash in self.tx_hashes if tx_hash not in tx_hashes_fails
        ]
        self.logger.debug(
            f"Test ran successefully for hashes {tx_hashes_success} and"
            f"needs to be rerun for hashes {tx_hashes_fails}."
        )
        self.tx_hashes = tx_hashes_fails

    def add_hashes_to_queue(self, tx_hashes: list[str]) -> None:
        """
        Add a list of hashes to tx_hashes.
        """
        self.tx_hashes += tx_hashes

    def alert(self, msg: str) -> None:
        """
        This function is called to create an alert for a failed test.
        It must be implemented by all subclasses.
        """
        self.logger.error(msg)

        if self.slack_client:
            self.slack_client.chat_postMessage(
                channel=os.environ.get("SLACK_CHANNEL", "#alerts-ebbo"), text=msg
            )
