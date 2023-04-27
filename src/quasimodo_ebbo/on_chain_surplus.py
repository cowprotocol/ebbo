"""
This component of EBBO testing parses all settlements happening on-chain and recovers
each orders' surplus. We call Quasimodo to provide a solution for the same order, 
and then a comparison is made to determine whether the order should be flagged.
"""
from typing import List, Tuple, Optional
from copy import deepcopy
import os
from dotenv import load_dotenv
import requests
from web3 import Web3
from src.configuration import *
from src.constants import (
    INFURA_KEY,
    ABSOLUTE_ETH_FLAG_AMOUNT,
    REL_DEVIATION_FLAG_PERCENT,
)
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi

# fetch keys
load_dotenv()
QUASIMODO_SOLVER_URL = os.getenv("QUASIMODO_SOLVER_URL")


class QuasimodoTestEBBO:
    """
    Functions required for on-chain quasimodo calling functionality
    """

    def __init__(self) -> None:
        """
        Makes ethereum node connection via Infura, creates contract
        and logger instance
        """
        self.web_3 = Web3(
            Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}")
        )
        self.contract_instance = self.web_3.eth.contract(address=ADDRESS, abi=gpv2Abi)
        self.logger = get_logger()

    def create_tx_list(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        settlement_hash: Optional[str] = None,
    ) -> None:
        """
        Puts transactions in list, calls required function in case of range of blocks.
        """
        settlement_hashes_list = []
        if settlement_hash is not None:
            settlement_hashes_list = [settlement_hash]

        elif start_block is not None and end_block is not None:
            settlement_hashes_list = get_tx_hashes_by_block(
                self.web_3, start_block, end_block
            )
            # At this point we have all the needed hashes
        self.decoder(settlement_hashes_list)

    def decoder(self, settlement_hashes_list: List[str]) -> None:
        """
        Decode each hash which also calculates surplus
        """
        for settlement_hash in settlement_hashes_list:
            self.decode_single_hash(settlement_hash)

    def decode_single_hash(self, settlement_hash: str) -> Optional[bool]:
        """
        Goes through all settlements fetched, decodes orders,
        gets response from AWS bucket.
        Returns `None` in case data cannot be fetched, a not-None value "True" otherwise.
        """
        try:
            encoded_transaction = self.web_3.eth.get_transaction(settlement_hash)
            decoded_settlement = DecodedSettlement.new(
                self.contract_instance, encoded_transaction.input
            )
        except ValueError as except_err:
            self.logger.error(
                "Unhandled exception, possibly can't decode: %s", str(except_err)
            )
            return None
        (winning_orders, bucket_response) = self.get_order_data_by_hash(settlement_hash)
        if bucket_response is None:
            return None
        self.solve_orders_in_settlement(
            bucket_response, winning_orders, settlement_hash, decoded_settlement
        )
        return True

    def get_order_data_by_hash(
        self, settlement_hash: str
    ) -> Tuple[List[str], Optional[dict]]:
        """
        Returns competition endpoint data since we need order_id and auction_id, and also AWS
        Bucket response.
        """
        bucket_response = None
        comp_data = None
        try:
            # first fetch from production environment
            comp_data = requests.get(
                f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlement_hash}"
            )
            status_code = comp_data.status_code
            if status_code == 200:
                comp_data = comp_data.json()
                auction_id = comp_data["auctionId"]
                bucket_response = dict(
                    requests.get(
                        (
                            "https://solver-instances.s3.eu-central-1.amazonaws.com/"
                            f"prod-mainnet/{auction_id}.json"
                        )
                    ).json()
                )
            elif status_code == 404:
                # attempt fetch from staging environment, if prod failed.
                comp_data = requests.get(
                    (
                        "https://barn.api.cow.fi/mainnet/api/v1/solver_competition/"
                        f"by_tx_hash/{settlement_hash}"
                    )
                )
                status_code = comp_data.status_code
                if comp_data.status_code == 200:
                    comp_data = comp_data.json()
                    auction_id = comp_data["auctionId"]
                    bucket_response = dict(
                        requests.get(
                            (
                                "https://solver-instances.s3.eu-central-1.amazonaws.com/"
                                f"staging-mainnet/{auction_id}.json"
                            )
                        ).json()
                    )
            return comp_data["solutions"][-1]["orders"], bucket_response
        except ValueError as except_err:
            self.logger.error("Unhandled exception: %s", str(except_err))

    def get_solver_response(order_id: str, bucket_response: dict):
        """
        Updates AWS bucket response to a single order for posting
        to quasimodo, in order to get the solutions JSON.
        """
        solver_instance = deepcopy(bucket_response)
        for key, order in solver_instance["orders"].items():
            if order["id"] == order_id:
                solver_instance["orders"] = {key: order}
                break

        # convert back to JSON for sending to Quasimodo
        # bucket_response_json = json.dumps(solver_instance)

        # # space here to post and receive instance JSON from Quasimodo
        # data = {
        # "time_limit": "20",
        # "use_internal_buffers": "false",
        # "objective": "surplusfeescosts"
        # }
        # solution_json = requests.post(solver_instance_json, params=data)

        # assuming jsonObject is called solution_json
        # solution = solution_json.json() to convert to dict

        # 'solution' is what we use here as a python object in instance_file.py
        # return quasimodo solved solution
        # return solution, order

    def solve_orders_in_settlement(
        self,
        bucket_response: dict,
        winning_orders,
        settlement_hash: str,
        decoded_settlement,
    ):
        """
        This function goes over orders in settlement,
        calculates surplus difference by making calls to
        surplus calculating functions for on-chain solution, and
        quasimodo solution.
        """
        # there can be multiple orders/trades in a single settlement
        for trade in decoded_settlement.trades:
            sell_token_clearing_price = decoded_settlement.clearing_prices[
                trade["sellTokenIndex"]
            ]
            buy_token_clearing_price = decoded_settlement.clearing_prices[
                trade["buyTokenIndex"]
            ]
            # convert flags value to binary to extract L.S.B (Least Sigificant Byte)
            order_type = str(f"{trade['flags']:08b}")[-1]
            winning_surplus = get_surplus_order(
                trade["executedAmount"],
                trade["sellAmount"],
                sell_token_clearing_price,
                buy_token_clearing_price,
                order_type,
            )
            order_id = winning_orders[decoded_settlement.trades.index(trade)]["id"]
            solver_solution, order = self.get_solver_response(order_id, bucket_response)

            sell_token = order["sell_token"]
            buy_token = order["buy_token"]
            # if a valid solution is returned by solver
            if len(solver_solution["prices"]) > 0:
                sell_token_clearing_price = solver_solution["prices"][sell_token]
                buy_token_clearing_price = solver_solution["prices"][buy_token]
                quasimodo_surplus = get_surplus_order(
                    trade["executedAmount"],
                    trade["sellAmount"],
                    sell_token_clearing_price,
                    buy_token_clearing_price,
                    order_type,
                )
                diff_surplus = winning_surplus - quasimodo_surplus
                self.check_flag_condition(
                    diff_surplus,
                    trade,
                    order_type,
                    bucket_response["tokens"],
                    order,
                )

    def check_flag_condition(self, diff_surplus: int, trade, order_type, tokens, order):
        """
        Based on order type, this function fetches percent_deviation,
        and surplus difference in ETH to flag or NOT flag orders.
        """
        if order_type == "1":
            buy_or_sell_amount = int(trade["sellAmount"])
            external_price = int(tokens[order["sell_token"]]["external_price"])
        elif order_type == "0":
            buy_or_sell_amount = int(trade["buyAmount"])
            external_price = int(tokens[order["buy_token"]]["external_price"])

        percent_deviation, diff_in_eth = percent_eth_conversions_order(
            diff_surplus,
            buy_or_sell_amount,
            external_price,
        )
        if (
            percent_deviation < -REL_DEVIATION_FLAG_PERCENT
            and diff_in_eth < -ABSOLUTE_ETH_FLAG_AMOUNT
        ):
            print("flag")

    def print_logs(self, settlement_hash, order_id, winning_surplus):
        """
        print logs if order is flagged
        """
        # flag_log = "Settlement Hash: {}\nFor order: {}\nAbsolute ETH Difference: {}\n
        # Relative Percent Difference: {}\n".format(
        #     settlement_hash,
        #     order_id,
        #     str(format(diff_in_eth, ".5f")),
        #     str(format(percent_deviation, ".4f")),
        # )
        flag_log = "Settlement Hash: {}\nFor order: {}\nWinning surplus: {}\n".format(
            settlement_hash, order_id, winning_surplus
        )
        self.logger.info(flag_log)


# ---------------------------- TESTING --------------------------------
def main():
    """
    Main loop, to be deleted.
    """
    instance = QuasimodoTestEBBO()
    option_input = input("b for block input, h for hash input: ")
    match option_input:
        case "b":
            start_block = input("Start Block: ")
            end_block = input("End Block: ")
            instance.create_tx_list(start_block, end_block, None)
        case "h":
            settlement_hash = input("Settlement Hash: ")
            instance.create_tx_list(None, None, settlement_hash)


if __name__ == "__main__":
    main()
