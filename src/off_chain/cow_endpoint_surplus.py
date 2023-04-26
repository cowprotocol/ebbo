"""
EBBO Historical Data Testing via block number inputs or a single settlement hash.
Uses CoW Endpoint provided callData.
"""
import json
import os
from web3 import Web3
from typing import List, Dict, Tuple, Any, Optional
from dotenv import load_dotenv
import requests
from src.configuration import *
from src.on_chain.on_chain_surplus import DecodedSettlement
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi

load_dotenv()
INFURA_KEY = os.getenv("INFURA_KEY")


class EBBOAnalysis:
    """
    initialization of logging object, and vars for analytics report.
    """

    def __init__(self, file_name: Optional[str] = None) -> None:
        self.total_orders = 0
        self.higher_surplus_orders = 0
        self.total_surplus_eth = 0.0
        self.logger = get_logger(f"{file_name}")
        self.solver_dict = get_solver_dict()
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
        data for all of the hashes.
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
                if json_competition_data.status_code == 200:
                    solver_competition_data.append(
                        json.loads(json_competition_data.text)
                    )
                    # print(tx_hash)
                elif json_competition_data.status_code == 404:
                    barn_endpoint_url = (
                        "https://barn.api.cow.fi/mainnet/api/v1"
                        f"/solver_competition/by_tx_hash/{tx_hash}"
                    )
                    barn_competition_data = requests.get(
                        barn_endpoint_url, headers=header, timeout=30
                    )
                    if barn_competition_data.status_code == 200:
                        solver_competition_data.append(
                            json.loads(barn_competition_data.text)
                        )
            except ValueError as except_err:
                self.logger.error("Unhandled exception: %s.", str(except_err))

        return solver_competition_data

    def get_order_data(
        self, individual_win_order_id: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        This function uses an orderUID to fetch order data from CoW endpoint.
        Checks both production and staging.
        """

        individual_order_data = {}
        status_code = 0
        try:
            prod_order_data_url = (
                f"https://api.cow.fi/mainnet/api/v1/orders/{individual_win_order_id}"
            )
            prod_order = requests.get(
                prod_order_data_url,
                headers=header,
                timeout=30,
            )
            if prod_order.status_code == 200:
                individual_order_data = json.loads(prod_order.text)
                status_code = prod_order.status_code

            elif prod_order.status_code == 404:
                barn_order_data_url = (
                    "https://barn.api.cow.fi/mainnet/api/v1"
                    f"/orders/{individual_win_order_id}"
                )
                barn_order = requests.get(
                    barn_order_data_url, headers=header, timeout=30
                )
                if barn_order.status_code == 200:
                    individual_order_data = json.loads(barn_order.text)
                    status_code = barn_order.status_code
        except ValueError as except_err:
            self.logger.error(
                "Endpoint might be down, Unhandled exception: %s.", str(except_err)
            )

        return (individual_order_data, status_code)

    def get_decoded_settlement(self, tx_hash):
        encoded_transaction = self.web_3.eth.get_transaction(tx_hash)
        decoded_settlement = DecodedSettlement.new(
            self.contract_instance, encoded_transaction.input
        )
        return (
            decoded_settlement.trades,
            decoded_settlement.clearing_prices,
        )
    
    def get_onchain_order_data(trade, onchain_clearing_prices):
        return {
            "sell_token_clearing_price": onchain_clearing_prices[trade["sellTokenIndex"]],
            "buy_token_clearing_price": onchain_clearing_prices[trade["buyTokenIndex"]],
            "order_type": str("{0:08b}".format(trade["flags"])),
            "executed_amount": trade["executedAmount"],
            "sell_amount": trade["sellAmount"],
            "buy_amount": trade["buyAmount"],
        }


    def get_order_surplus(self, competition_data: Dict[str, Any]) -> None:
        """
        This function goes through each order that the winning solution executed
        and finds non-winning solutions that executed the same order and
        calculates surplus difference between that pair (winning and non-winning solution).
        """
        winning_solver = competition_data["solutions"][-1]["solver"]
        trades, onchain_clearing_prices = self.get_decoded_settlement(competition_data["transactionHash"])
        for trade in trades:
            onchain_order_data = self.get_onchain_order_data(trade, onchain_clearing_prices)

        for individual_win_order in competition_data["solutions"][-1]["orders"]:
            self.solver_dict[winning_solver][0] += 1
            self.total_orders += 1
            (individual_order_data, status_code) = self.get_order_data(
                individual_win_order["id"]
            )
            try:
                if (
                    individual_order_data["isLiquidityOrder"]
                    or individual_order_data["class"] == "limit"
                    or status_code != 200
                ):
                    continue

                surplus_deviation_dict = {}
                soln_count = 0
                for soln in competition_data["solutions"]:
                    if soln["objective"]["total"] < 0:
                        surplus_deviation_dict[soln_count] = 0.0, 0.0
                        soln_count += 1
                        continue
                    for order in soln["orders"]:
                        if individual_win_order["id"] == order["id"]:
                            # order data, executed amount, clearing price vector, and
                            # external prices are passed
                            percent_deviation, surplus_eth = get_flagging_values(
                                individual_order_data,
                                order["executedAmount"],
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
        if sorted_values[0][0] < -0.002 and sorted_values[0][1] < -0.1:
            for key, value in sorted_dict.items():
                if value == sorted_values[0]:
                    first_key = key
                    break

            self.higher_surplus_orders += 1
            solver = competition_data["solutions"][-1]["solver"]
            self.solver_dict[solver][1] += 1
            self.total_surplus_eth += sorted_values[0][0]

            self.logging_function(
                individual_order_id,
                first_key,
                solver,
                competition_data,
                sorted_values,
            )

    def logging_function(
        self,
        individual_order_id: str,
        first_key: int,
        solver: str,
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
            solver,
            competition_data["solutions"][first_key]["solver"],
            str(format(sorted_values[0][1], ".4f")) + "%",
            str(format(sorted_values[0][0], ".5f")) + " ETH",
        )

    def statistics_output(self, start_block: int, end_block: int) -> None:
        """
        statistics_output() provides an analytics report over the range of blocks searched for
        finding better surplus. Includes percent error by solvers, percent of all orders with
        better surplus, total ETH value potentially missed, etc.
        """

        self.logger.info(
            "Better Surplus Potential orders percent: %s,      total missed ETH value: %s",
            self.get_percent_better_orders(),
            str(format(self.total_surplus_eth, ".5f")),
        )
        self.logger.info(
            "Total Orders = %s over %s blocks from %s to %s",
            str(self.total_orders),
            str(int(end_block) - int(start_block)),
            str(start_block),
            str(end_block),
        )
        for key, value in self.solver_dict.items():
            if value[0] == 0:
                error_percent = 0.0
            else:
                error_percent = (value[1] * 100) / (value[0])
            self.logger.info(
                "Solver: %s errored: %s%%", key, format(error_percent, ".3f")
            )

    def get_percent_better_orders(self) -> str:
        """
        get_percent_better_orders() returns the percent of better orders.
        """
        try:
            percent = (self.higher_surplus_orders * 100) / self.total_orders
            string_percent = str(format(percent, ".3f")) + "%"
        except ValueError as except_err:
            self.logger.error(
                "Possibly no. of orders = 0, Unhandled exception: %s.", str(except_err)
            )
        return string_percent


def get_flagging_values(
    individual_order_data, executed_amount, clearing_prices, external_prices
):
    order_type = individual_order_data["kind"]
    sell_token = individual_order_data["sellToken"]
    buy_token = individual_order_data["buyToken"]

    if order_type == "buy":
        win_surplus = int(individual_order_data["sellAmount"]) - int(
            individual_order_data["executedSellAmountBeforeFees"]
        )
        soln_surplus = get_surplus_buy_order(
            executed_amount,
            int(individual_order_data["sellAmount"]),
            clearing_prices[sell_token],
            clearing_prices[buy_token],
        )
        diff_surplus = win_surplus - soln_surplus
        # surplus_token is sell_token for buy order
        percent_deviation, surplus_eth = percent_eth_conversions_buy_order(
            diff_surplus,
            int(individual_order_data["sellAmount"]),
            int(external_prices[sell_token]),
        )
    elif order_type == "sell":
        win_surplus = int(individual_order_data["executedBuyAmount"]) - int(
            individual_order_data["buyAmount"]
        )
        soln_surplus = get_surplus_sell_order(
            executed_amount,
            int(individual_order_data["buyAmount"]),
            clearing_prices[sell_token],
            clearing_prices[buy_token],
        )
        diff_surplus = win_surplus - soln_surplus
        # surplus_token is buy_token for sell order
        percent_deviation, surplus_eth = percent_eth_conversions_sell_order(
            diff_surplus,
            int(individual_order_data["buyAmount"]),
            int(external_prices[buy_token]),
        )
    return percent_deviation, surplus_eth
