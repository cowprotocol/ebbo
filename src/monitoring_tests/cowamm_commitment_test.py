"""
Checks that commitments for custom CoW AMM of CoW AMM orders are reset.
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
    """Checks that commitments for custom CoW AMM of CoW AMM orders are reset

    Whenever a preinteraction calling the commit functinon of the (old) CoW AMM smart contract is
    called, the currently commit order on the corresponding CoW AMM is checked. If the commited
    order is not equal to the default order, the commitment was not reset.
    """

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.contract = self.web3_api.web_3.eth.contract(
            address=Address(HexBytes(COWAMM_CONSTANT_PRODUCT_ADDRESS)),
            abi=cowamm_constantproduct,
        )

    def check_commitments(self, settlement: dict[str, Any]) -> bool:
        """Checks the commitment of CoW AMM orders.

        If there is a preinteraction with a call to the commit function of the CoW AMM contant
        product smart contract, the commitment of that AMM is checked at the current point in
        time.

        This is not a check for including a commit in post interactions or within interactions.
        It also does not check if the uncommit happened immediately, but just checks if the
        current commitment is to the default order.
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
        decoded_interaction = self.contract.decode_function_input(
            interaction["callData"]
        )[1]
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
        Wrapper function for the whole test. Checks that commitments for custom CoW AMM of CoW
        AMM orders are reset
        """

        transaction = self.web3_api.get_transaction(tx_hash)
        if transaction is None:
            return False
        settlement = self.web3_api.get_settlement(transaction)

        success = self.check_commitments(settlement)

        return success
