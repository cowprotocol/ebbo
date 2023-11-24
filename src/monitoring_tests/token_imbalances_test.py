"""
Comparing order surplus per token pair to a reference solver in the competition.
"""
# pylint: disable=logging-fstring-interpolation
# pylint: disable=duplicate-code

from typing import Any
from fractions import Fraction
from web3.types import TxData
from src.monitoring_tests.base_test import BaseTest
from src.apis.web3api import Web3API
from src.apis.tenderlyapi import TenderlyAPI
from src.apis.coingeckoapi import CoingeckoAPI
from src.apis.tokenlistapi import TokenListAPI
from src.constants import SETTLEMENT_CONTRACT_ADDRESS

ETH_FLOW_ADDRESS = "0x40a50cf069e992aa4536211b23f286ef88752187"
ETH_ADDRESS = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
WETH_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"


class TokenImbalancesTest(BaseTest):
    """Test settlement for token imbalances."""

    def __init__(self) -> None:
        super().__init__()
        self.web3_api = Web3API()
        self.tenderly_api = TenderlyAPI()
        self.coingecko_api = CoingeckoAPI()
        self.tokenlist_api = TokenListAPI()

    def compute_token_imbalances(
        self, transaction: TxData, trace: dict[str, Any]
    ) -> dict[str, int]:
        """Compute token imbalances from transaction data.
        This is equal to the full imbalance of the settlement minus the imbalances due to fees.
        """

        full_token_imbalances = self.compute_full_token_imbalances(trace)
        fee_token_imbalances = self.compute_fee_token_imbalances(transaction)

        # combine token imbalances: full_token_imbalances - fee_token_imbalances
        result = {
            k: full_token_imbalances.get(k, 0) - fee_token_imbalances.get(k, 0)
            for k in set(full_token_imbalances) | set(fee_token_imbalances)
        }

        # remove all tokens with zero slippage
        result = {k: v for k, v in result.items() if v != 0}

        return result

    def compute_full_token_imbalances(self, trace: dict[str, Any]) -> dict[str, int]:
        """Compute full token imbalance from tenderly trace data.
        This includes imbalances due to fees or due to internalized trades."""
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

        for token_event in token_events:
            from_address = token_event["from"].lower()
            to_address = token_event.get(
                "to", ""
            ).lower()  # some token events do not have a "to" address field

            # If the settlement contract trades, then ignore all transfers from it
            # to itself. Those transfers are covered by trade events.
            if (
                from_address == SETTLEMENT_CONTRACT_ADDRESS.lower()
                and to_address == SETTLEMENT_CONTRACT_ADDRESS.lower()
            ):
                continue

            sign = 1
            if from_address == SETTLEMENT_CONTRACT_ADDRESS.lower():
                sign = -1

            address = token_event["assetInfo"].get("contractAddress", ETH_ADDRESS)
            result[address] = result.get(address, 0) + sign * int(
                token_event["rawAmount"], 16
            )

        return result

    def compute_fee_token_imbalances(self, transaction: TxData) -> dict[str, int]:
        """Compute fee token imbalance from transaction data."""
        settlement = self.web3_api.get_settlement(transaction)
        trades = self.web3_api.get_trades(settlement)

        result: dict[str, int] = {}
        for trade in trades:
            sell_token = trade.data.sell_token.lower()
            fee_amount = trade.execution.fee_amount
            result[sell_token] = fee_amount

        return result

    def compute_contract_trading_token_imbalances(self) -> dict[str, int]:
        """Compute token imbalance due to trading of the settlement contract.
        This is relevant for correct accounting in settlements where the settlement contract is one
        of the traders.
        This is NOT implemented yet."""
        result: dict[str, int] = {}
        return result

    def compute_internalized_token_imbalances(self) -> dict[str, int]:
        """Compute token imbalance due to internalized trades.
        This is NOT implemented yet."""
        result: dict[str, int] = {}
        return result

    def get_token_prices_in_eth(
        self, tokens: list[str]
    ) -> dict[str, Fraction | None] | None:
        """Get prices in ETH for all tokens in a list.
        Uses the coingecko api for prices and token lists for decimals."""
        result: dict[str, Fraction | None] = {}
        eth_price = self.coingecko_api.get_token_price_in_usd(WETH_ADDRESS)
        decimals = self.tokenlist_api.get_token_decimals()
        if eth_price is None or decimals is None:
            return None

        for address in tokens:
            token_price_usd = self.coingecko_api.get_token_price_in_usd(address)
            token_decimals = decimals.get(address, None)
            if token_price_usd is None or token_decimals is None:
                result[address] = None
                continue

            result[address] = (
                Fraction(token_price_usd)
                / 10**token_decimals
                / Fraction(eth_price)
                * 10**18
            )
        return result

    def compute_token_imbalance_value(
        self, token_imbalances: dict[str, int], token_prices: dict[str, Fraction | None]
    ) -> Fraction:
        """Computes the ETH value of token imbalances."""
        eth_value = Fraction(0)
        for token in token_imbalances:
            token_price = token_prices[token]
            if token_price is None:
                self.logger.warning(f"No price for token {token}.")
            else:
                eth_value += token_imbalances[token] * token_price
        return eth_value

    def run(self, tx_hash: str) -> bool:
        """Runs the token imbalances test."""

        transaction = self.web3_api.get_transaction(tx_hash)
        trace = self.tenderly_api.trace_transaction(tx_hash)
        if transaction is None or trace is None:
            return False

        token_imbalances = self.compute_token_imbalances(transaction, trace)

        token_prices = self.get_token_prices_in_eth(list(token_imbalances.keys()))
        if token_prices is None:
            return False

        eth_value = self.compute_token_imbalance_value(token_imbalances, token_prices)

        if eth_value > 10**17:  # does not conform to convention for logging yet.
            self.logger.warning(
                f"Large slippage detected for hash {tx_hash}: {float(eth_value) / 10**18:.5f} ETH"
                + f"(imbalances {token_imbalances} with prices {token_prices}"
            )

        return True
