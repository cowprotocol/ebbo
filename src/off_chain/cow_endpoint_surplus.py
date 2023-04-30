"""
This class is the first component of the EBBO Monitoring Suite. Orders of the winning
settlement are tested for EBBO relative to all other solutions provided.
Competition Data is fetched via the CoW API. 
"""
import json
import traceback
from typing import List, Dict, Tuple, Any, Optional
from web3 import Web3
import requests
from src.configuration import (
    get_logger,
    get_tx_hashes_by_block,
    get_surplus_order,
    percent_eth_conversions_order,
)
from src.quasimodo_ebbo.on_chain_surplus import DecodedSettlement
from src.constants import (
    INFURA_KEY,
    header,
    ADDRESS,
    ABSOLUTE_ETH_FLAG_AMOUNT,
    REL_DEVIATION_FLAG_PERCENT,
    SUCCESS_CODE,
    FAIL_CODE,
)
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi


class EndpointSolutionsEBBO:
    """
    initialization of logging object, and vars for analytics report.
    """

    def __init__(self, file_name: Optional[str] = None) -> None:
        self.logger = get_logger(f"{file_name}")
        self.web_3 = Web3(
            Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}")
        )
        self.contract_instance = self.web_3.eth.contract(address=ADDRESS, abi=gpv2Abi)

    def get_surplus_by_input(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        settlement_hash: Optional[str] = None,
    ) -> None:
        """
        Below function takes start, end blocks as an input or solely the tx hash for EBBO testing.
        Adds all hashes to a list (between blocks or single hash) and fetches competition endpoint
        data for all of the hashes, and calls on get_order_surplus by passing the list.
        """
        settlement_hashes_list = []

        if settlement_hash is not None:
            settlement_hashes_list.append(settlement_hash)

        elif start_block is not None and end_block is not None:
            # get list of hashes within a range of blocks for GPV2 Settlement Contract
            settlement_hashes_list = get_tx_hashes_by_block(
                self.web_3, start_block, end_block
            )
        if not settlement_hashes_list:
            raise ValueError("No settlement hashes found")

        solver_competition_data = self.get_solver_competition_data(
            settlement_hashes_list
        )
        for comp_data in solver_competition_data:
            self.get_order_surplus(comp_data)

    def get_solver_competition_data(
        self, settlement_hashes_list: List[str]
    ) -> List[Dict[str, Any]]:
        """
        This function uses a list of tx hashes to fetch and assemble competition data
        for each of the tx hashes and returns it to get_surplus_by_input for further
        surplus calculation.
        """

        solver_competition_data = []
        for tx_hash in settlement_hashes_list:
            try:
                prod_endpoint_url = (
                    "https://api.cow.fi/mainnet/api/v1/solver_competition"
                    f"/by_tx_hash/{tx_hash}"
                )
                json_competition_data = requests.get(
                    prod_endpoint_url,
                    headers=header,
                    timeout=30,
                )
                if json_competition_data.status_code == SUCCESS_CODE:
                    solver_competition_data.append(
                        json.loads(json_competition_data.text)
                    )
                    # print(tx_hash)
                elif json_competition_data.status_code == FAIL_CODE:
                    barn_endpoint_url = (
                        "https://barn.api.cow.fi/mainnet/api/v1"
                        f"/solver_competition/by_tx_hash/{tx_hash}"
                    )
                    barn_competition_data = requests.get(
                        barn_endpoint_url, headers=header, timeout=30
                    )
                    if barn_competition_data.status_code == SUCCESS_CODE:
                        solver_competition_data.append(
                            json.loads(barn_competition_data.text)
                        )
            except ValueError as except_err:
                self.logger.error("Unhandled exception: %s.", str(except_err))

        return solver_competition_data

    def get_decoded_settlement(self, tx_hash: str):
        """
        Takes settlement hash as input, returns decoded settlement data.
        """
        encoded_transaction = self.web_3.eth.get_transaction(tx_hash)
        decoded_settlement = DecodedSettlement.new(
            self.contract_instance, encoded_transaction.input
        )
        return (
            decoded_settlement.trades,
            decoded_settlement.clearing_prices,
            decoded_settlement.tokens,
        )

    def get_onchain_order_data(self, trade, onchain_clearing_prices, tokens):
        """
        Returns required data to calculate surplus for winning order
        using onchain data from decoded settlement.
        """
        return {
            "sell_token_clearing_price": onchain_clearing_prices[
                trade["sellTokenIndex"]
            ],
            "buy_token_clearing_price": onchain_clearing_prices[trade["buyTokenIndex"]],
            "sell_token": tokens[trade["sellTokenIndex"]].lower(),
            "buy_token": tokens[trade["buyTokenIndex"]].lower(),
            "order_type": str(f"{trade['flags']:08b}")[-1],
            "executed_amount": trade["executedAmount"],
            "sell_amount": trade["sellAmount"],
            "buy_amount": trade["buyAmount"],
            "fee_amount": trade["feeAmount"],
        }

    def get_order_surplus(self, competition_data: Dict[str, Any]) -> None:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """
        trades, onchain_clearing_prices, tokens = self.get_decoded_settlement(
            competition_data["transactionHash"]
        )
        # this loop iterates over a single trade from on-chain trades (decoded data)
        # and order from the list of settled orders in the winning solution. We
        # do this since the corresponding order ID for the trade needs to be chosen.

        # zip is used for simultaneous iteration.
        for trade, individual_win_order in zip(
            trades, competition_data["solutions"][-1]["orders"]
        ):
            onchain_order_data = self.get_onchain_order_data(
                trade, onchain_clearing_prices, tokens
            )
            try:
                # ignore limit orders, represented by zero fee amount
                if onchain_order_data["fee_amount"] == 0:
                    continue

                surplus_deviation_dict = {}
                soln_count = 0
                for soln in competition_data["solutions"]:
                    # ignore negative objective solutions
                    if soln["objective"]["total"] < 0:
                        # this adds ETH surplus, percent deviation for a solution
                        surplus_deviation_dict[soln_count] = 0.0, 0.0
                        soln_count += 1
                        continue
                    for order in soln["orders"]:
                        if individual_win_order["id"] == order["id"]:
                            # order data, executed amount, clearing price vector, and
                            # external prices are passed
                            surplus_eth, percent_deviation = get_flagging_values(
                                onchain_order_data,
                                int(order["executedAmount"]),
                                soln["clearingPrices"],
                                competition_data["auction"]["prices"],
                            )
                            surplus_deviation_dict[soln_count] = (
                                surplus_eth,
                                percent_deviation,
                            )
                    soln_count += 1
                self.flagging_order_check(
                    surplus_deviation_dict,
                    individual_win_order["id"],
                    competition_data,
                )
            except TypeError as except_err:
                self.logger.error("Unhandled exception: %s.", str(except_err))
                self.logger.error(traceback.format_exc())

    def flagging_order_check(
        self,
        surplus_deviation_dict: Dict[int, Tuple[float, float]],
        individual_order_id: str,
        competition_data: Dict[str, Any],
    ) -> None:
        """
        Below function finds the solution that could have been given a better surplus (if any) and
        checks whether if meets the flagging conditions. If yes, logging function is called.
        """

        sorted_dict = dict(
            sorted(surplus_deviation_dict.items(), key=lambda x: x[1][0])
        )
        sorted_values = sorted(sorted_dict.values(), key=lambda x: x[0])
        if (
            sorted_values[0][0] < -ABSOLUTE_ETH_FLAG_AMOUNT
            and sorted_values[0][1] < -REL_DEVIATION_FLAG_PERCENT
        ):
            for key, value in sorted_dict.items():
                if value == sorted_values[0]:
                    first_key = key
                    break
            winning_solver = competition_data["solutions"][-1]["solver"]

            self.logging_function(
                individual_order_id,
                first_key,
                winning_solver,
                competition_data,
                sorted_values,
            )

    def logging_function(
        self,
        individual_order_id: str,
        first_key: int,
        winning_solver: str,
        competition_data: Dict[str, Any],
        sorted_values: List[Tuple[float, float]],
    ) -> None:
        """
        Logs to terminal (and file iff file_name is passed).
        """

        self.logger.info(
            "Transaction Hash: %s\nFor order: %s\nWinning Solver: %s\n"
            "More surplus Corresponding Solver: %s\nDeviation: %s\n"
            "absolute difference: %s\n",
            competition_data["transactionHash"],
            individual_order_id,
            winning_solver,
            competition_data["solutions"][first_key]["solver"],
            str(format(sorted_values[0][1], ".4f")) + "%",
            str(format(sorted_values[0][0], ".5f")) + " ETH",
        )


def get_flagging_values(
    onchain_order_data, executed_amount, clearing_prices, external_prices
):
    """
    This function calculates surplus for solution, compares to winning
    solution to get surplus difference, and finally returns percent_deviations
    and surplus difference in eth based on external prices.
    """
    if onchain_order_data["order_type"] == "1":  # buy order
        # in this case, it is sell amount
        buy_or_sell_amount = int(onchain_order_data["sell_amount"])
        conversion_external_price = int(
            external_prices[onchain_order_data["sell_token"]]
        )
    elif onchain_order_data["order_type"] == "0":  # sell order
        # in this case, it is buy amount
        buy_or_sell_amount = int(onchain_order_data["buy_amount"])
        conversion_external_price = int(
            external_prices[onchain_order_data["buy_token"]]
        )

    win_surplus = get_surplus_order(
        executed_amount,
        buy_or_sell_amount,
        onchain_order_data["sell_token_clearing_price"],
        onchain_order_data["buy_token_clearing_price"],
        onchain_order_data["order_type"],
    )

    soln_surplus = get_surplus_order(
        executed_amount,
        buy_or_sell_amount,
        clearing_prices[onchain_order_data["sell_token"]],
        clearing_prices[onchain_order_data["buy_token"]],
        onchain_order_data["order_type"],
    )
    # difference in surplus
    diff_surplus = win_surplus - soln_surplus

    percent_deviation, surplus_eth = percent_eth_conversions_order(
        diff_surplus,
        buy_or_sell_amount,
        conversion_external_price,
    )
    # divide by 10**18 to convert to ETH, consistent with quasimodo test
    surplus_eth = surplus_eth / pow(10, 18)
    return surplus_eth, percent_deviation
