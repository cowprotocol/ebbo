"""
Comparing order surplus per token pair to a reference solver in the competition.
"""
# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from fractions import Fraction
from web3.types import TxData, TxReceipt
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.tenderlyapi import TenderlyAPI
from src.constants import SETTLEMENT_CONTRACT_ADDRESS

ETH_FLOW_ADDRESS = "0x40a50cf069e992aa4536211b23f286ef88752187"
ETH_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"


class TokenImbalancesTest(BaseTest):
    """Test settlement for token imbalances."""

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.tenderly_api = TenderlyAPI()

    def compute_token_imbalances(
        self, transaction: TxData, receipt: TxReceipt
    ) -> dict[str, int] | None:
        """Compute token imbalances from transaction data."""

        tx_hash = transaction["hash"].hex()
        settlement = self.web3_api.get_settlement(transaction)
        trace = self.tenderly_api.trace_transaction(tx_hash)
        if trace is None:
            return None

        trade_events = [
            trade_event
            for trade_event in trace["result"]["logs"]
            if trade_event["name"] == "Trade"
        ]

        trade_addresses: list[str] = []
        for trade in settlement["trades"]:
            trade_addresses.append(trade["receiver"].lower())
        for trade_event in trade_events:
            trade_addresses.append(trade_event["inputs"][0]["value"].lower())

        balance_change_indices = [
            bc["transfers"]
            for bc in trace["result"]["balanceChanges"]
            if bc["address"].lower() == SETTLEMENT_CONTRACT_ADDRESS.lower()
        ][0]

        token_events = [
            ac
            for i, ac in enumerate(trace["result"]["assetChanges"])
            if i in balance_change_indices
        ]

        result: dict[str, int] = {}

        for trade_event in trade_events:
            sell_token = trade_event["inputs"][1]["value"].lower()
            buy_token = trade_event["inputs"][2]["value"].lower()
            result[sell_token] = (
                result.get(sell_token, 0)
                + int(trade_event["inputs"][3]["value"])
                - int(trade_event["inputs"][5]["value"])
            )
            result[buy_token] = result.get(buy_token, 0) - int(
                trade_event["inputs"][4]["value"]
            )

        for token_event in token_events:
            from_address = token_event["from"].lower()
            to_address = token_event.get("to", "").lower()
            # ignore transfers to and from traders
            if (
                (
                    from_address in trade_addresses
                    and from_address != SETTLEMENT_CONTRACT_ADDRESS.lower()
                )
                or (
                    to_address in trade_addresses
                    and to_address != SETTLEMENT_CONTRACT_ADDRESS.lower()
                )
                # If the settlement contract trades, then ignore all transfers from it
                # to itself. Those transfers are covered by trade events.
                or (
                    from_address == SETTLEMENT_CONTRACT_ADDRESS.lower()
                    and to_address == SETTLEMENT_CONTRACT_ADDRESS.lower()
                )
            ):
                continue

            sign = 1
            if from_address == SETTLEMENT_CONTRACT_ADDRESS.lower():
                sign = -1

            address = token_event["assetInfo"].get("contractAddress", ETH_ADDRESS)
            result[address] = result.get(address, 0) + sign * int(
                Fraction(token_event["amount"])
                * 10 ** token_event["assetInfo"]["decimals"]
            )

        return result

    def run(self, tx_hash: str) -> bool:
        """Runs the token imbalances test."""

        receipt = self.web3_api.get_receipt(tx_hash)
        transaction = self.web3_api.get_transaction(tx_hash)
        if receipt is None or transaction is None:
            return False

        token_imbalances = self.compute_token_imbalances(transaction, receipt)

        return True
