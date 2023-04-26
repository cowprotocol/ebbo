"""
This file contains functions used by cow_endpoint_surplus and quasimodo_test_surplus.
"""
import logging
import os
import requests
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from dune_client.client import DuneClient
from dune_client.query import Query

load_dotenv()
DUNE_KEY = os.getenv("DUNE_KEY")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_KEY")

ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"

def get_solver_dict() -> Dict[str, List[int]]:
    """
    Function prepares a solver dictionary by fetching solver names from a Dune query.
    """
    solver_dict = {}
    query = Query(
        name="Solver Dictionary",
        query_id=1372857,
    )
    if DUNE_KEY is not None:
        dune = DuneClient(DUNE_KEY)
        results = dune.refresh(query)
        solvers = results.get_rows()
        for solver in solvers:
            solver_dict[solver["name"]] = [0, 0]

        # These names need to be updated since Dune and Orderbook Endpoint have different names.
        # Example, "1Inch: [0, 0]" is a specific row, the first value is the number of solutions
        # won, second value is number of solutions of that solver with higher surplus found.

        solver_dict["BaselineSolver"] = solver_dict.pop("Baseline")
        solver_dict["1Inch"] = solver_dict.pop("Gnosis_1inch")
        solver_dict["0x"] = solver_dict.pop("Gnosis_0x")
        solver_dict["BalancerSOR"] = solver_dict.pop("Gnosis_BalancerSOR")
        solver_dict["ParaSwap"] = solver_dict.pop("Gnosis_ParaSwap")
        solver_dict["SeaSolver"] = solver_dict.pop("Seasolver")
        solver_dict["CowDexAg"] = solver_dict.pop("DexCowAgg")
        solver_dict["NaiveSolver"] = solver_dict.pop("Naive")

    return solver_dict


def get_logger(filename: Optional[str] = None) -> logging.Logger:
    """
    get_logger() returns a logger object that can write to a file, terminal or only file if needed.
    """
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if filename:
        file_handler = logging.FileHandler(filename + ".log", mode="w")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_tx_hashes_by_block(web_3, start_block: int, end_block: int) -> List[str]:
    """
    Function filters hashes by contract address, and block ranges
    """
    filter_criteria = {
        "fromBlock": int(start_block),
        "toBlock": int(end_block),
        "address": ADDRESS,
    }
    # transactions may have repeating hashes, since even event logs are filtered
    # therefore, check if hash has already been added to the list

    # only successful transactions are filtered
    transactions = web_3.eth.filter(filter_criteria).get_all_entries()
    settlement_hashes_list = []
    for transaction in transactions:
        tx_hash = (transaction["transactionHash"]).hex()
        if tx_hash not in settlement_hashes_list:
            settlement_hashes_list.append(tx_hash)
    return settlement_hashes_list



def get_eth_value():
    eth_price_url = f"https://api.etherscan.io/api?module=stats&action=ethprice&apikey={ETHERSCAN_KEY}"
    eth_price = requests.get(eth_price_url).json()["result"]["ethusd"]
    min_flag_usd = 4.00
    eth_absolute_check = str(format(min_flag_usd / float(eth_price), ".6f"))
    return eth_absolute_check


def percent_eth_conversions_sell_order(diff_surplus, buy_amount, external_price):
    """
    calcuate order flag condition values,
    (relative % deviation, absolute ETH difference) for sell orders
    """
    # implies a sell order
    percent_deviation = (diff_surplus * 100) / buy_amount
    # diff_in_eth = (
    #     external_price / (pow(10, 18)) * (diff_surplus)
    # )
    diff_in_eth = (external_price/(pow(10, 18))) * (diff_surplus/(pow(10, 18)))
    return percent_deviation, diff_in_eth


def percent_eth_conversions_buy_order(diff_surplus, sell_amount, external_price):
    """
    calcuate order flag condition values,
    (relative % deviation, absolute ETH difference) for buy orders
    """
    # implies a buy order
    percent_deviation = (diff_surplus * 100) / sell_amount
    # diff_in_eth = (
    #     external_price / (pow(10, 18)) * (diff_surplus)
    # )
    diff_in_eth = (external_price/(pow(10, 18))) * (diff_surplus/(pow(10, 18)))

    return percent_deviation, diff_in_eth


def get_surplus_buy_order(
    executed_amount,
    sell_amount,
    sell_token_clearing_price,
    buy_token_clearing_price):

    exec_amt = int(
        Fraction(executed_amount)
        * Fraction(buy_token_clearing_price)
        // Fraction(sell_token_clearing_price)
    )
    surplus = sell_amount - exec_amt
    return surplus


def get_surplus_sell_order(
    executed_amount,
    buy_amount,
    sell_token_clearing_price,
    buy_token_clearing_price):

    """
    computes surplus difference given non-winning solution data and winning solution data.
    """

    exec_amt = int(
        Fraction(executed_amount)
        * Fraction(sell_token_clearing_price)
        // Fraction(buy_token_clearing_price)
    )
    surplus = exec_amt - buy_amount
    return surplus


header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
