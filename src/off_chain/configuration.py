"""
This file contains functions used by cow_endpoint_surplus.
"""
import logging
from typing import Dict, List, Optional
from config import DUNE_KEY
from dune_client.client import DuneClient
from dune_client.query import Query

"""
get_solver_dict() prepares a solver dictionary by fetching solver names from a Dune query.
Example, "1Inch: [0, 0]" is a specific row, the first value is the number of solutions that could have
been given a better surplus, the second value is the total number of solutions executed by that solver.
"""


def get_solver_dict() -> Dict[str, List[int]]:
    solver_dict = {}
    query = Query(
        name="Solver Dictionary",
        query_id=1372857,
    )

    dune = DuneClient(DUNE_KEY)
    results = dune.refresh(query)
    solvers = vars((vars(results))["result"])
    for solver in solvers["rows"]:
        solver_dict[solver["name"]] = [0, 0]

    # These names need to be updated since Dune and Orderbook Endpoint have different names.
    solver_dict["BaselineSolver"] = solver_dict.pop("Baseline")
    solver_dict["1Inch"] = solver_dict.pop("Gnosis_1inch")
    solver_dict["0x"] = solver_dict.pop("Gnosis_0x")
    solver_dict["BalancerSOR"] = solver_dict.pop("Gnosis_BalancerSOR")
    solver_dict["ParaSwap"] = solver_dict.pop("Gnosis_ParaSwap")
    solver_dict["SeaSolver"] = solver_dict.pop("Seasolver")
    solver_dict["CowDexAg"] = solver_dict.pop("DexCowAgg")
    solver_dict["NaiveSolver"] = solver_dict.pop("Naive")

    return solver_dict


"""
get_logger() returns a logger object that can write to a file, terminal or only file if needed.
"""


def get_logger(filename: Optional[str] = None) -> logging.Logger:
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if filename:
        fh = logging.FileHandler(filename + ".log", mode="w")
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
