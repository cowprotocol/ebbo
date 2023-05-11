"""
Fee Monitoring
"""

from typing import Tuple
from eth_typing import Address, HexStr
from hexbytes import HexBytes
from web3 import Web3
import json
import requests
from src.constants import INFURA_KEY, ADDRESS, SUCCESS_CODE, FAIL_CODE, header
from src.helper_functions import (
    get_logger,
    get_solver_competition_data,
    DecodedSettlement,
)
from contracts.gpv2_settlement import gpv2_settlement as gpv2Abi


class FeeMonitoring:
    """
    Class for fee monitoring.
    """

    def __init__(self) -> None:
        """
        TODO: Merge this with the setup of the other classes.
        """
        self.web_3 = Web3(
            Web3.HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}")
        )
        self.contract_instance = self.web_3.eth.contract(
            address=Address(HexBytes(ADDRESS)), abi=gpv2Abi
        )
        self.logger = get_logger()

    def get_encoded_transaction(self, tx_hash: str):
        """
        TODO: Merge with code from other tests.
        Takes settlement hash as input, returns decoded settlement data.
        """
        return self.web_3.eth.get_transaction(HexStr(tx_hash))

    def get_decoded_settlement(self, encoded_transaction) -> DecodedSettlement:
        return DecodedSettlement.new(
            self.contract_instance, encoded_transaction["input"]
        )

    def get_receipt(self, tx_hash: str):
        return self.web_3.eth.wait_for_transaction_receipt(HexStr(tx_hash))

    def get_orders(self, tx_hash: str):
        prod_endpoint_url = (
            "https://api.cow.fi/mainnet/api/v1/transactions/" + tx_hash + "/orders"
        )
        orders_response = requests.get(
            prod_endpoint_url,
            headers=header,
            timeout=30,
        )
        if orders_response.status_code != SUCCESS_CODE:
            self.logger.error(
                "Error loading orders from mainnet: ", orders_response.status_code
            )

        orders = json.loads(orders_response.text)

        return orders

    def get_gas_costs(self, encoded_transaction, receipt) -> Tuple[int]:
        return int(receipt["gasUsed"]), int(encoded_transaction["gasPrice"])

    def get_fee(self, tx_hash, order_uid) -> int:
        return 0  # TODO: get from data base

    def get_order_execution(self, tx_hash, order_uid):
        prod_endpoint_url = (
            "https://api.cow.fi/mainnet/api/v1/trades?orderUid=" + order_uid
        )
        trades_response = requests.get(
            prod_endpoint_url,
            headers=header,
            timeout=30,
        )
        trades = json.loads(trades_response.text)
        for t in trades:
            if t["txHash"] == tx_hash:
                trade = t
                break
            self.logger.error("Order not traded in transaction.")

        fee_amount = self.get_fee(tx_hash, order_uid)
        sell_amount = int(trade["sellAmount"]) - fee_amount
        buy_amount = int(trade["buyAmount"])

        return buy_amount, sell_amount, fee_amount

    def get_quote(self, decoded_settlement, i) -> Tuple[int]:
        trade = decoded_settlement.trades[i]

        if str(f"{trade['flags']:08b}")[-1] == "0":
            kind = "sell"
        else:
            kind = "buy"

        request_dict = {
            "sellToken": decoded_settlement.tokens[trade["sellTokenIndex"]],
            "buyToken": decoded_settlement.tokens[trade["buyTokenIndex"]],
            "receiver": trade["receiver"],
            "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "partiallyFillable": False,
            "sellTokenBalance": "erc20",
            "buyTokenBalance": "erc20",
            "from": trade["receiver"],
            "priceQuality": "optimal",
            "signingScheme": "eip712",
            "onchainOrder": False,
            "kind": kind,
            "sellAmountBeforeFee": str(trade["executedAmount"]),
        }

        try:
            prod_endpoint_url = "https://api.cow.fi/mainnet/api/v1/quote"
            quote_response = requests.post(
                prod_endpoint_url,
                headers=header,
                json=request_dict,
                timeout=30,
            )
            if quote_response.status_code != SUCCESS_CODE:
                barn_endpoint_url = "https://barn.api.cow.fi/mainnet/api/v1/quote"
                quote_response = requests.post(
                    barn_endpoint_url,
                    headers=header,
                    json=json.dumps(request_dict),
                    timeout=30,
                )
                if quote_response.status_code != SUCCESS_CODE:
                    logger.error("Quote error: %s.", quote_response.status_code)
        except ValueError as except_err:
            logger.error("Unhandled exception: %s.", str(except_err))

        quote_json = json.loads(quote_response.text)

        quote_buy_amount = int(quote_json["quote"]["buyAmount"])
        quote_sell_amount = int(quote_json["quote"]["sellAmount"])
        quote_fee_amount = int(quote_json["quote"]["feeAmount"])

        return quote_buy_amount, quote_sell_amount, quote_fee_amount

    def get_solver_solution(self, decoded_settlement, i):
        # solver_json = json.loads()

        solver_buy_amount = 0
        solver_sell_amount = 0
        solver_fee_amount = 0
        return solver_buy_amount, solver_sell_amount, solver_fee_amount

    def fee_test(self, tx_hash) -> bool:
        # get trades via api
        orders = self.get_orders(tx_hash)
        # loop through trades

        encoded_transaction = self.get_encoded_transaction(tx_hash)
        decoded_settlement = self.get_decoded_settlement(encoded_transaction)

        partially_fillable_indices = []
        for i in range(len(orders)):
            if orders[i][
                "partiallyFillable"
            ]:  # second least significant bit "1" iff order is partially fillable
                partially_fillable_indices.append(i)

        if len(partially_fillable_indices) > 0:
            # get additional data for the batch
            receipt = self.get_receipt(tx_hash)
            competition_data = get_solver_competition_data([tx_hash])[0]

            for i in partially_fillable_indices:
                # get additional data for the trade
                buy_amount, sell_amount, fee_amount = self.get_order_execution(
                    tx_hash, orders[i]["uid"]
                )
                quote_buy_amount, quote_sell_amount, quote_fee_amount = self.get_quote(
                    decoded_settlement, i
                )
                (
                    solver_buy_amount,
                    solver_sell_amount,
                    solver_fee_amount,
                ) = self.get_solver_solution(
                    decoded_settlement, i
                )  # TODO: use those values

                diff_fee_abs = fee_amount - quote_fee_amount
                diff_fee_rel = (fee_amount - quote_fee_amount) / quote_fee_amount

                log_output = (
                    "Quote test:"
                    "Tx hash: "
                    + tx_hash
                    + "\t\t"
                    + "Order indices: "
                    + str(i)
                    + "\t\t"
                    + "Winning Solver: "
                    + competition_data["solutions"][-1]["solver"]
                    + "\t\t"
                    + "Fee: "
                    + str(fee_amount)
                    + "\t\t"
                    + "Fee quote: "
                    + str(quote_fee_amount)
                    + "\t\t"
                    + "Absolute difference: "
                    + str(diff_fee_abs)
                    + "\t\t"
                    + "Relative difference: "
                    + (str(format(100 * diff_fee_rel, ".2f")) + "%")
                )
                if abs(diff_fee_abs) > 1e15 or abs(diff_fee_rel) > 0.2:
                    self.logger.warn(log_output)
                else:
                    self.logger.info(log_output)

            # get batch costs
            gas_amount, gas_price = self.get_gas_costs(encoded_transaction, receipt)
            cost = gas_amount * gas_price
            # get batch fees (not correct if some orders are market orders)
            fee = int(competition_data["solutions"][-1]["objective"]["fees"])

            a_abs = fee - cost
            a_rel = (fee - cost) / cost

            log_output = (
                "Tx hash: "
                + tx_hash
                + "\t\t"
                + "Order indices: "
                + str(partially_fillable_indices)
                + "\t\t"
                + "Winning Solver: "
                + competition_data["solutions"][-1]["solver"]
                + "\t\t"
                + "Fee: "
                + (str(format(fee * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Cost: "
                + (str(format(cost * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Absolute difference: "
                + (str(format(a_abs * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Relative difference: "
                + (str(format(100 * a_rel, ".2f")) + "%")
            )

            if (abs(a_abs) > 1e15 or abs(a_rel) > 0.2) and len(orders) == len(
                partially_fillable_indices
            ):
                self.logger.warn(log_output)
            else:
                self.logger.info(log_output)

        return True
