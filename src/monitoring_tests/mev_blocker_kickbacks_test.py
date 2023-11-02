"""
Checks whether there were any kickbacks received after each settlement.
It generates an alert when kickbacks due to a specific settlement are
more than KICKBACKS_ALERT_THRESHOLD
"""
# pylint: disable=logging-fstring-interpolation
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.constants import (
    MEV_BLOCKER_KICKBACKS_ADDRESS,
    KICKBACKS_ALERT_THRESHOLD,
)


class MEVBlockerRefundsMonitoringTest(BaseTest):
    """
    This test checks whether there was any MEV Blocker kicback, and
    generates a log/alert if this is the case.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if kickback is more than
        KICKBACK_ETH_THRESHOLD, in which case it generates an alert.
        """
        block_number = self.web3_api.get_tx_block_number(tx_hash)
        if block_number is None:
            return False

        total_eth_kickbacks = self.web3_api.get_eth_transfers_by_block_range(
            block_number, block_number, MEV_BLOCKER_KICKBACKS_ADDRESS
        )
        if total_eth_kickbacks is None:
            return False
        log_msg = f'"Kickback of {total_eth_kickbacks} ETH received due to {tx_hash}"'
        if total_eth_kickbacks >= KICKBACKS_ALERT_THRESHOLD:
            self.alert(log_msg)
        else:
            self.logger.info(log_msg)
        return True
