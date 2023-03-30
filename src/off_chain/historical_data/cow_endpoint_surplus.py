"""
EBBO Historical Data Testing via block number inputs or a single settlement hash.
Uses CoW Endpoint provided callData.
"""
import json
import requests
from fractions import Fraction
import directory


class EBBOHistoricalDataTesting:
    def __init__(self, file_name):
        self.total_orders = 0
        self.higher_surplus_orders = 0
        self.total_surplus_eth = 0
        self.file_name = file_name

    """
    The below function takes start, end blocks as an input or solely the tx hash for EBBO testing.
    Adds all hashes to a list (between blocks or single hash) and fetches competition endpoint data for all of the hashes.
    Then calls on the get_order_surplus in a loop to compute potential better surplus for each settlement, if any.
    """
    def get_surplus_by_input(
        self, start_block=None, end_block=None, settlement_hash=None
    ) -> None:
        
        settlement_hashes_list = []

        if settlement_hash is not None:
            settlement_hashes_list.append(settlement_hash)

        elif start_block is not None and end_block is not None:
            # Etherscan endpoint call for settlements between start and end block
            try:
                etherscan_url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={start_block}&endblock={end_block}&sort=desc&apikey={directory.ETHERSCAN_KEY}"
                # all "result" go into results (based on API return value names from docs)
                settlements = json.loads((requests.get(etherscan_url)).text)["result"]
                settlement_hashes_list = []
                for set in settlements:
                    settlement_hashes_list.append(set["hash"])

            except ValueError:
                print("etherscan error.")

        solver_competition_data = self.get_solver_competition_data(settlement_hashes_list)
        for comp_data in solver_competition_data:
            self.get_order_surplus(comp_data)
            # self.statistics_output(start_block, end_block)


    def get_solver_competition_data(self, settlement_hashes_list):
        solver_competition_data = []
        for tx_hash in settlement_hashes_list:
            endpoint_url = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}" 
            json_competition_data = requests.get(endpoint_url)
            if json_competition_data.status_code == 200:
                solver_competition_data.append(json.loads(json_competition_data.text))

        return solver_competition_data


    def get_order_surplus(self, competition_data) -> None:

        winning_solution = competition_data["solutions"][-1]
        winning_solver = winning_solution["solver"]
        winning_orders = winning_solution["orders"]

        for individual_win_order in winning_orders:
            directory.solver_dict[winning_solver][0] += 1
            self.total_orders += 1
            individual_win_order_id = individual_win_order["id"]
            order_data_url = f"https://api.cow.fi/mainnet/api/v1/orders/{individual_win_order_id}"
            json_order = requests.get(order_data_url)
            if json_order.status_code == 200:
                individual_order_data = json.loads(json_order.text)
                if individual_order_data["isLiquidityOrder"]:
                    continue
                # printing "processing..." as a debug test to ensure running program
                print("processing...")
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


    def print_function(self, surplus_deviation_dict, individual_order_id,competition_data) -> None:
        sorted_dict = dict(
            sorted(surplus_deviation_dict.items(), key=lambda x: x[1][0])
        )
        sorted_values = sorted(sorted_dict.values(), key=lambda x: x[0])
        if sorted_values[0][0] < -0.001 and sorted_values[0][1] < -1:
            for key, value in sorted_dict.items():
                if value == sorted_values[0]:
                    first_key = key
                    break

            self.higher_surplus_orders += 1
            solver = competition_data["solutions"][-1]["solver"]
            directory.solver_dict[solver][1] += 1
            self.total_surplus_eth += sorted_values[0][0]

            # recurring write to file indicating a flagged order and details
            with open(f"{self.file_name}", mode="a") as file:
                # file.write("Settlement Hash: " + settlement_hash + "\n")
                file.write("For order: " + individual_order_id + "\n")
                file.write("Winning Solver: " + solver + "\n")
                file.write(
                    "More surplus Corresponding Solver: "
                    + competition_data["solutions"][first_key]["solver"]
                    + "     Deviation: "
                    + str(format(sorted_values[0][1], ".4f"))
                    + "%"
                    + "   absolute difference: "
                    + str(format(sorted_values[0][0], ".5f"))
                    + " ETH\n"
                )
                file.write("\n")
                file.close()

    def statistics_output(self, start_block, end_block) -> None:
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
            total_surplus_eth = self.total_surplus_eth
            file.write(
                f"Total missed surplus: "
                + str(format(total_surplus_eth, ".3f"))
                + "ETH\n"
            )
            file.write("\n")

            for key in directory.solver_dict:
                if directory.solver_dict[key][0] == 0:
                    error_percent = 0
                else:
                    error_percent = (directory.solver_dict[key][1] * 100) / (
                        directory.solver_dict[key][0]
                    )
                file.write(
                    f"Solver: {key} errored: "
                    + str(format(error_percent, ".3f"))
                    + "%\n"
                )
            file.close()

    def get_percent(self, higher_surplus_orders: int, total_orders: int):
        percent = (higher_surplus_orders * 100) / total_orders
        string_percent = str(format(percent, ".3f"))
        return string_percent


def get_surplus_difference(individual_order_data, soln_clearingPrice, order):
    buy_amount = int(individual_order_data["buyAmount"])
    sell_amount = int(individual_order_data["sellAmount"])
    sell_token = individual_order_data["sellToken"]
    buy_token = individual_order_data["buyToken"]
    kind = individual_order_data["kind"]

    if kind == "sell":
        win_surplus = (
            int(individual_order_data["executedBuyAmount"]) - buy_amount
        )
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