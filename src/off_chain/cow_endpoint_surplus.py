"""
EBBO Historical Data Testing via block number inputs or a single settlement hash.
Uses CoW Endpoint provided callData.
"""
import json
import requests
from fractions import Fraction
from config import ETHERSCAN_KEY
from src.off_chain.configuration import get_solver_dict, header, get_logger
from typing import List, Dict, Tuple, Any, Optional


class EBBOAnalysis:
    def __init__(self, file_name: Optional[str] = None) -> None:
        self.total_orders = 0
        self.higher_surplus_orders = 0
        self.total_surplus_eth = 0.0
        self.logger = get_logger(f"{file_name}")
        self.solver_dict = get_solver_dict()

    """
    Below function takes start, end blocks as an input or solely the tx hash for EBBO testing.
    Adds all hashes to a list (between blocks or single hash) and fetches competition endpoint data for all of the hashes.
    Then calls on the get_order_surplus in a loop to compute potential better surplus for each settlement, if any.
    """

    def get_surplus_by_input(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        settlement_hash: Optional[str] = None,
    ) -> None:
        settlement_hashes_list = []

        if settlement_hash is not None:
            settlement_hashes_list.append(settlement_hash)

        elif start_block is not None and end_block is not None:
            # Etherscan endpoint call for settlements between start and end block
            settlement_hashes_list = self.get_settlement_hashes(start_block, end_block)
        solver_competition_data = self.get_solver_competition_data(
            settlement_hashes_list
        )
        for comp_data in solver_competition_data:
            self.get_order_surplus(comp_data)

    """
    This function gets all hashes for a contract address between two blocks
    """

    def get_settlement_hashes(self, start_block: int, end_block: int) -> List[str]:
        etherscan_url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={start_block}&endblock={end_block}&sort=desc&apikey={ETHERSCAN_KEY}"
        # all "result" go into results (based on API return value names from docs)
        try:
            settlements = json.loads(
                (
                    requests.get(
                        etherscan_url,
                        headers=header,
                        timeout=30,
                    )
                ).text
            )["result"]
            settlement_hashes_list = []
            for settlement in settlements:
                settlement_hashes_list.append(settlement["hash"])
        except Exception as e:
            self.logger.error(f"Unhandled exception: {str(e)}.")

        return settlement_hashes_list

    """
    This function uses a list of tx hashes to fetch and assemble competition data
    for each of the tx hashes and returns it to get_surplus_by_input for further surplus calculation.
    """

    def get_solver_competition_data(
        self, settlement_hashes_list: List[str]
    ) -> List[Dict[str, Any]]:
        solver_competition_data = []
        for tx_hash in settlement_hashes_list:
            try:
                prod_endpoint_url = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}"
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
                    barn_endpoint_url = f"https://barn.api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}"
                    barn_competition_data = requests.get(
                        barn_endpoint_url, headers=header, timeout=30
                    )
                    if barn_competition_data == 200:
                        solver_competition_data.append(
                            json.loads(barn_competition_data)
                        )
                        # print(tx_hash)
            except Exception as e:
                self.logger.error(f"Unhandled exception: {str(e)}.")

        return solver_competition_data

    """
    get_order_data() uses an orderUID to fetch order data from CoW endpoint.
    Checks both production and staging.
    """

    def get_order_data(
        self, individual_win_order_id: str
    ) -> Tuple[Dict[str, Any], int]:
        individual_order_data = {}
        status_code = 0  # Set default values for these variables
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
                barn_order_data_url = f"https://barn.api.cow.fi/mainnet/api/v1/orders/{individual_win_order_id}"
                barn_order = requests.get(
                    barn_order_data_url, headers=header, timeout=30
                )
                if barn_order.status_code == 200:
                    individual_order_data = json.loads(barn_order.text)
                    status_code = barn_order.status_code
        except Exception as e:
            self.logger.error(f"endpoint might be down, Unhandled exception: {str(e)}.")

        return (individual_order_data, status_code)

    """
    This function goes through each order that the winning solution executed and finds non-winning
    solutions that executed the same order and calculates surplus difference between that pair 
    (winning and non-winning solution). 
    Difference conversions to ETH and % deviations from traded amount have been made to check for flagging orders.
    """

    def get_order_surplus(self, competition_data: Dict[str, Any]) -> None:
        winning_solver = competition_data["solutions"][-1]["solver"]
        winning_orders = competition_data["solutions"][-1]["orders"]

        for individual_win_order in winning_orders:
            self.solver_dict[winning_solver][0] += 1
            self.total_orders += 1
            individual_win_order_id = individual_win_order["id"]
            (individual_order_data, status_code) = self.get_order_data(
                individual_win_order_id
            )
            try:
                if individual_order_data["isLiquidityOrder"] or status_code != 200:
                    continue

                surplus_deviation_dict = {}
                soln_count = 0
                for soln in competition_data["solutions"]:
                    for order in soln["orders"]:
                        if individual_win_order_id == order["id"]:
                            (
                                diff_surplus,
                                percent_deviation,
                                surplus_token,
                            ) = get_surplus_difference(
                                individual_order_data, soln["clearingPrices"], order
                            )
                            surplus_eth = (
                                int(
                                    competition_data["auction"]["prices"][surplus_token]
                                )
                                / (pow(10, 18))
                            ) * (diff_surplus / pow(10, 18))
                            surplus_deviation_dict[soln_count] = (
                                surplus_eth,
                                percent_deviation,
                            )
                    soln_count += 1
                self.print_function(
                    surplus_deviation_dict,
                    individual_win_order_id,
                    competition_data,
                )
            except Exception as e:
                self.logger.error(f"Unhandled exception: {str(e)}.")

    def print_function(
        self,
        surplus_deviation_dict: Dict[int, Tuple[float, float]],
        individual_order_id: str,
        competition_data: Dict[str, Any],
    ) -> None:
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

            self.log_to_file(
                individual_order_id,
                first_key,
                solver,
                competition_data,
                sorted_values,
            )

    def log_to_file(
        self,
        individual_order_id: str,
        first_key: int,
        solver: str,
        competition_data: Dict[str, Any],
        sorted_values: List[Tuple[float, float]],
    ) -> None:
        self.logger.info("Transaction Hash: %s", competition_data["transactionHash"])
        self.logger.info("For order: %s", individual_order_id)
        self.logger.info("Winning Solver: %s", solver)
        self.logger.info(
            "More surplus Corresponding Solver: %s",
            competition_data["solutions"][first_key]["solver"],
        )
        self.logger.info("Deviation: %s", str(format(sorted_values[0][1], ".4f")) + "%")
        self.logger.info(
            "absolute difference: %s", str(format(sorted_values[0][0], ".5f")) + " ETH"
        )
        self.logger.info(" ")

    def statistics_output(self, start_block: int, end_block: int) -> None:
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
        for key in self.solver_dict:
            if self.solver_dict[key][0] == 0:
                error_percent = 0.0
            else:
                error_percent = (self.solver_dict[key][1] * 100) / (
                    self.solver_dict[key][0]
                )
            self.logger.info(
                "Solver: %s errored: %s%%", key, format(error_percent, ".3f")
            )

    def get_percent_better_orders(self) -> str:
        string_percent = str
        try:
            percent = (self.higher_surplus_orders * 100) / self.total_orders
            string_percent = str(format(percent, ".3f")) + "%"
        except:
            self.logger.critical("Number of orders = 0.")
        return string_percent


"""
computes surplus difference given non-winning solution data and winning solution data.
"""


def get_surplus_difference(
    individual_order_data: Dict[str, Any],
    soln_clearing_price: Dict[str, Any],
    order: Dict[str, Any],
) -> Tuple[int, float, str]:
    buy_amount = int(individual_order_data["buyAmount"])
    sell_amount = int(individual_order_data["sellAmount"])
    sell_token = individual_order_data["sellToken"]
    buy_token = individual_order_data["buyToken"]
    kind = individual_order_data["kind"]

    if kind == "sell":
        win_surplus = int(individual_order_data["executedBuyAmount"]) - buy_amount
        if individual_order_data["class"] == "limit":
            exec_amt = (
                (
                    int(Fraction(order["executedAmount"]))
                    - int(individual_order_data["executedSurplusFee"])
                )
                * Fraction(soln_clearing_price[sell_token])
                // Fraction(soln_clearing_price[buy_token])
            )
            surplus = exec_amt - buy_amount
        else:
            exec_amt = int(
                Fraction(order["executedAmount"])
                * Fraction(soln_clearing_price[sell_token])
                // Fraction(soln_clearing_price[buy_token])
            )
            surplus = exec_amt - buy_amount

        diff_surplus = win_surplus - surplus
        percent_deviation = (diff_surplus * 100) / buy_amount
        surplus_token = individual_order_data["buyToken"]

    elif kind == "buy":
        win_surplus = sell_amount - int(
            individual_order_data["executedSellAmountBeforeFees"]
        )
        if individual_order_data["class"] == "limit":
            exec_amt = (
                (int(Fraction(order["executedAmount"])))
                * Fraction(soln_clearing_price[buy_token])
                // Fraction(soln_clearing_price[sell_token])
            )
            surplus = (
                sell_amount
                - int(individual_order_data["executedSurplusFee"])
                - exec_amt
            )
        else:
            exec_amt = int(
                Fraction(order["executedAmount"])
                * Fraction(soln_clearing_price[buy_token])
                // Fraction(soln_clearing_price[sell_token])
            )
            surplus = sell_amount - exec_amt

        diff_surplus = win_surplus - surplus
        percent_deviation = (diff_surplus * 100) / sell_amount
        surplus_token = individual_order_data["sellToken"]

    return (diff_surplus, percent_deviation, surplus_token)
