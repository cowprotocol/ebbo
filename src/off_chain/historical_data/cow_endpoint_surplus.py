"""
EBBO Historical Data Testing via block number inputs or a single settlement hash.
Uses CoW Endpoint provided callData.
"""
import json
import requests
from fractions import Fraction
import directory
import configuration
from typing import List, Dict, Tuple, Any, Optional
import logging


class EBBOHistoricalDataTesting:
    def __init__(self, file_name: Optional[str] = None) -> None:
        self.total_orders = 0
        self.higher_surplus_orders = 0
        self.total_surplus_eth = 0.0
        self.file_name = file_name

        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f"{self.file_name}.log", mode="w"),
            ],
        )

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
        etherscan_url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={start_block}&endblock={end_block}&sort=desc&apikey={directory.ETHERSCAN_KEY}"
        # all "result" go into results (based on API return value names from docs)
        try:
            settlements = json.loads(
                (
                    requests.get(
                        etherscan_url,
                        headers=configuration.header,
                        timeout=1000000,
                    )
                ).text
            )["result"]
            settlement_hashes_list = []
            for settlement in settlements:
                settlement_hashes_list.append(settlement["hash"])
        except ValueError:
            logging.critical("etherscan error.")

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
            endpoint_url = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}"
            json_competition_data = requests.get(
                endpoint_url,
                headers=configuration.header,
                timeout=1000000,
            )
            if json_competition_data.status_code == 200:
                solver_competition_data.append(json.loads(json_competition_data.text))

        return solver_competition_data

    """
    This function goes through each order that the winning solution executed and finds non-winning
    solutions that executed the same rder and calculates surplus difference between that pair 
    (winning and non-winning solution). 
    Difference conversions to ETH and % deviations from traded amount have been made to check for flagging orders.
    """

    def get_order_surplus(self, competition_data: Dict[str, Any]) -> None:
        winning_solver = competition_data["solutions"][-1]["solver"]
        winning_orders = competition_data["solutions"][-1]["orders"]

        for individual_win_order in winning_orders:
            configuration.solver_dict[winning_solver][0] += 1
            self.total_orders += 1
            individual_win_order_id = individual_win_order["id"]
            order_data_url = (
                f"https://api.cow.fi/mainnet/api/v1/orders/{individual_win_order_id}"
            )
            json_order = requests.get(
                order_data_url,
                headers=configuration.header,
                timeout=1000000,
            )
            if json_order.status_code == 200:
                individual_order_data = json.loads(json_order.text)
                if individual_order_data["isLiquidityOrder"]:
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
            configuration.solver_dict[solver][1] += 1
            self.total_surplus_eth += sorted_values[0][0]

            if self.file_name == None:
                self.print_logs(
                    individual_order_id,
                    first_key,
                    solver,
                    competition_data,
                    sorted_values,
                )
                # write to file if file_name has a value passed from the tests file
            else:
                self.write_to_file(
                    individual_order_id,
                    first_key,
                    solver,
                    competition_data,
                    sorted_values,
                )

    def write_to_file(
        self,
        individual_order_id: str,
        first_key: int,
        solver: str,
        competition_data: Dict[str, Any],
        sorted_values: List[Tuple[float, float]],
    ) -> None:
        # with open(f"{self.file_name}", mode="a") as file:
        #     file.write(
        #         "Transaction Hash: " + competition_data["transactionHash"] + "\n"
        #     )
        #     file.write("For order: " + individual_order_id + "\n")
        #     file.write("Winning Solver: " + solver + "\n")
        #     file.write(
        #         "More surplus Corresponding Solver: "
        #         + competition_data["solutions"][first_key]["solver"]
        #         + "     Deviation: "
        #         + str(format(sorted_values[0][1], ".4f"))
        #         + "%"
        #         + "   absolute difference: "
        #         + str(format(sorted_values[0][0], ".5f"))
        #         + " ETH\n"
        #     )
        #     file.write("\n")
        #     file.close()
        logging.info("Transaction Hash: %s", competition_data["transactionHash"])
        logging.info("For order: %s", individual_order_id)
        logging.info("Winning Solver: %s", solver)
        logging.info(
            "More surplus Corresponding Solver: %s",
            competition_data["solutions"][first_key]["solver"],
        )
        logging.info("Deviation: %s", str(format(sorted_values[0][1], ".4f")) + "%")
        logging.info(
            "absolute difference: %s", str(format(sorted_values[0][0], ".5f")) + " ETH"
        )
        logging.info(" ")

    def print_logs(
        self,
        individual_order_id: str,
        first_key: int,
        solver: str,
        competition_data: Dict[str, Any],
        sorted_values: List[Tuple[float, float]],
    ) -> None:
        print("Transaction Hash: " + competition_data["transactionHash"])
        print("For order: " + individual_order_id)
        print("Winning Solver: " + solver)
        print(
            "More surplus Corresponding Solver: "
            + competition_data["solutions"][first_key]["solver"]
            + "     Deviation: "
            + str(format(sorted_values[0][1], ".4f"))
            + "%"
            + "   absolute difference: "
            + str(format(sorted_values[0][0], ".5f"))
            + " ETH"
        )
        print()

    def statistics_output(self, start_block: int, end_block: int) -> None:
        with open(f"{self.file_name}", mode="a") as file:
            file.write(
                f"Total Orders = {str(self.total_orders)} over {str(int(end_block)-int(start_block))} blocks from {str(start_block)} to {str(end_block)}\n"
            )
            file.write(
                "No. of better surplus orders: "
                + str(self.higher_surplus_orders)
                + "\n"
            )
            percent_better_offers = self.get_percent(
                self.higher_surplus_orders, self.total_orders
            )
            file.write(
                "Percent of potentially better offers: " + percent_better_offers + "%\n"
            )
            file.write(
                f"Total missed surplus: "
                + str(format(self.total_surplus_eth, ".3f"))
                + "ETH\n"
            )
            file.write("\n")

            for key in configuration.solver_dict:
                if configuration.solver_dict[key][0] == 0:
                    error_percent = 0.0
                else:
                    error_percent = (configuration.solver_dict[key][1] * 100) / (
                        configuration.solver_dict[key][0]
                    )
                file.write(
                    f"Solver: {key} errored: "
                    + str(format(error_percent, ".3f"))
                    + "%\n"
                )
            file.close()

    def get_percent(self, higher_surplus_orders: int, total_orders: int) -> str:
        percent = (higher_surplus_orders * 100) / total_orders
        string_percent = str(format(percent, ".3f"))
        return string_percent


"""
computes surplus difference given non-winning solution data and winning solution data.
"""


def get_surplus_difference(
    individual_order_data: Dict[str, Any],
    soln_clearingPrice: Dict[str, Any],
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
                * Fraction(soln_clearingPrice[sell_token])
                // Fraction(soln_clearingPrice[buy_token])
            )
            surplus = exec_amt - buy_amount
        else:
            exec_amt = int(
                Fraction(order["executedAmount"])
                * Fraction(soln_clearingPrice[sell_token])
                // Fraction(soln_clearingPrice[buy_token])
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
                * Fraction(soln_clearingPrice[buy_token])
                // Fraction(soln_clearingPrice[sell_token])
            )
            surplus = (
                sell_amount
                - int(individual_order_data["executedSurplusFee"])
                - exec_amt
            )
        else:
            exec_amt = int(
                Fraction(order["executedAmount"])
                * Fraction(soln_clearingPrice[buy_token])
                // Fraction(soln_clearingPrice[sell_token])
            )
            surplus = sell_amount - exec_amt

        diff_surplus = win_surplus - surplus
        percent_deviation = (diff_surplus * 100) / sell_amount
        surplus_token = individual_order_data["sellToken"]

    return (diff_surplus, percent_deviation, surplus_token)
