"""
EBBO Historical Data Testing via block number inputs or a single settlement hash.
Uses CoW Endpoint provided callData.
"""
import json
import requests
from fractions import Fraction
import directory

class EBBOHistoricalDataTesting:

    def __init__(self):
        self.total_orders = 0
        self.higher_surplus_orders = 0
        self.total_surplus_eth = 0
        self.file_name = str

        self.solver_dict = {
            "1Inch": [0, 0],
            "Raven": [0, 0],
            "0x": [0, 0],
            "PLM": [0, 0],
            "Quasilabs": [0, 0],
            "Otex": [0, 0],
            "SeaSolver": [0, 0],
            "Laertes": [0, 0],
            "ParaSwap": [0, 0],
            "BalancerSOR": [0, 0],
            "BaselineSolver": [0, 0],
            "Legacy": [0, 0],
            "NaiveSolver": [0, 0],
            "DMA": [0, 0],
            "CowDexAg": [0, 0],
            "Barter": [0, 0],
        }

    def total_surplus(self, start_block=None, end_block=None, settlement_hash=None, file_name=None):
        self.file_name = file_name

        if settlement_hash is not None:
            self.get_order_surplus(settlement_hash)

        elif start_block is not None and end_block is not None:
            # Etherscan endpoint call for settlements between start and end block
            try:
                etherscan_url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={start_block}&endblock={end_block}&sort=desc&apikey={directory.ETHERSCAN_KEY}"
                # all "result" go into results (based on API return value names from docs)
                settlements = json.loads((requests.get(etherscan_url)).text)["result"]

                # loop over all settlements and get surplus difference for each
                for settlement in settlements:
                    self.get_order_surplus(settlement["hash"])
                self.statistics_output(start_block, end_block)
            except ValueError:
                print("etherscan error.")

    def get_order_surplus(self, settlement_hash: str):
        # Once we have settlement transaction hashes, call competition endpoint to get solver data
        endpoint_url = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlement_hash}"
        json_competition_data = requests.get(endpoint_url)

        if json_competition_data.status_code == 200:
            competition_data = json.loads(json_competition_data.text)
            winning_solution = competition_data["solutions"][-1]
            winning_solver = winning_solution["solver"]
            winning_orders = winning_solution["orders"]

            for individual_win_order in winning_orders:
                self.solver_dict[winning_solver][0] += 1
                self.total_orders = self.total_orders + 1
                individual_win_order_id = individual_win_order["id"]
                order_data_url = f"https://api.cow.fi/mainnet/api/v1/orders/{individual_win_order_id}"
                json_order = requests.get(order_data_url)
                if json_order.status_code == 200:
                    individual_order_data = json.loads(json_order.text)
                    if individual_order_data["isLiquidityOrder"] is False:
                    # printing settlement_hash as a debug test
                        print(settlement_hash)
                        surplus_deviation_dict = {}
                        soln_count = 0
                        for soln in competition_data["solutions"]:
                            for order in soln["orders"]:
                                if individual_win_order_id == order["id"]:
                                    diff_surplus, percent_deviation, surplus_token = self.get_surplus_difference(
                                        individual_order_data, soln, order
                                    )
                                    surplus_eth = (
                                        int(competition_data["auction"]["prices"][surplus_token])
                                        / (pow(10, 18))
                                    ) * (diff_surplus / pow(10, 18))
                                    surplus_deviation_dict[soln_count] = surplus_eth, percent_deviation
                            soln_count += 1
                        self.print_function(
                            surplus_deviation_dict, settlement_hash, individual_win_order_id, competition_data
                        )
        else:
            print("not able to fetch data from competition endpoint.")


    def get_surplus_difference(self, individual_order_data, soln, order):
        buy_amount_from_id = int(individual_order_data["buyAmount"])
        sell_amount_from_id = int(individual_order_data["sellAmount"])
        sell_token = individual_order_data["sellToken"]
        buy_token = individual_order_data["buyToken"]
        kind = individual_order_data["kind"]

        if kind == "sell":
            win_surplus = int(individual_order_data["executedBuyAmount"]) - buy_amount_from_id
            if individual_order_data["class"] == "limit":
                exec_amt = (
                    (int(Fraction(order["executedAmount"]))
                    - int(individual_order_data["executedSurplusFee"]))
                    * Fraction(soln["clearingPrices"][sell_token])
                    // Fraction(soln["clearingPrices"][buy_token])
                )
                surplus = exec_amt - buy_amount_from_id
            else:
                exec_amt = int(Fraction(order["executedAmount"])
                            * Fraction(soln["clearingPrices"][sell_token])
                            // Fraction(soln["clearingPrices"][buy_token]))
                surplus = exec_amt - buy_amount_from_id

            diff_surplus = win_surplus - surplus
            percent_deviation = (diff_surplus * 100) / buy_amount_from_id
            surplus_token = individual_order_data["buyToken"]

        elif kind == "buy":
            win_surplus = sell_amount_from_id - int(individual_order_data["executedSellAmountBeforeFees"])
            if individual_order_data["class"] == "limit":
                exec_amt = (
                    (int(Fraction(order["executedAmount"])))
                    * Fraction(soln["clearingPrices"][buy_token])
                    // Fraction(soln["clearingPrices"][sell_token])
                )
                surplus = sell_amount_from_id - int(individual_order_data["executedSurplusFee"]) - exec_amt
            else:
                exec_amt = int(Fraction(order["executedAmount"])
                            * Fraction(soln["clearingPrices"][buy_token])
                            // Fraction(soln["clearingPrices"][sell_token]))
                surplus = sell_amount_from_id - exec_amt

            diff_surplus = win_surplus - surplus
            percent_deviation = (diff_surplus * 100) / sell_amount_from_id
            surplus_token = individual_order_data["sellToken"]

        return (diff_surplus, percent_deviation, surplus_token)


    def print_function(self, surplus_deviation_dict, settlement_hash, individual_order_id, competition_data):
        sorted_dict = dict(sorted(surplus_deviation_dict.items(), key=lambda x: x[1][0]))
        sorted_values = sorted(sorted_dict.values(), key=lambda x: x[0])
        if sorted_values[0][0] < -0.001 and sorted_values[0][1] < -1:
            for key, value in sorted_dict.items():
                if value == sorted_values[0]:
                    first_key = key
                    break
                
            self.higher_surplus_orders += 1
            solver = competition_data["solutions"][-1]["solver"]
            self.solver_dict[solver][1] += 1
            self.total_surplus_eth += sorted_values[0][0]

            # recurring write to file indicating a flagged order and details
            with open(f"{self.file_name}", mode="a") as file:
                file.write("Settlement Hash: " + settlement_hash + "\n")
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


    def statistics_output(self, start_block, end_block):
        with open(f"{self.file_name}", mode="a") as file:
            file.write(
                f"Total Orders = {str(self.total_orders)} over {str(int(end_block)-int(start_block))} blocks from {str(start_block)} to {str(end_block)}\n"
            )
            file.write("No. of better surplus orders: " + str(self.higher_surplus_orders) + "\n")
            percent_better_offers = self.get_percent(self.higher_surplus_orders, self.total_orders)
            file.write("Percent of potentially better offers: " + percent_better_offers + "%\n")
            total_surplus_eth = self.total_surplus_eth
            file.write(f"Total missed surplus: " + str(format(total_surplus_eth, ".3f")) + "ETH\n")
            file.write("\n")

            for key in self.solver_dict:
                if self.solver_dict[key][0] == 0:
                    error_percent = 0
                else:
                    error_percent = (self.solver_dict[key][1] * 100) / (self.solver_dict[key][0])
                file.write(f"Solver: {key} errored: " +  str(format(error_percent, '.3f')) + "%\n")
            file.close()


    def get_percent(self, higher_surplus_orders: int, total_orders: int) -> str:
        percent = (higher_surplus_orders * 100)/total_orders
        percent = str(format(percent, '.3f'))
        return percent
