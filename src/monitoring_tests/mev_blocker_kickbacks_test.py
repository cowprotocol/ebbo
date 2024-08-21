"""
Checks whether there were any kickbacks received after each settlement.
It generates an alert when kickbacks due to a specific settlement are
more than KICKBACKS_ALERT_THRESHOLD
"""
# pylint: disable=logging-fstring-interpolation
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.constants import (
    COW_DAO_MEV_BLOCKER_KICKBACKS_ADDRESS,
    COPIUM_MEV_BLOCKER_KICKBACKS_ADDRESS,
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

        cow_dao_total_eth_kickbacks = self.web3_api.get_eth_transfers_by_block_range(
            block_number, block_number, COW_DAO_MEV_BLOCKER_KICKBACKS_ADDRESS
        )
        copium_total_eth_kickbacks = self.web3_api.get_eth_transfers_by_block_range(
            block_number, block_number, COPIUM_MEV_BLOCKER_KICKBACKS_ADDRESS
        )
        eth_kickbacks = None
        if cow_dao_total_eth_kickbacks is not None:
            eth_kickbacks = cow_dao_total_eth_kickbacks
        if copium_total_eth_kickbacks is not None:
            eth_kickbacks = copium_total_eth_kickbacks

        if eth_kickbacks is None:
            return False
        log_output = "\t".join(
            [
                "MEV Blocker kickbacks test:",
                f"Tx Hash: {tx_hash}",
                f"Kickback: {eth_kickbacks:.5f}ETH",
            ]
        )
        if eth_kickbacks >= KICKBACKS_ALERT_THRESHOLD:
            self.alert(log_output)
        else:
            self.logger.info(log_output)
        return True
