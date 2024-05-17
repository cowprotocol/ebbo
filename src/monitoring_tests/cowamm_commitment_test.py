"""
Checks that surplus of CoW AMM jit orders equals nonlinear surplus.
"""
# pylint: disable=duplicate-code
from typing import Any

from eth_typing import Address
from hexbytes import HexBytes

from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API

from contracts.cowamm_constantproduct import cowamm_constantproduct

EMPTY_COMMITMENT = "0x0000000000000000000000000000000000000000000000000000000000000000"
COWAMM_CONSTANT_PRODUCT_ADDRESS = "0x34323B933096534e43958F6c7Bf44F2Bb59424DA".lower()


class CoWAMMCommitmentTest(BaseTest):
    """
    This test checks whether the Uniform Directed Prices constraint,
    as introduced in CIP-38, is satisfied.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.contract = self.web3_api.web_3.eth.contract(
            address=Address(HexBytes(COWAMM_CONSTANT_PRODUCT_ADDRESS)),
            abi=cowamm_constantproduct,
        )

    def check_commitments(self, settlement: dict[str, Any]) -> bool:
        """
        This function checks whether there are multiple orders in the same directed token pair,
        and if so, checks whether UDP is satisfied.
        """
        # iterate over pre-interactions
        for interaction in settlement["interactions"][0]:
            if interaction["target"] != COWAMM_CONSTANT_PRODUCT_ADDRESS:
                continue

            cowamm_address = self.get_cowamm_address(interaction)

            commitment = self.get_commitment(cowamm_address)
            if commitment is None:
                return False

            commitment_is_reset = commitment == EMPTY_COMMITMENT

            log_output = "\t".join(
                [
                    "CoW AMM Commitment test",
                    f"Commitment reset: {commitment_is_reset}",
                    f"CoW AMM: {cowamm_address}",
                    f"Commitment: {commitment}",
                ]
            )
            if not commitment_is_reset:
                self.alert(log_output)
            else:
                self.logger.info(log_output)

        return True

    def get_cowamm_address(self, interaction: dict[str, Any]) -> str:
        """Get the address of the CoW AMM from the commit interaction"""
        decoded_interaction = self.contract.decode_function_input(interaction["callData"])[1]
        cowamm_address = str(decoded_interaction["owner"])
        return cowamm_address

    def get_commitment(self, cowamm: str) -> str | None:
        """Get the commited order for a given CoW AMM
        It calls the commitment function in the smart contract for a given address and returns a
        string of the format "0x...".
        """
        return "0x" + str(self.contract.functions.commitment(cowamm).call().hex())

    def run(self, tx_hash: str) -> bool:
        """
        Wrapper function for the whole test. Checks if violation is more than
        UDP_SENSITIVITY_THRESHOLD, in which case it generates an alert.
        """

        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)

        success = self.check_commitments(settlement)

        return success
